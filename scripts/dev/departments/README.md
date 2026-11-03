# Development departments

Each folder owns one concern. Edit the department implementation, not orchestration glue.

| Department | Responsibility |
|---|---|
| `workflow` | Run stages and resume workflow state |
| `context` | Build task context and collect evidence |
| `execution` | Run commands and record output |
| `tasks` | Persist task state and incidents |
| `documentation` | Map code changes to documentation review |

Rules are advisory. These scripts report evidence and failures; they do not decide which project files may be edited.

Import examples:

```python
from scripts.dev.departments.tasks import get_task
from scripts.dev.departments.execution import execute_command
from scripts.dev.departments.context import ContextBuilder
from scripts.dev.departments.workflow.engine import WorkflowEngine
```

`controller/` remains a compatibility layer for existing scripts and tests. New development belongs under `departments/`.

## Stock-AI checks

Run focused deterministic checks without contacting a market-data provider:

```powershell
.\scripts\dev\test-stock-ai.ps1 -Suite ai
.\scripts\dev\test-stock-ai.ps1 -Suite offline
.\scripts\dev\test-stock-ai.ps1 -TestPath stock-signal-bot\backend\app\tests\test_backtest_engine.py -Keyword gap
```

Live provider checks are opt-in with `-LiveProvider`. Use `-PythonPath` to select a different interpreter.
