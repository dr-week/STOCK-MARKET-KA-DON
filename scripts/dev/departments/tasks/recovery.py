"""Failure recording department API."""

from scripts.dev.departments.tasks.recovery_impl import classify_error, record_incident

__all__ = ["classify_error", "record_incident"]
