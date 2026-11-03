"""Compatibility exports for task state operations."""

from scripts.dev.departments.tasks.state import create_task, get_task, transition_task

__all__ = ["create_task", "get_task", "transition_task"]
