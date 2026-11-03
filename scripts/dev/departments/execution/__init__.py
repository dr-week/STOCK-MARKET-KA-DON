"""Command execution and output processing."""

from scripts.dev.departments.execution.commands import execute_command
from scripts.dev.departments.execution.summarizer import OutputSummarizer

__all__ = ["execute_command", "OutputSummarizer"]
