# CRM Helper Automation

A robust, self-healing automation tool for managing CRM activities. It automatically processes "Planned" activities, marks them as "Held", and creates copies with dates distributed evenly across future workdays.

## 🚀 Features

*   **Smart Processing**: Works directly from the Activities list for maximum speed.
*   **Load Balancing**: Distributes new activities evenly across available weekdays (Mon-Fri) using a Round-Robin algorithm.
*   **Self-Healing**: Automatically detects and closes stuck modals or popups to prevent crashes.
*   **Robust Selectors**: Uses structural detection to handle dynamic IDs and Vue.js interfaces.
*   **Pagination Support**: Handles multi-page lists automatically.

## 📋 Prerequisites

*   Python 3.12+
*   `uv` (modern Python package manager)

## 🛠️ Setup

1.  **Clone the repository**
2.  **Install dependencies**:
    ```bash
    uv sync
    ```
3.  **Install Playwright browsers**:
    ```bash
    uv run playwright install chromium
    ```
4.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```env
    LOGIN=your_email@example.com
    PASSWORD=your_password
    BASE_URL=https://mysigma.support
    ```

## ⚙️ Configuration

You can tweak settings in `src/config.py` or via environment variables:

*   `START_DATE`: Start of the scheduling window (e.g., 2026-08-24)
*   `END_DATE`: End of the scheduling window (e.g., 2026-09-30)
*   `HEADLESS`: Set to `False` to watch the browser in action (default: `True`).

## ▶️ Usage

Run the main automation script:

```bash
uv run main.py
```

The script will:
1.  Login to the CRM.
2.  Navigate to the Activities page.
3.  Iterate through all pages.
4.  Find "PLANNED" activities.
5.  Mark them as "HELD".
6.  Create a copy for a future date.
7.  Generate a summary report in `output/`.

## 📂 Output

*   **Logs**: Detailed logs are saved in `logs/` directory.
*   **Reports**: JSON summaries of processed users are saved in `output/`.

## 🤖 For Developers

See [AGENTS.md](AGENTS.md) for detailed architectural documentation, selector strategies, and internal logic description.
