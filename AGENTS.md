# Developer Guide & Agent Context

This document contains technical details, architectural decisions, and best practices for future developers and AI agents working on this codebase.

## 🧠 Project Architecture

The project is designed as an automated CRM helper using **Playwright** for browser automation. It focuses on robustness and "self-healing" capabilities to handle dynamic web interfaces.

### Core Components

1.  **`main.py`**: The entry point.
    *   Iterates through pages of the Activities list (`/activities/`).
    *   Manages the high-level loop (Row 0 to 99).
    *   **CRITICAL**: Does NOT reload the page after every action to preserve row order and speed.
2.  **`src/automation/activities_page.py`**: Page Object for the list view.
    *   Handles navigation and pagination.
    *   Uses smart waits (timeout + visibility check) for pagination instead of flaky `networkidle`.
3.  **`src/automation/user_processor.py`**: The heavy lifter.
    *   Processes individual rows *directly in the list* (Preferred) or via Details page (Fallback).
    *   **Self-Healing**: Automatically detects and forces close stuck modals using `_ensure_modal_closed()`.
4.  **`src/date_distributor.py`**:
    *   Implements Round-Robin date assignment (Mon-Fri only) to ensure even workload distribution.

## 🔍 Selectors Strategy (The "Why")

We discovered through inspection that standard attributes (ID, Name) are often missing or unstable (Vue.js `data-v-...`). Therefore, we rely on **Structural and Text-based Selectors**.

### Activities List (`/activities/`)
*   **Row**: `#activity-table-false tbody tr:not(:has-text("Loading"))`
    *   We explicitly filter out "Loading" rows to avoid trying to interact with skeletons.
*   **Status**: `span[title="PLANNED"]`
    *   Case-insensitive check in code is safer, but this selector finds the element.
*   **Pagination**: `li.pagination__item:not(.disabled) a:has-text("Next")`
    *   The button is an `<a>` inside an `<li>`.

### Modals
The "Copy Activity" modal lacks `name` or `id` attributes on inputs.
*   **Description**: `textarea.form-control` (Unique in modal).
*   **Start Date**: `.datepicker-div input` (First one in modal).
*   **Scope**: Always scope selectors to `.modal:visible` to avoid ghost elements.

## 🛡️ Best Practices for this Codebase

1.  **Direct List Processing**: Always prefer interacting with buttons ("Mark as HELD", "Copy") directly in the table row. It is 10x faster than opening the details page.
2.  **Modal Management**: Modals are sticky. Always verify they are closed. If an interaction fails, check for a blocking modal first.
3.  **No Page Reloads**: The activity list is dynamic. Reloading shifts rows and causes skips. Iterate through the visible DOM elements.
4.  **Robust Pagination**: `networkidle` is a lie on this SPA. Use `wait_for_timeout(3000)` + `wait_for_selector` for the next page's rows.
5.  **Round-Robin Dates**: Do not use `random`. The `DateDistributor` ensures perfect load balancing.

## 🛠️ Debugging Tips

*   **Logs**: Check `logs/` directory. Each run creates a timestamped log.
*   **Screenshots**: If adding new features, use `page.screenshot()` on failure to see what the bot sees.
*   **Strict Mode**: Playwright is strict. If you see "strict mode violation", use `.first` or refine the selector.

## 🔄 Workflow Logic

1.  Login to `/accounts`.
2.  Navigate to `/activities/`.
3.  Loop Pages:
    *   Loop Rows (0..100):
        *   Check for `span[title="PLANNED"]`.
        *   If found: Click HELD -> Click Copy -> Fill Modal -> Save.
        *   If not found: Skip.
    *   Click "Next" -> Wait for table refresh.
