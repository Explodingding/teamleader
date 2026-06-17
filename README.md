# Teamleader Electrical Utilities — Application Pack

CV, cover letter, and interview preparation documents for Łukasz Klimowski's
application for Teamleader Electrical Utilities at Ciner Glass, Lommel, Belgium.

## Live site

**https://explodingding.github.io/teamleader/**

GitHub Pages serves the HTML directly from the `main` branch root.
Every push to `main` updates the site automatically (no build step needed).

## Documents

| File | Description |
|------|-------------|
| `index.html` | Hub — links to all documents |
| `cv.html` | Curriculum Vitae |
| `cover-letter.html` | Cover letter |
| `team-development.html` | Team development & supervision model |
| `working-method.html` | Working method |
| `utilities-scope.html` | Utilities & site scope |
| `kpi-approach.html` | KPI & statistics approach |
| `leadership-edge.html` | Leadership advantages |
| `case-studies.html` | STAR case studies |
| `interview-prep.html` | Interview preparation |
| `job-analysis.html` | Vacancy fit analysis |

## PDF export

Open any document → **Print / Save PDF** in the toolbar (enable **Background graphics** for colours).

## Local preview

```powershell
python -m http.server 8080
```
Open http://localhost:8080

## DWG extraction script

`scripts/extract_dwg.py` — extracts layers, blocks, and text from DWG/DXF files.
Requires `ezdxf`: `pip install -r scripts/requirements-dwg.txt`

Large CAD files (`*.dwg`, `*.dxf`) are excluded via `.gitignore` (GitHub 100 MB limit).
