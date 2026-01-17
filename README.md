# CRM Helper

Automated CRM activity management tool using Playwright for browser automation.

## Overview

CRM Helper automates the process of updating planned activities in the CRM system at https://mysigma.support/activities/. The tool:
- Logs into the CRM system
- Processes all users across all pages
- Finds activities with "Planned" status
- Marks them as "HELD" and creates copies with new dates
- Distributes dates evenly across weekdays (Mon-Fri)
- Generates reports and logs

## Features

- **Automated Processing**: Handles all users across paginated lists
- **Smart Date Distribution**: Even distribution across weekdays (excludes weekends)
- **Robust Error Handling**: Continues processing on errors
- **Comprehensive Logging**: Dual logging (console + file)
- **Detailed Reports**: JSON reports for users without planned activities
- **Headless Mode**: Runs in background without UI

## Prerequisites

- Python 3.14+
- uv package manager
- Internet connection

## Installation

1. Clone the repository and navigate to the project directory

2. Install dependencies:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv run playwright install chromium
```

4. Configure credentials in `.env` file (already exists):
```env
LOGIN=your_email@example.com
PASSWORD=your_password
```

## Configuration

Edit `.env` file or use environment variables to configure:

```env
# Required
LOGIN=your_email@example.com
PASSWORD=your_password

# Optional (with defaults)
BASE_URL=https://mysigma.support
HEADLESS=true
TIMEOUT_DEFAULT=30000
TIMEOUT_NAVIGATION=60000
START_DATE=2026-08-24
END_DATE=2026-09-30
LOG_LEVEL=INFO
```

## IMPORTANT: Selector Configuration

Before first run, you need to update selectors in the automation modules:

1. Run Playwright codegen to inspect the CRM website:
```bash
uv run playwright codegen https://mysigma.support/accounts
```

2. Update selectors in these files:
   - `src/automation/auth.py` - Login form selectors
   - `src/automation/activities_page.py` - User list and pagination selectors
   - `src/automation/user_processor.py` - Activity table and modal selectors

Look for `# TODO: Update these selectors` comments in each file.

## Usage

### Basic Run

```bash
uv run python main.py
```

### Debug Mode (Visible Browser)

Edit `.env` and set:
```env
HEADLESS=false
```

Then run:
```bash
uv run python main.py
```

## Project Structure

```
crm-helper/
├── .env                          # Configuration (credentials)
├── main.py                       # Entry point
├── logs/                         # Log files
│   └── crm_automation_*.log
├── output/                       # JSON reports
│   ├── users_without_planned_*.json
│   └── processing_report_*.json
└── src/
    ├── config.py                 # Configuration management
    ├── logger.py                 # Logging setup
    ├── date_distributor.py       # Date distribution logic
    ├── automation/
    │   ├── browser.py            # Browser management
    │   ├── auth.py               # Authentication
    │   ├── activities_page.py   # Page navigation
    │   └── user_processor.py    # User processing
    └── models/
        └── user.py               # Data models
```

## Workflow

1. **Login**: Authenticates with provided credentials
2. **Navigate**: Goes to activities page
3. **Iterate Pages**: Processes all pagination pages
4. **For Each User**:
   - Opens user detail
   - Finds activities with "Planned" status
   - Marks each as "HELD"
   - Clicks "Copy" button
   - Fills modal:
     - Description: "!!!"
     - Start: Next weekday date (YYYY-MM-DD 00:00)
   - Saves and closes modal
   - Reloads page to refresh list
5. **Generate Reports**: Creates JSON files with results

## Output Files

### Users Without Planned Activities
`output/users_without_planned_YYYYMMDD_HHMMSS.json`
```json
[
  {"user_index": 5},
  {"user_index": 12}
]
```

### Processing Report
`output/processing_report_YYYYMMDD_HHMMSS.json`
```json
{
  "total_users": 50,
  "successful_users": 48,
  "failed_users": 2,
  "users_without_planned": [5, 12],
  "total_activities_processed": 120,
  "errors": [...],
  "execution_time": 1234.56
}
```

### Log Files
`logs/crm_automation_YYYYMMDD_HHMMSS.log`

Contains detailed execution logs with timestamps, debug info, and error traces.

## Date Distribution

The tool distributes activity dates evenly across weekdays (Monday-Friday) from August 24, 2026 to September 30, 2026:

- **Algorithm**: Round-robin distribution
- **Weekdays Only**: Automatically excludes weekends
- **Even Distribution**: Each date gets approximately equal number of activities
- **Format**: YYYY-MM-DD 00:00

Example: If there are 27 weekdays and 54 activities, each date gets 2 activities.

## Error Handling

The tool is designed to be resilient:

- **Authentication Errors**: Stops execution, logs error
- **User Processing Errors**: Logs error, continues with next user
- **Timeout Errors**: Logs warning, continues
- **Unexpected Errors**: Logs full traceback, continues

All errors are logged to both console and log file.

## Troubleshooting

### Login Fails
- Verify credentials in `.env`
- Check if selectors in `auth.py` are correct
- Run with `HEADLESS=false` to see what's happening

### No Users Found
- Check selectors in `activities_page.py`
- Verify you're on correct URL
- Check browser console for JavaScript errors

### Activities Not Processing
- Update selectors in `user_processor.py`
- Check if "Planned" status text matches exactly
- Verify modal form field names

### Timeout Errors
- Increase timeouts in `.env`:
  ```env
  TIMEOUT_DEFAULT=60000
  TIMEOUT_NAVIGATION=90000
  ```

## Performance

Expected execution times:
- Login: ~5 seconds
- Per user: ~10-20 seconds (depends on activity count)
- Page navigation: ~3 seconds
- **Total for 100 users: ~20-30 minutes**

## Development

### Adding New Features

1. Update relevant module in `src/`
2. Update tests (when implemented)
3. Update README

### Testing Selectors

Use Playwright's inspector:
```bash
uv run playwright codegen https://mysigma.support/activities/
```

### Debugging

1. Set `HEADLESS=false` in `.env`
2. Set `LOG_LEVEL=DEBUG` in `.env`
3. Add breakpoints or `await page.pause()` in code
4. Run with:
```bash
uv run python main.py
```

## Safety Features

- Credentials stored in `.env` (not in code)
- `.env` added to `.gitignore` (won't be committed)
- Readonly `.gitignore` entries for logs and output
- Comprehensive error logging for debugging
- Graceful shutdown on errors

## License

Private project - not for redistribution

## Support

For issues or questions, contact the development team.
