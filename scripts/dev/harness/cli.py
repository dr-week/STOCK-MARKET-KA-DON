"""
Unified CLI for SMKD AI Agent Harness.
"""

import sys
import argparse
import json

from scripts.dev.harness.doctor import EnvironmentDoctor
from scripts.dev.harness.detector import DuplicateDetector
from scripts.dev.harness.integrity_validator import MarketDataIntegrityValidator
from scripts.dev.harness.evaluator import AgentEvaluationHarness
from scripts.dev.harness.orchestrator import AgentOrchestrator


def cmd_doctor(args):
    doctor = EnvironmentDoctor()
    res = doctor.run_all_checks()
    for item in res["checks"]:
        lvl = item["level"]
        msg = item["message"]
        color = "\033[92m" if lvl == "PASS" else ("\033[93m" if lvl == "WARN" else "\033[91m")
        reset = "\033[0m"
        print(f"{color}[{lvl}]{reset} {msg}")
    print(f"\nDoctor Summary: {'PASSED' if res['passed'] else 'FAILED'}")
    sys.exit(res["exit_code"])


def cmd_eval(args):
    harness = AgentEvaluationHarness()
    print("Running AI Agent Safeguards and Evaluation Suite...")
    report = harness.run_suite()
    print("\nEvaluation Results:")
    for test in report["tests"]:
        st = test["status"]
        name = test["name"]
        color = "\033[92m" if st == "PASS" else "\033[91m"
        reset = "\033[0m"
        detail = test.get("detail") or test.get("error") or ""
        print(f"  {color}[{st}]{reset} {name} - {detail}")

    print(f"\nSuite Completed: {report['passed']} Passed, {report['failed']} Failed.")
    if args.json:
        print(json.dumps(report, indent=2))
    sys.exit(0 if report["failed"] == 0 else 1)


def cmd_duplicate_check(args):
    detector = DuplicateDetector()
    res = detector.check(args.target, search_root=args.root)
    print(json.dumps(res, indent=2))
    sys.exit(0)


def cmd_validate_integrity(args):
    validator = MarketDataIntegrityValidator()
    res = validator.scan_production_paths_for_synthetic_leaks()
    print(f"Scanned {res['files_scanned']} production files.")
    if res["valid"]:
        print("\033[92m[PASS]\033[0m Zero synthetic or fixture leaks found in production paths.")
        sys.exit(0)
    else:
        print(f"\033[91m[FAIL]\033[0m Found {len(res['leaks_found'])} synthetic leaks:")
        for leak in res["leaks_found"]:
            print(f"  - {leak}")
        sys.exit(1)


def cmd_orchestrate(args):
    orchestrator = AgentOrchestrator()
    files = [f.strip() for f in args.files.split(",") if f.strip()] if args.files else None
    res = orchestrator.run_pipeline(args.task_id, changed_files=files)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res.get("status") == "COMPLETED" else 1)


def main():
    parser = argparse.ArgumentParser(description="SMKD AI Agent Harness & Quality Validation Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run preflight environment checks")
    p_doc.set_defaults(func=cmd_doctor)

    # eval
    p_eval = subparsers.add_parser("eval", help="Run AI agent safeguards evaluation suite")
    p_eval.add_argument("--json", action="store_true", help="Output full JSON report")
    p_eval.set_defaults(func=cmd_eval)

    # duplicate-check
    p_dup = subparsers.add_parser("duplicate-check", help="Scan codebase for duplicate capabilities")
    p_dup.add_argument("--target", required=True, help="Name of component or capability to check")
    p_dup.add_argument("--root", default=None, help="Root directory to search")
    p_dup.set_defaults(func=cmd_duplicate_check)

    # validate-integrity
    p_val = subparsers.add_parser("validate-integrity", help="Verify market data integrity & leak checks")
    p_val.set_defaults(func=cmd_validate_integrity)

    # orchestrate
    p_orch = subparsers.add_parser("orchestrate", help="Orchestrate multi-stage task pipeline")
    p_orch.add_argument("--task-id", required=True, help="Task ID")
    p_orch.add_argument("--files", default=None, help="Comma-separated changed files")
    p_orch.set_defaults(func=cmd_orchestrate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
