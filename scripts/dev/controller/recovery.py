"""Compatibility exports for task failure recording."""

from scripts.dev.departments.tasks.recovery import classify_error, record_incident

__all__ = ["classify_error", "record_incident"]
