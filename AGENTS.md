# Developer Guide & Agent Context

Technical details, architectural decisions, and best practices for developers and AI agents working on this codebase.

## Project Architecture

The project is a CLI + GUI tool built on **Playwright** for browser automation. Entry points:

- `uv run crm run` — runs the automation (via `src/crm_helper/cli.py` → `main.py`)
- `uv run crm gui` — opens the config GUI (via `src/crm_helper/cli.py` → `gui.py`)

### Package Layout

```
src/crm_helper/         # Main package (src-layout, built with uv_build)
├── cli.py              # Typer app: `run` and `gui` commands
├── config.py           # Pydantic BaseSettings — reads from .env
├── date_distributor.py # Round-robin weekday scheduler with holiday exclusion
├── gui.py              # CustomTkinter GUI for .env editing
├── logger.py           # Logging setup (file + console)
├── main.py             # Top-level async automation loop
├── automation/
│   ├── activities_page.py  # Page object: list navigation, pagination
│   ├── auth.py             # Login / session verification
│   ├── browser.py          # Playwright context lifecycle
│   └── user_processor.py   # Per-row: detect PLANNED → HELD + Copy
└── models/
    └── user.py             # UserResult, ProcessingReport (Pydantic)
```

### Core Components

1. **`main.py`** — top-level loop.
   - Iterates pages of `/activities/`, processes each visible row.
   - Does **not** reload the page between rows — reloading shifts DOM indices and causes skips.

2. **`automation/activities_page.py`** — page object for the list view.
   - Pagination: waits for table content with `wait_for_selector`, avoids flaky `networkidle` on this SPA.

3. **`automation/user_processor.py`** — the heavy lifter.
   - **Primary path**: click "Mark as HELD" + "Copy" directly in the table row.
   - **Fallback path**: navigate to the details page if row buttons are missing.
   - **Self-healing**: `_ensure_modal_closed()` force-closes stuck modals before each row.
   - **Performance**: row is fetched with `:nth-child(n)` — O(1) lookup. The previous `:not(:has-text("Loading"))` filter was O(n) as the DOM grew with copies.

4. **`date_distributor.py`** — round-robin weekday scheduler.
   - Generates a sorted list of Mon–Fri dates in `[start_date, end_date]`, excluding `holidays`.
   - `get_next_date()` cycles through this list indefinitely, returning dates as `"YYYY-MM-DD"` strings.

5. **`config.py`** — `pydantic-settings` `BaseSettings`.
   - Reads all fields from `.env` (or environment variables).
   - Key fields: `login`, `password`, `start_date`, `end_date`, `holidays: list[date]`, `headless`.
   - `holidays` is parsed from a comma-separated string by pydantic automatically.

6. **`gui.py`** — `CustomTkinter` desktop configurator.
   - Reads/writes `.env` directly (path resolved relative to package root).
   - Date fields use a custom `DatePicker` widget: `CTkEntry` + button that opens a `CTkToplevel` with `tkcalendar.Calendar`.
   - Holidays use `HolidayPicker`: a list of date chips with `×` removal and `+ Add holiday` button.
   - **Why not `DateEntry` from tkcalendar**: its dropdown popup calculates position incorrectly inside CustomTkinter scaled windows — goes off-screen. `CTkToplevel` with manual positioning is reliable.

## Selectors Strategy

Standard attributes (ID, `name`) are often missing or unstable (Vue.js `data-v-...`). We use structural and text-based selectors.

### Activities List (`/activities/`)

| Element | Selector | Notes |
|---|---|---|
| Row by position | `#activity-table-false tbody tr:nth-child(n)` | O(1), used in `user_processor` |
| Status badge | `span[title="PLANNED"]` | Presence check to skip non-planned rows |
| Next page | `li.pagination__item:not(.disabled) a:has-text("Next")` | `<a>` inside `<li>` |

### Copy Activity Modal

The modal has no `name`/`id` on inputs — scope all selectors to `.modal:visible`:

| Element | Selector |
|---|---|
| Description | `textarea.form-control` |
| Start date | `.datepicker-div input` (first in modal) |
| Save button | `button[type="submit"]` or `:has-text("Save")` |

## Best Practices

1. **Direct list processing**: always prefer row buttons over details-page navigation — ~10× faster.
2. **No page reloads mid-loop**: the list is live; reloading shifts indices and causes duplicates/skips.
3. **Modal hygiene**: always verify modal is closed after each action; check for blocking modals before starting each row.
4. **Round-robin dates**: never use `random`. `DateDistributor.get_next_date()` guarantees even distribution.
5. **Selector scoping**: scope modal selectors to the modal locator, not the full page, to avoid ghost elements.

## Debugging Tips

- **Logs**: each run creates a timestamped file in `logs/`. Set `HEADLESS=False` in `.env` to watch the browser.
- **Screenshots on failure**: add `await page.screenshot(path="debug.png")` in exception handlers.
- **Playwright strict mode**: if you see "strict mode violation", add `.first` or narrow the selector.
- **GUI `.env` path**: `ENV_FILE = Path(__file__).parent.parent.parent / ".env"` — three levels up from `src/crm_helper/gui.py` to project root.

## Build System

- Build backend: `uv_build` (requires package at `src/crm_helper/` matching project name `crm-helper` → `crm_helper`).
- CLI entry point defined in `pyproject.toml`: `crm = "crm_helper.cli:app"`.
- Install: `uv sync` — installs the package in editable mode and all dependencies.

## Workflow Logic

```
login → /activities/
└── for each page:
    └── for each row (by :nth-child index):
        ├── check for span[title="PLANNED"]
        ├── if found:
        │   ├── _ensure_modal_closed()
        │   ├── click "Mark as HELD"
        │   ├── click "Copy"
        │   ├── fill modal (description="!!!", start_date=DateDistributor.get_next_date())
        │   └── save modal
        └── if not found: skip
    └── click "Next" → wait_for_selector (table rows)
```
