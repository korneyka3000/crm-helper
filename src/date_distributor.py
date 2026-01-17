from datetime import date, timedelta
from typing import List


class DateDistributor:
    """
    Distributes dates evenly across weekdays (Monday-Friday) using round-robin algorithm.

    Excludes weekends (Saturday and Sunday) and ensures even distribution of activities
    across all available weekdays in the specified date range.
    """

    def __init__(self, start_date: date, end_date: date):
        """
        Initialize DateDistributor with a date range.

        Args:
            start_date: Start date for scheduling range
            end_date: End date for scheduling range
        """
        self.start_date = start_date
        self.end_date = end_date
        self.weekdays: List[date] = self._calculate_weekdays()
        self.current_index: int = 0

        if not self.weekdays:
            raise ValueError(f"No weekdays found in range {start_date} to {end_date}")

    def _calculate_weekdays(self) -> List[date]:
        """
        Calculate all weekdays (Mon-Fri) in the date range.

        Returns:
            List of weekday dates in chronological order
        """
        weekdays = []
        current = self.start_date

        while current <= self.end_date:
            # isoweekday(): Monday=1, ..., Friday=5, Saturday=6, Sunday=7
            if current.isoweekday() not in [6, 7]:
                weekdays.append(current)
            current += timedelta(days=1)

        return weekdays

    def get_next_date(self) -> str:
        """
        Get the next date in round-robin fashion.

        Returns:
            Date string in format "YYYY-MM-DD 00:00"
        """
        if not self.weekdays:
            raise RuntimeError("No weekdays available for distribution")

        # Get current date
        current_date = self.weekdays[self.current_index]

        # Increment and wrap around
        self.current_index = (self.current_index + 1) % len(self.weekdays)

        # Format as required by CRM
        return current_date.strftime("%Y-%m-%d 00:00")

    def reset(self) -> None:
        """Reset the distributor to start from the first date."""
        self.current_index = 0

    def get_weekday_count(self) -> int:
        """Get the total number of weekdays in the range."""
        return len(self.weekdays)

    def get_weekdays(self) -> List[str]:
        """
        Get all weekdays as formatted strings.

        Returns:
            List of all weekday dates in "YYYY-MM-DD 00:00" format
        """
        return [d.strftime("%Y-%m-%d 00:00") for d in self.weekdays]
