# Teamleader Electrical Utilities — Application Pack

HTML documents for the Ciner Glass Lommel application (CV, cover letter, interview prep, development pack).

## Live site (recommended)

**https://explodingding.github.io/teamleader/**

The pack is deployed automatically on every push to `main` via GitHub Pages.

### First-time setup (one minute)

1. Open **Settings → Pages** in this repo.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Push to `main` (or re-run the *Deploy application pack to GitHub Pages* workflow).

## Why opening files locally often “doesn’t work”

Double-clicking `html/index.html` opens it as `file://…`. Browsers block **ES module** scripts (used for Mermaid diagrams) from CDNs on `file://` pages. CSS and plain HTML still load, but diagrams stay blank.

Serving the same files over **HTTPS** (GitHub Pages, or a local server) fixes this.

### Local preview (optional)

```powershell
cd html
python -m http.server 8080
```

Then open http://localhost:8080

## Repo layout

| Path | Contents |
|------|----------|
| `html/` | Application pack (published to Pages) |
| `scripts/` | DWG/DXF extraction helper (`extract_dwg.py`) |
| `01-*.md` … `05-*.md` | Polish planning templates |

Large CAD files (`*.dwg`, `*.dxf`) are gitignored (GitHub 100 MB limit).

## PDF export

From the live site or local server: open any document → **Print / Save PDF** in the toolbar.
