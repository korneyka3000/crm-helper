# CRM Helper Automation

A robust automation tool for managing CRM activities. Automatically processes "Planned" activities, marks them as "Held", and creates copies with dates distributed evenly across future workdays.

## Features

- **Smart Processing**: Works directly from the Activities list for maximum speed.
- **Load Balancing**: Distributes new activities evenly across weekdays (Mon–Fri) using a Round-Robin algorithm.
- **Holiday Exclusion**: Configurable list of public holidays skipped during date distribution.
- **Self-Healing**: Automatically detects and closes stuck modals to prevent crashes.
- **Pagination Support**: Handles multi-page lists automatically.
- **GUI Configurator**: Visual interface for editing all settings without touching `.env`.
- **CLI Interface**: Single entry point for both automation and GUI.

## Prerequisites

- Python 3.14+
- `uv` package manager

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Install Playwright browser:
   ```bash
   uv run playwright install chromium
   ```
4. Create `.env` in the project root (or use the GUI — see below):
   ```env
   LOGIN=your_email@example.com
   PASSWORD=your_password
   START_DATE=2026-07-01
   END_DATE=2026-09-30
   HOLIDAYS=2026-07-03,2026-11-07
   HEADLESS=True
   ```

## Usage

```bash
# Run the automation
uv run crm run

# Open the configuration GUI
uv run crm gui

# Show help
uv run crm --help
```

### GUI

`uv run crm gui` opens a desktop window where you can:
- Edit login credentials
- Pick start/end dates from a calendar
- Add/remove holidays via calendar picker
- Toggle headless mode
- Save settings and launch the automation in one click

## Configuration

All settings are read from `.env` in the project root (managed via `pydantic-settings`):

| Variable | Default | Description |
|---|---|---|
| `LOGIN` | — | CRM username / email |
| `PASSWORD` | — | CRM password |
| `START_DATE` | `2026-07-01` | Start of scheduling window |
| `END_DATE` | `2026-09-30` | End of scheduling window |
| `HOLIDAYS` | _(empty)_ | Comma-separated dates to skip (YYYY-MM-DD) |
| `HEADLESS` | `True` | `False` to watch the browser |
| `BASE_URL` | `https://mysigma.support` | CRM base URL |

## Output

- **Logs**: timestamped log files in `logs/`
- **Reports**: JSON summaries of each run in `output/`

## Project Structure

```
src/crm_helper/
├── cli.py              # Typer CLI entry point
├── config.py           # Pydantic-settings configuration
├── date_distributor.py # Round-robin weekday scheduler
├── gui.py              # CustomTkinter GUI
├── logger.py           # Logging setup
├── main.py             # Automation entry point
├── automation/
│   ├── activities_page.py  # Page object for the Activities list
│   ├── auth.py             # Login / session management
│   ├── browser.py          # Playwright browser lifecycle
│   └── user_processor.py   # Per-row processing logic
└── models/
    └── user.py             # Pydantic data models
```

## For Developers

See [AGENTS.md](AGENTS.md) for architectural decisions, selector strategies, and debugging tips.
