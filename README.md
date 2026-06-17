# Teamleader Electrical Utilities — Application Pack

HTML documents for the Ciner Glass Lommel application (CV, cover letter, interview prep, development pack).

## Live site

**https://explodingding.github.io/teamleader/**

### GitHub Pages setup (required once)

1. Repo → **Settings** → **Pages**
2. **Build and deployment** → **Source**: **Deploy from a branch**
3. **Branch**: `gh-pages` · folder **`/ (root)`** → **Save**
4. Wait ~1 minute after the deploy workflow finishes on `main`

The workflow copies everything from `html/` to the `gh-pages` branch. If Pages points at `main` instead, you will only see this README and **all document links will 404**.

## Why links break

| Situation | What happens |
|-----------|----------------|
| Pages source = `main` (repo root) | Shows README; `cv.html` etc. do not exist → **404** |
| Open `html/index.html` from disk (`file://`) | Mermaid diagrams fail; some assets blocked |
| Pages source = `gh-pages` (correct) | All links work over HTTPS |

## Local preview

```powershell
cd html
python -m http.server 8080
```

Open http://localhost:8080 — links work locally; the GitHub base-path script only runs on `github.io`.

## PDF export

Open any document → **Print / Save PDF** in the toolbar (enable **Background graphics** for colours).
