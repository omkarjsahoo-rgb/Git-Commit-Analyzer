# Git Commit Analyzer

A local developer tool that analyzes Git repositories: it scores commit message quality, tracks contributor activity, flags inactive branches and visualizes development patterns.

**Read-only by design.** It never commits, checks out, fetches, deletes or pushes anything in the repository it analyzes, and it needs no GitHub login. It reads folders on your own computer. To analyze a GitHub project, `git clone` it first and point the app at the folder.

Built with Python, Flask, GitPython and SQLite on the backend, and React (Vite), Chart.js and plain CSS on the frontend.

## Features

| Area | What it does |
|---|---|
| **Overview** | Commits, contributors, branches, quality score, conventional-commit rate, activity chart, contributor chart, quality distribution and recent commits |
| **Commits** | Full history with search (message, author, hash), branch and quality filters, paging, and a per-commit breakdown of problems with a suggested rewrite |
| **Contributors** | Commits per person, share, active days, first and last commit, average message quality, and active contributors over time |
| **Branches** | Local branches with last commit date, age, unmerged commits and an active / stale / inactive status. Potentially inactive branches are highlighted. |
| **Reports** | Repository health score with findings, the lowest-scoring commits, CSV exports (commits, contributors, branches) and saved analysis snapshots |
| **Settings** | Open or close a repository, plus preferences (default chart period, branch inactivity threshold, commits per page) |

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer (developed on Node 26)
- Git installed and available on your PATH (GitPython needs the `git` executable)

## Installation

```bash
git clone https://github.com/omkarjsahoo-rgb/Git-Commit-Analyzer.git
cd Git-Commit-Analyzer
```

**Backend** (Windows PowerShell):

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Backend** (macOS / Linux):

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once.

**Frontend:**

```bash
cd frontend
npm install
```

## Running

You need two terminals, both started from the project folder.

**Terminal 1: backend** (the prompt must show `(venv)`):

```powershell
cd backend
venv\Scripts\Activate.ps1        # macOS / Linux: source venv/bin/activate
python run.py
```

It listens on `http://127.0.0.1:5001`.

**Terminal 2: frontend:**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**, enter the path of a local Git repository (the folder that directly contains `.git`) and press Open. In Windows File Explorer, right-click the folder and choose "Copy as path".

## Tests

```powershell
cd backend
venv\Scripts\Activate.ps1
pytest -v
```

The suite (110 tests) builds throwaway Git repositories in temporary folders, so it never touches your own projects. It includes a test that fingerprints every file of a repository (including `.git`), calls every endpoint and checks that nothing changed.

For frontend linting: `cd frontend && npm run lint`.

## How scoring works

Each commit subject gets 0 to 100 points:

| Part | Points | What earns them |
|---|---|---|
| Format | 40 | Valid Conventional Commits: `type(scope): description`. A near miss such as `Fix: bug` earns 15. |
| Description | 30 | 3 or more meaningful words earns 30, 2 words 15, 1 word 5, a vague description 0 |
| Subject length | 15 | Up to 50 characters earns 15, 51 to 72 earns 10, over 72 earns 3, under 10 earns 0 |
| Style | 15 | 5 each for no trailing period, imperative mood ("add", not "added") and sensible capitalization |

Ratings: **excellent** 80+, **good** 60 to 79, **fair** 40 to 59, **poor** below 40. A vague message (such as `final commit` or `fix bug`) can never score above 35.

Messages that Git or tools write for you are **not scored**: merge commits, `Revert "..."`, `fixup!` / `squash!` and `Initial commit`.

Recognized types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

**Health score** = 70% average message quality + 30% branch hygiene (the share of non-protected branches that are not flagged inactive). 75 and above is *healthy*, 50 to 74 *needs attention*, below 50 *at risk*.

**Branch status** uses your threshold N: *active* is under N days since the last commit, *stale* is N to 2N, *inactive* is over 2N. Only branches that are inactive **and** not protected are flagged. `main`, `master`, `develop` and the current branch are never flagged. The tool only labels branches and never changes them.

## API

All endpoints return JSON (errors look like `{"error": "..."}`) except the CSV downloads. Every analysis endpoint takes the repository folder as `path`.

| Method and endpoint | Purpose |
|---|---|
| `GET /api/health` | Server check |
| `POST /api/repository/open` | Validate a path, return repository info, remember it |
| `GET /api/repository/recent` | Recently opened repositories |
| `GET /api/commits` | Paged commits with quality (`limit`, `offset`, `branch`, `q`, `rating`) |
| `GET /api/branches` | Local branches |
| `GET /api/branches/analysis` | Branch status and age (`inactive_days`) |
| `POST /api/quality/check` | Score any message (`{"message": "..."}`) |
| `GET /api/quality/summary` | Average score, distribution, lowest-scoring commits |
| `GET /api/contributors` | Per-contributor statistics |
| `GET /api/activity` | Commits over time (`period`: daily, weekly or monthly; `periods`) |
| `GET /api/reports/health` | Health score, findings, problem breakdown |
| `GET /api/reports/commits.csv` | Commit analysis export |
| `GET /api/reports/contributors.csv` | Contributor export |
| `GET /api/reports/branches.csv` | Branch export (`inactive_days`) |
| `POST /api/reports/snapshots` | Save the current totals to the history table |
| `GET /api/reports/snapshots` | Saved snapshots for a repository |

## Project structure

```
backend/
  run.py                      Entry point
  app/
    __init__.py               App factory, error handlers, host check
    config.py                 Settings (port, database path, limits)
    database.py               SQLite setup (recent repositories, analysis history)
    routes/                   HTTP endpoints, one file per feature
    services/
      git_service.py          Read-only Git access (GitPython)
      quality_checker.py      Commit message scoring
      analytics_service.py    Contributor, activity and branch analytics
      report_service.py       CSV building and health summary
    utils/                    Validation and error types
  tests/                      pytest suites (one file per phase)
  data/                       SQLite file is created here (git-ignored)
frontend/
  src/
    api/client.js             Every call to the backend
    context/RepoContext.jsx   The currently open repository
    hooks/                    useApi, useDebounce
    components/               Layout, sidebar, panels, tables, charts
    pages/                    Overview, Commits, Contributors, Branches, Reports, Settings
    styles/                   theme.css (palette) and global.css
    utils/                    Formatting helpers and saved preferences
```

## Safety and design decisions

- **Read-only.** `git_service.py` only uses read operations (iterating commits, listing branches, counting). A test proves that no file in a repository changes after every endpoint has been called.
- **Local only.** The server binds to `127.0.0.1`, allows cross-origin requests only from the dev server, and rejects requests whose `Host` header is not `localhost` or `127.0.0.1` (protection against DNS-rebinding).
- **Input validation.** Paths, limits, search text and ratings are validated on the server. Bad input returns a clear JSON error, never a stack trace.
- **Spreadsheet-safe CSVs.** Cells that start with `=`, `+`, `-` or `@` get a leading `'` so Excel cannot run them as formulas. Files are UTF-8 with a BOM so accents and emoji open correctly.
- **The tool's own data** (recent repositories, saved snapshots) lives in `backend/data/analyzer.db`, never inside the analyzed repository. Preferences live in your browser's local storage.
- **No demo data.** Every number and chart comes from the repository you open.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No module named 'git'` | The virtual environment is not active. Activate it (the prompt shows `(venv)`) and try again. |
| "Cannot reach the backend" | The backend is not running, or was started outside the venv. Start `python run.py` in the `backend` folder. |
| Port 5001 already in use | Change `PORT` in `backend/app/config.py` and the proxy target in `frontend/vite.config.js`. |
| "That looks like a web address" | The app reads local folders only. Run `git clone <url>` first, then enter the folder path. |
| "not a Git repository" | Select the folder that directly contains `.git`, not a subfolder or the `.git` folder itself. |
| "dubious ownership" | Git refuses folders owned by another Windows user. Run `git config --global --add safe.directory "<folder>"` once. |
| Bare repository error | Bare repositories have no working folder. Select a normal clone. |

## Limitations

- Only **local branches** are analyzed. The tool never fetches, so run `git pull` yourself to see new remote commits.
- Quality, contributor, activity and report figures cover the **newest 5,000 commits**. The app says so when a repository is larger.
- The vague-word list and imperative-mood check are heuristics tuned for English. They are right most of the time, not always.
- The Commits and Overview pages work out which branches contain each commit, which can be slow on repositories with very many commits and branches.
- This is a development tool: it runs Flask's development server in debug mode and is not meant to be hosted for other people.