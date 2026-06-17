#!/usr/bin/env python3
"""
Extract structured data from AutoCAD DWG files.

DWG is a proprietary binary format. This script converts DWG -> DXF first, then
parses the DXF with ezdxf. Conversion options (first match wins):

  1. ODA File Converter (recommended on Windows)
     https://www.opendesign.com/guestfiles/oda_file_converter
  2. LibreDWG dwg2dxf (if installed and on PATH)
  3. An existing .dxf file (pass --dxf path/to/file.dxf)

Examples:
  python extract_dwg.py drawing.dwg
  python extract_dwg.py drawing.dwg --output report.json
  python extract_dwg.py drawing.dwg --format csv --output layers.csv
  python extract_dwg.py --dxf drawing.dxf --output report.json
  python extract_dwg.py drawing.dwg --oda "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional


def _require_ezdxf():
    try:
        import ezdxf  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: ezdxf\n"
            "Install with: pip install -r scripts/requirements-dwg.txt"
        ) from exc


@dataclass
class TextEntity:
    type: str
    layer: str
    text: str
    x: float
    y: float
    z: float
    height: Optional[float] = None
    rotation: Optional[float] = None
    block: Optional[str] = None


@dataclass
class LayerInfo:
    name: str
    color: int
    linetype: str
    is_on: bool
    is_locked: bool


@dataclass
class BlockInfo:
    name: str
    base_point: list[float]
    entity_count: int


@dataclass
class EntitySummary:
    type: str
    count: int


@dataclass
class ExtractionResult:
    source_file: str
    dxf_file: str
    converter: str
    dxf_version: str
    units: Optional[str]
    layers: list[LayerInfo] = field(default_factory=list)
    blocks: list[BlockInfo] = field(default_factory=list)
    entity_summary: list[EntitySummary] = field(default_factory=list)
    texts: list[TextEntity] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def find_oda_converter(explicit: Optional[str] = None) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("ODA_FILE_CONVERTER")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"),
            Path(r"C:\Program Files\ODA\ODAFileConverter 26.4.0\ODAFileConverter.exe"),
            Path("/usr/bin/ODAFileConverter"),
            Path("/usr/local/bin/ODAFileConverter"),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def find_dwg2dxf() -> Optional[str]:
    return shutil.which("dwg2dxf")


def convert_with_oda(dwg_path: Path, oda_exe: Path, version: str = "ACAD2018") -> Path:
    with tempfile.TemporaryDirectory(prefix="dwg_extract_") as tmp:
        out_dir = Path(tmp) / "out"
        out_dir.mkdir()
        cmd = [
            str(oda_exe),
            str(dwg_path.parent),
            str(out_dir),
            version,
            "DXF",
            "0",
            "1",
            dwg_path.name,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"ODA File Converter failed: {stderr or 'unknown error'}")

        dxf_candidates = sorted(out_dir.glob("*.dxf"))
        if not dxf_candidates:
            raise RuntimeError("ODA conversion produced no DXF output.")

        persistent = dwg_path.with_suffix(".converted.dxf")
        shutil.copy2(dxf_candidates[0], persistent)
        return persistent


def convert_with_libredwg(dwg_path: Path) -> Path:
    dwg2dxf = find_dwg2dxf()
    if not dwg2dxf:
        raise RuntimeError("dwg2dxf not found on PATH.")

    out_path = dwg_path.with_suffix(".converted.dxf")
    proc = subprocess.run(
        [dwg2dxf, "-o", str(out_path), str(dwg_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"dwg2dxf failed: {stderr or 'unknown error'}")
    if not out_path.is_file():
        raise RuntimeError("dwg2dxf did not create output DXF.")
    return out_path


def resolve_dxf(
    dwg_path: Optional[Path],
    dxf_path: Optional[Path],
    oda_path: Optional[str],
    keep_converted: bool,
) -> tuple[Path, str]:
    if dxf_path:
        if not dxf_path.is_file():
            raise FileNotFoundError(f"DXF not found: {dxf_path}")
        return dxf_path.resolve(), "provided-dxf"

    if not dwg_path:
        raise ValueError("Provide either a DWG file or --dxf.")

    if not dwg_path.is_file():
        raise FileNotFoundError(f"DWG not found: {dwg_path}")

    oda = find_oda_converter(oda_path)
    if oda:
        converted = convert_with_oda(dwg_path.resolve(), oda)
        if not keep_converted:
            return converted, f"oda:{oda.name}"
        return converted, f"oda:{oda.name}"

    if find_dwg2dxf():
        converted = convert_with_libredwg(dwg_path.resolve())
        return converted, "libredwg:dwg2dxf"

    raise RuntimeError(
        "Cannot read DWG directly. Install one of:\n"
        "  - ODA File Converter (Windows): https://www.opendesign.com/guestfiles/oda_file_converter\n"
        "  - LibreDWG dwg2dxf (Linux/macOS)\n"
        "Or convert manually to DXF and pass --dxf path/to/file.dxf"
    )


def vec3(point: Any) -> tuple[float, float, float]:
    return float(point.x), float(point.y), float(point.z)


def iter_layout_entities(layout: Any) -> Iterator[Any]:
    for entity in layout:
        yield entity
        if entity.dxftype() == "INSERT":
            try:
                for virtual in entity.virtual_entities():
                    yield virtual
            except Exception:
                continue


def extract_texts(msp: Any) -> list[TextEntity]:
    texts: list[TextEntity] = []
    for entity in iter_layout_entities(msp):
        dxftype = entity.dxftype()
        if dxftype == "TEXT":
            x, y, z = vec3(entity.dxf.insert)
            texts.append(
                TextEntity(
                    type="TEXT",
                    layer=entity.dxf.layer,
                    text=(entity.dxf.text or "").strip(),
                    x=x,
                    y=y,
                    z=z,
                    height=getattr(entity.dxf, "height", None),
                    rotation=getattr(entity.dxf, "rotation", None),
                )
            )
        elif dxftype == "MTEXT":
            x, y, z = vec3(entity.dxf.insert)
            plain = entity.plain_text() if hasattr(entity, "plain_text") else entity.text
            texts.append(
                TextEntity(
                    type="MTEXT",
                    layer=entity.dxf.layer,
                    text=(plain or "").strip(),
                    x=x,
                    y=y,
                    z=z,
                    height=getattr(entity.dxf, "char_height", None),
                    rotation=getattr(entity.dxf, "rotation", None),
                )
            )
        elif dxftype == "ATTRIB":
            x, y, z = vec3(entity.dxf.insert)
            texts.append(
                TextEntity(
                    type="ATTRIB",
                    layer=entity.dxf.layer,
                    text=(entity.dxf.text or "").strip(),
                    x=x,
                    y=y,
                    z=z,
                    block=getattr(entity.dxf, "tag", None),
                )
            )
    return [t for t in texts if t.text]


def extract_layers(doc: Any) -> list[LayerInfo]:
    layers: list[LayerInfo] = []
    for layer in doc.layers:
        layers.append(
            LayerInfo(
                name=layer.dxf.name,
                color=int(layer.dxf.color),
                linetype=str(layer.dxf.linetype),
                is_on=not layer.is_off(),
                is_locked=layer.is_locked(),
            )
        )
    return sorted(layers, key=lambda item: item.name.lower())


def extract_blocks(doc: Any) -> list[BlockInfo]:
    blocks: list[BlockInfo] = []
    for block in doc.blocks:
        if block.name.startswith("*"):
            continue
        base = block.block.dxf.base_point
        blocks.append(
            BlockInfo(
                name=block.name,
                base_point=[float(base.x), float(base.y), float(base.z)],
                entity_count=sum(1 for _ in block),
            )
        )
    return sorted(blocks, key=lambda item: item.name.lower())


def extract_entity_summary(msp: Any) -> list[EntitySummary]:
    counts: dict[str, int] = {}
    for entity in iter_layout_entities(msp):
        dxftype = entity.dxftype()
        counts[dxftype] = counts.get(dxftype, 0) + 1
    return [
        EntitySummary(type=name, count=count)
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def extract_from_dxf(dxf_path: Path, source_file: str, converter: str) -> ExtractionResult:
    import ezdxf

    warnings: list[str] = []
    try:
        doc = ezdxf.readfile(str(dxf_path))
    except ezdxf.DXFStructureError:
        doc, auditor = ezdxf.recover.readfile(str(dxf_path))
        warnings.extend(auditor.errors[:20])
        if len(auditor.errors) > 20:
            warnings.append(f"... and {len(auditor.errors) - 20} more DXF recovery issues")

    msp = doc.modelspace()
    units = None
    if doc.units is not None:
        try:
            units = str(doc.units)
        except Exception:
            units = repr(doc.units)

    return ExtractionResult(
        source_file=source_file,
        dxf_file=str(dxf_path),
        converter=converter,
        dxf_version=doc.dxfversion,
        units=units,
        layers=extract_layers(doc),
        blocks=extract_blocks(doc),
        entity_summary=extract_entity_summary(msp),
        texts=extract_texts(msp),
        warnings=warnings,
    )


def write_json(result: ExtractionResult, output: Path) -> None:
    payload = asdict(result)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(result: ExtractionResult, output: Path, section: str) -> None:
    if section == "texts":
        rows = result.texts
        fieldnames = ["type", "layer", "text", "x", "y", "z", "height", "rotation", "block"]
    elif section == "layers":
        rows = result.layers
        fieldnames = ["name", "color", "linetype", "is_on", "is_locked"]
    elif section == "blocks":
        rows = result.blocks
        fieldnames = ["name", "base_point", "entity_count"]
    elif section == "entities":
        rows = result.entity_summary
        fieldnames = ["type", "count"]
    else:
        raise ValueError(f"Unknown CSV section: {section}")

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def print_summary(result: ExtractionResult) -> None:
    print(f"Source:     {result.source_file}")
    print(f"DXF used:   {result.dxf_file}")
    print(f"Converter:  {result.converter}")
    print(f"DXF ver:    {result.dxf_version}")
    print(f"Units:      {result.units or 'unknown'}")
    print(f"Layers:     {len(result.layers)}")
    print(f"Blocks:     {len(result.blocks)}")
    print(f"Text items: {len(result.texts)}")
    print("Entity types:")
    for item in result.entity_summary[:15]:
        print(f"  {item.type:12} {item.count}")
    if len(result.entity_summary) > 15:
        print(f"  ... {len(result.entity_summary) - 15} more types")
    if result.warnings:
        print(f"Warnings:   {len(result.warnings)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract data from DWG/DXF CAD files.")
    parser.add_argument("dwg", nargs="?", help="Path to input .dwg file")
    parser.add_argument("--dxf", help="Use an existing .dxf instead of converting DWG")
    parser.add_argument(
        "--output",
        "-o",
        help="Output file (.json or .csv). Default: print summary to stdout",
    )
    parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format when --output is set (default: json)",
    )
    parser.add_argument(
        "--csv-section",
        choices=("texts", "layers", "blocks", "entities"),
        default="texts",
        help="Which section to export when --format csv (default: texts)",
    )
    parser.add_argument(
        "--oda",
        help="Path to ODAFileConverter.exe (or set ODA_FILE_CONVERTER env var)",
    )
    parser.add_argument(
        "--keep-converted",
        action="store_true",
        help="Keep the intermediate .converted.dxf next to the DWG",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    _require_ezdxf()
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    dwg_path = Path(args.dwg).resolve() if args.dwg else None
    dxf_path = Path(args.dxf).resolve() if args.dxf else None

    try:
        resolved_dxf, converter = resolve_dxf(
            dwg_path=dwg_path,
            dxf_path=dxf_path,
            oda_path=args.oda,
            keep_converted=args.keep_converted,
        )
        source = str(dxf_path or dwg_path)
        result = extract_from_dxf(resolved_dxf, source_file=source, converter=converter)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        output = Path(args.output)
        if args.format == "json":
            write_json(result, output)
        else:
            write_csv(result, output, args.csv_section)
        print(f"Wrote {args.format.upper()} to {output}")
    else:
        print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
