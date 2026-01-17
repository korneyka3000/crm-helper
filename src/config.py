from datetime import date
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Configuration settings for CRM Helper automation."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Authentication credentials
    login: str = Field(..., description="CRM login username/email")
    password: str = Field(..., description="CRM login password")

    # Application URLs
    base_url: str = Field(default="https://mysigma.support", description="Base URL of CRM system")

    # Browser settings
    headless: bool = Field(default=True, description="Run browser in headless mode")

    # Timeout settings (in milliseconds)
    timeout_default: int = Field(default=30000, description="Default timeout (30s)")
    timeout_navigation: int = Field(default=60000, description="Navigation timeout (60s)")
    timeout_modal: int = Field(default=10000, description="Modal appearance timeout (10s)")

    # Retry settings
    retry_max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=2.0, description="Retry delay in seconds")

    # Date range for activity scheduling
    start_date: date = Field(default=date(2026, 8, 24), description="Start date for scheduling")
    end_date: date = Field(default=date(2026, 9, 30), description="End date for scheduling")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: Path = Field(default=Path("logs"), description="Directory for log files")

    # Output settings
    output_dir: Path = Field(default=Path("output"), description="Directory for output files")

    @property
    def accounts_url(self) -> str:
        """Full URL for accounts/login page."""
        return f"{self.base_url}/accounts"

    @property
    def activities_url(self) -> str:
        """Full URL for activities page."""
        return f"{self.base_url}/activities/"

    def ensure_directories(self) -> None:
        """Ensure log and output directories exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
