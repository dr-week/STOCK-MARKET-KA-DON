import sys
import argparse
import json
from scripts.dev.controller.storage import init_db
from scripts.dev.controller.state import create_task, get_task, transition_task
from scripts.dev.controller.commands import execute_command
from scripts.dev.controller.recovery import record_incident
from scripts.dev.controller.documentation import check_doc_sync_status
from scripts.dev.controller.context_builder import ContextBuilder
from scripts.dev.controller.workflow import WorkflowEngine

def cmd_workflow(args):
    init_db()
    engine = WorkflowEngine(run_id=args.run_id)
    files = [f.strip() for f in args.changed_files.split(",") if f.strip()] if args.changed_files else None
    result = engine.run_or_resume(args.task_id, changed_files=files)
    print(json.dumps(result, indent=2))

def cmd_pack(args):
    init_db()
    task = get_task(args.task_id)
    if not task:
        print(f"Task '{args.task_id}' not found.", file=sys.stderr)
        sys.exit(1)

    builder = ContextBuilder()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] if args.symbols else []
    packet = builder.build_packet(
        task_id=args.task_id,
        objective=task["title"],
        skill_name=args.skill or "smkd-safe-edit",
        allowed_paths=task["scope"],
        symbols_to_trace=symbols
    )
    transition_task(args.task_id, "CONTEXT_READY", reason="Context packet built and verified")
    print(json.dumps({"task_id": args.task_id, "status": "CONTEXT_READY", "packet_files": list(packet["context_layers"]["layer_4_retrieved_evidence"]["files"].keys())}, indent=2))

def cmd_create(args):
    init_db()
    scope = [s.strip() for s in args.scope.split(",") if s.strip()] if args.scope else []
    acceptance = [a.strip() for a in args.acceptance.split(",") if a.strip()] if args.acceptance else []
    task = create_task(args.task_id, args.title, scope, acceptance, args.priority)
    print(json.dumps(task, indent=2))

def cmd_status(args):
    init_db()
    task = get_task(args.task_id)
    if not task:
        print(f"Task '{args.task_id}' not found.", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(task, indent=2))

def cmd_run(args):
    init_db()
    task = get_task(args.task_id)
    if not task:
        print(f"Task '{args.task_id}' not found.", file=sys.stderr)
        sys.exit(1)

    if task["status"] in {"READY", "RETRY_PENDING", "BLOCKED", "DONE"}:
        transition_task(args.task_id, "IN_PROGRESS", reason="Command execution started")

    exit_code, stdout, stderr, summary = execute_command(args.task_id, args.command, cwd=args.cwd)
    if args.compact:
        print(summary["compact_representation"])
    else:
        print(stdout + "\n" + stderr)

    if exit_code != 0:
        inc = record_incident(args.task_id, args.command, stdout + "\n" + stderr, exit_code)
        if inc["is_blocked"]:
            print(f"\n[ADVISORY] Repeated failure '{inc['fingerprint']}'. Review diagnostics before retrying.", file=sys.stderr)
    sys.exit(exit_code)

def cmd_verify(args):
    init_db()
    task = get_task(args.task_id)
    if not task:
        print(f"Task '{args.task_id}' not found.", file=sys.stderr)
        sys.exit(1)

    transition_task(args.task_id, "VERIFYING", reason="Verification requested")

    # Scope and doc checks
    changed_files = [f.strip() for f in args.changed_files.split(",") if f.strip()] if args.changed_files else []
    scope_violations = [f for f in changed_files if task["scope"] and f not in task["scope"]]
    if scope_violations:
        print(f"[ADVISORY] Files outside declared scope: {scope_violations}", file=sys.stderr)
    doc_status = check_doc_sync_status(args.task_id, changed_files)

    can_done = (
        args.test_exit == 0
        and doc_status["status"] != "PENDING_SYNC"
    )

    if can_done:
        final_task = transition_task(args.task_id, "DONE", reason="All verification criteria passed")
        print(f"[SUCCESS] Task {args.task_id} verified and moved to DONE.")
    else:
        reasons = []
        if args.test_exit != 0:
            reasons.append(f"Tests failed with exit code {args.test_exit}")
        if doc_status["status"] == "PENDING_SYNC":
            reasons.append(f"Documentation update required: {doc_status['pending_docs']}")

        final_task = transition_task(
            args.task_id,
            "RETRY_PENDING",
            reason="; ".join(reasons),
            next_action="Resolve verification blockers before retrying."
        )
        print(f"[VERIFY FAILED] Task remaining in RETRY_PENDING: {'; '.join(reasons)}")

    print(json.dumps(final_task, indent=2))

def main():
    parser = argparse.ArgumentParser(description="SMKD Local Development Controller CLI")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # create
    p_create = subparsers.add_parser("create")
    p_create.add_argument("--task-id", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--scope", default="")
    p_create.add_argument("--acceptance", default="")
    p_create.add_argument("--priority", default="MEDIUM")
    p_create.set_defaults(func=cmd_create)

    # pack
    p_pack = subparsers.add_parser("pack")
    p_pack.add_argument("--task-id", required=True)
    p_pack.add_argument("--skill", default="smkd-safe-edit")
    p_pack.add_argument("--symbols", default="")
    p_pack.set_defaults(func=cmd_pack)

    # workflow
    p_wf = subparsers.add_parser("workflow")
    p_wf.add_argument("--task-id", required=True)
    p_wf.add_argument("--run-id", default=None)
    p_wf.add_argument("--changed-files", default="")
    p_wf.set_defaults(func=cmd_workflow)

    # status
    p_status = subparsers.add_parser("status")
    p_status.add_argument("--task-id", required=True)
    p_status.set_defaults(func=cmd_status)

    # run
    p_run = subparsers.add_parser("run")
    p_run.add_argument("--task-id", required=True)
    p_run.add_argument("--command", required=True)
    p_run.add_argument("--cwd", default=None)
    p_run.add_argument("--compact", action="store_true", default=False)
    p_run.set_defaults(func=cmd_run)

    # verify
    p_verify = subparsers.add_parser("verify")
    p_verify.add_argument("--task-id", required=True)
    p_verify.add_argument("--changed-files", default="")
    p_verify.add_argument("--test-exit", type=int, default=0)
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
