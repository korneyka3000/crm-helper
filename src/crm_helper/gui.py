import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path

import customtkinter as ctk
from tkcalendar import Calendar

ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def write_env(values: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in values.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return datetime.today().date()


def _parse_holidays(s: str) -> list[date]:
    result = []
    for part in s.split(","):
        part = part.strip()
        if part:
            with suppress(ValueError):
                result.append(datetime.strptime(part, "%Y-%m-%d").date())
    return sorted(result)


def _open_calendar(
    anchor: ctk.CTkBaseClass, initial: date, on_select: Callable[[date], None]
) -> ctk.CTkToplevel:
    """Open a calendar popup positioned below anchor and call on_select with the chosen date."""
    popup = ctk.CTkToplevel(anchor)
    popup.title("")
    popup.resizable(False, False)
    popup.transient(anchor.winfo_toplevel())

    anchor.update_idletasks()
    x = anchor.winfo_rootx()
    y = anchor.winfo_rooty() + anchor.winfo_height() + 2
    popup.geometry(f"+{x}+{y}")

    cal = Calendar(
        popup,
        selectmode="day",
        date_pattern="yyyy-mm-dd",
        year=initial.year,
        month=initial.month,
        day=initial.day,
        font=("", 12),
    )
    cal.pack(padx=8, pady=(8, 4))

    def confirm():
        selected = datetime.strptime(cal.get_date(), "%Y-%m-%d").date()
        popup.destroy()
        on_select(selected)

    ctk.CTkButton(popup, text="Select", command=confirm).pack(pady=(0, 8))
    popup.grab_set()
    return popup


class DatePicker(ctk.CTkFrame):
    def __init__(self, master, initial: date | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._date = initial or datetime.today().date()
        self._popup: ctk.CTkToplevel | None = None

        self._entry = ctk.CTkEntry(self, width=110)
        self._entry.insert(0, self._date.strftime("%Y-%m-%d"))
        self._entry.pack(side="left", padx=(0, 4))

        ctk.CTkButton(self, text="...", width=32, command=self._open).pack(side="left")

    def _open(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._popup.focus()
            return

        def on_select(d: date):
            self._date = d
            self._entry.delete(0, "end")
            self._entry.insert(0, d.strftime("%Y-%m-%d"))

        self._popup = _open_calendar(self._entry, _parse_date(self._entry.get()), on_select)

    def get_date(self) -> date:
        return _parse_date(self._entry.get())


class HolidayPicker(ctk.CTkFrame):
    def __init__(self, master, initial: list[date] | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._dates: list[date] = initial or []
        self._popup: ctk.CTkToplevel | None = None

        self._list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._list_frame.pack(fill="x")

        self._add_btn = ctk.CTkButton(self, text="+ Add holiday", width=160, command=self._open)
        self._add_btn.pack(anchor="w", pady=(4, 0))

        self._refresh()

    def _refresh(self) -> None:
        for w in self._list_frame.winfo_children():
            w.destroy()
        for d in self._dates:
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=d.strftime("%Y-%m-%d"), width=110, anchor="w").pack(side="left")
            ctk.CTkButton(
                row,
                text="×",  # noqa: RUF001
                width=28,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                command=lambda dd=d: self._remove(dd),
            ).pack(side="left")

    def _remove(self, d: date) -> None:
        self._dates.remove(d)
        self._refresh()

    def _open(self) -> None:
        if self._popup and self._popup.winfo_exists():
            self._popup.focus()
            return

        def on_select(d: date):
            if d not in self._dates:
                self._dates.append(d)
                self._dates.sort()
                self._refresh()

        self._popup = _open_calendar(self._add_btn, datetime.today().date(), on_select)

    def get_value(self) -> str:
        return ",".join(d.strftime("%Y-%m-%d") for d in self._dates)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CRM Helper — Config")
        self.resizable(False, False)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._env = read_env()
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._date_pickers: dict[str, DatePicker] = {}
        self._headless_var = ctk.BooleanVar(
            value=self._env.get("HEADLESS", "True").lower() == "true"
        )

        pad = {"padx": 16, "pady": 6}

        for key, label, masked in [
            ("LOGIN", "Login", False),
            ("PASSWORD", "Password", True),
        ]:
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", **pad)
            entry = ctk.CTkEntry(self, width=340, show="•" if masked else "")
            entry.insert(0, self._env.get(key, ""))
            entry.pack(fill="x", **pad)
            self._entries[key] = entry

        # Date range side by side
        date_frame = ctk.CTkFrame(self, fg_color="transparent")
        date_frame.pack(fill="x", padx=16, pady=6)
        date_frame.columnconfigure(0, weight=1)
        date_frame.columnconfigure(1, weight=1)

        date_fields = [("START_DATE", "Start date"), ("END_DATE", "End date")]
        for col, (key, label) in enumerate(date_fields):
            px = (0, 8) if col == 0 else (8, 0)
            ctk.CTkLabel(date_frame, text=label, anchor="w").grid(
                row=0, column=col, sticky="ew", padx=px
            )
            dp = DatePicker(date_frame, initial=_parse_date(self._env.get(key, "")))
            dp.grid(row=1, column=col, sticky="w", padx=px, pady=(2, 0))
            self._date_pickers[key] = dp

        # Holidays
        ctk.CTkLabel(self, text="Holidays", anchor="w").pack(fill="x", **pad)
        self._holiday_picker = HolidayPicker(
            self, initial=_parse_holidays(self._env.get("HOLIDAYS", ""))
        )
        self._holiday_picker.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Headless mode", anchor="w").pack(fill="x", **pad)
        ctk.CTkSwitch(self, text="", variable=self._headless_var).pack(anchor="w", **pad)

        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(**pad)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(4, 16))
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(
            side="left", expand=True, padx=(0, 6)
        )
        ctk.CTkButton(btn_frame, text="Save & Run", command=self._save_and_run).pack(
            side="left", expand=True
        )

    def _collect(self) -> dict[str, str]:
        values = {key: entry.get().strip() for key, entry in self._entries.items()}
        for key, dp in self._date_pickers.items():
            values[key] = dp.get_date().strftime("%Y-%m-%d")
        values["HOLIDAYS"] = self._holiday_picker.get_value()
        values["HEADLESS"] = str(self._headless_var.get())
        return values

    def _save(self) -> None:
        write_env(self._collect())
        self._status.configure(text="Saved ✓", text_color="green")

    def _save_and_run(self) -> None:
        self._save()
        subprocess.Popen([sys.executable, "-m", "crm_helper.main"])
        self._status.configure(text="Running…", text_color="gray")


if __name__ == "__main__":
    App().mainloop()
