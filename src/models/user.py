import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UserResult(BaseModel):
    """Result of processing a single user."""

    user_index: int = Field(..., description="Index of the user in the list")
    user_name: Optional[str] = Field(None, description="Name of the user (if available)")
    has_planned_activities: bool = Field(
        default=False, description="Whether user had planned activities"
    )
    activities_processed: int = Field(default=0, description="Number of activities processed")
    success: bool = Field(default=True, description="Whether processing was successful")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")

    class Config:
        json_schema_extra = {
            "example": {
                "user_index": 5,
                "user_name": "John Doe",
                "has_planned_activities": True,
                "activities_processed": 3,
                "success": True,
                "error_message": None,
            }
        }


class ProcessingReport(BaseModel):
    """Summary report of the entire processing run."""

    total_users: int = Field(..., description="Total number of users processed")
    successful_users: int = Field(..., description="Number of successfully processed users")
    failed_users: int = Field(..., description="Number of failed user processing attempts")
    users_without_planned: List[int] = Field(
        default_factory=list, description="User indices without planned activities"
    )
    total_activities_processed: int = Field(default=0, description="Total activities processed")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of errors encountered"
    )
    execution_time: float = Field(..., description="Total execution time in seconds")

    def save_to_json(self, output_path: Path) -> None:
        """
        Save report to JSON file.

        Args:
            output_path: Path where to save the report
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    def print_summary(self) -> str:
        """
        Generate human-readable summary.

        Returns:
            Formatted summary string
        """
        summary = [
            "\n" + "=" * 60,
            "CRM Helper - Processing Summary",
            "=" * 60,
            f"Total users processed: {self.total_users}",
            f"Successful: {self.successful_users}",
            f"Failed: {self.failed_users}",
            f"Users without planned activities: {len(self.users_without_planned)}",
            f"Total activities processed: {self.total_activities_processed}",
            f"Execution time: {self.execution_time:.2f}s ({self.execution_time / 60:.2f} minutes)",
            "=" * 60,
        ]

        if self.errors:
            summary.append(f"\nErrors encountered: {len(self.errors)}")
            for i, error in enumerate(self.errors[:5], 1):  # Show first 5 errors
                summary.append(
                    f"  {i}. User {error.get('user_index', 'unknown')}: {error.get('message', 'Unknown error')}"
                )
            if len(self.errors) > 5:
                summary.append(f"  ... and {len(self.errors) - 5} more errors")

        return "\n".join(summary)
