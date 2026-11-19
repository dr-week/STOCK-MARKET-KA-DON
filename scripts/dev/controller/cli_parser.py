import argparse
from typing import Callable, Dict


def build_cli_parser(handlers: Dict[str, Callable]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SMKD Local Development Controller CLI")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # create
    p_create = subparsers.add_parser("create")
    p_create.add_argument("--task-id", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--scope", default="")
    p_create.add_argument("--acceptance", default="")
    p_create.add_argument("--priority", default="MEDIUM")
    p_create.set_defaults(func=handlers["create"])

    # pack
    p_pack = subparsers.add_parser("pack")
    p_pack.add_argument("--task-id", required=True)
    p_pack.add_argument("--skill", default="smkd-safe-edit")
    p_pack.add_argument("--symbols", default="")
    p_pack.set_defaults(func=handlers["pack"])

    # workflow
    p_wf = subparsers.add_parser("workflow")
    p_wf.add_argument("--task-id", required=True)
    p_wf.add_argument("--run-id", default=None)
    p_wf.add_argument("--changed-files", default="")
    p_wf.set_defaults(func=handlers["workflow"])

    # status
    p_status = subparsers.add_parser("status")
    p_status.add_argument("--task-id", required=True)
    p_status.set_defaults(func=handlers["status"])

    # run
    p_run = subparsers.add_parser("run")
    p_run.add_argument("--task-id", required=True)
    p_run.add_argument("--command", required=True)
    p_run.add_argument("--cwd", default=None)
    p_run.add_argument("--compact", action="store_true", default=False)
    p_run.set_defaults(func=handlers["run"])

    # verify
    p_verify = subparsers.add_parser("verify")
    p_verify.add_argument("--task-id", required=True)
    p_verify.add_argument("--changed-files", default="")
    p_verify.add_argument("--test-exit", type=int, default=0)
    p_verify.set_defaults(func=handlers["verify"])

    return parser
