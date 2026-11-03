from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.dev.departments.context import builder_impl
from scripts.dev.departments.execution import commands_impl
from scripts.dev.departments.tasks import recovery_impl, storage_impl
from scripts.dev.departments.workflow.engine import WorkflowEngine
from scripts.dev.departments.workflow import engine_impl
from scripts.dev.departments.tasks.storage import init_db


class IsolatedDevRuntime:
    def __init__(self):
        self._temp_dir = TemporaryDirectory()
        runtime_dir = Path(self._temp_dir.name)
        self._patches = [
            patch.object(storage_impl, "RUNTIME_DIR", str(runtime_dir)),
            patch.object(storage_impl, "DB_PATH", str(runtime_dir / "dev-control.sqlite")),
            patch.object(engine_impl, "WORKFLOWS_DIR", str(runtime_dir / "workflows")),
            patch.object(builder_impl, "PACKETS_DIR", str(runtime_dir / "packets")),
            patch.object(recovery_impl, "INCIDENTS_DIR", str(runtime_dir / "incidents")),
            patch.object(commands_impl, "LOGS_DIR", str(runtime_dir / "logs")),
        ]

    def start(self):
        for item in self._patches:
            item.start()
        init_db()
        return self

    def stop(self):
        for item in reversed(self._patches):
            item.stop()
        self._temp_dir.cleanup()


def create_test_workflow(run_id, stage_results=None):
    engine = WorkflowEngine(run_id=run_id)
    original_execute_stage = engine._execute_stage
    stage_results = stage_results or {}

    def execute_stage(stage, task, files, focused_cmd, regression_cmds):
        if stage in stage_results:
            return stage_results[stage]
        if stage in {"validate-environment", "run-focused-tests", "run-required-checks"}:
            return True, 0, "External command stage isolated by unit test."
        return original_execute_stage(stage, task, files, focused_cmd, regression_cmds)

    engine._execute_stage = execute_stage
    return engine
