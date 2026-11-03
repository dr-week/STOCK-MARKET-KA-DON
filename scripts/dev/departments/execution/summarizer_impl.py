import re
from typing import Dict, Any, Optional, List

class OutputSummarizer:
    """
    Compresses verbose CLI and test outputs into compact, actionable summaries for the AI agent.
    Extracts:
    - Exit code and command
    - First meaningful error
    - Relevant stack trace / assertion failure
    - Context lines
    - Full log disk path
    """

    @staticmethod
    def summarize(command: str, exit_code: int, stdout: str, stderr: str, log_path: str) -> Dict[str, Any]:
        combined = stdout + "\n" + stderr
        lines = combined.splitlines()

        first_error = None
        stack_trace: List[str] = []
        failing_test = None
        suggested_action = "Inspect error details and apply targeted fix."

        # Parse exit code 0
        if exit_code == 0:
            summary_msg = "Command executed successfully."
            # Extract test numbers if available
            test_match = re.search(r"Ran (\d+) tests? in [0-9\.]+s\s+OK", combined)
            if test_match:
                summary_msg = f"All {test_match.group(1)} test(s) passed successfully."
            vitest_match = re.search(r"Test Files\s+(\d+) passed\s+\((\d+)\)", combined)
            if vitest_match:
                summary_msg = f"Vitest: all {vitest_match.group(1)} test suite(s) passed."

            return {
                "command": command,
                "exit_code": 0,
                "status": "PASS",
                "summary": summary_msg,
                "first_error": None,
                "stack_trace": [],
                "full_log_path": log_path
            }

        # Failure parsing: search for first meaningful error line
        in_trace = False
        for idx, line in enumerate(lines):
            l_strip = line.strip()

            # Detect test assertion failures
            if ("FAIL" in line or "AssertionError" in line or "ReferenceError" in line or "TypeError" in line or "SyntaxError" in line) and not first_error:
                first_error = l_strip
                in_trace = True

            # Detect Vitest failures
            if "FAIL" in line and (".test.ts" in line or ".spec.ts" in line):
                failing_test = l_strip

            # Collect stack trace lines
            if in_trace and (line.startswith(" ") or "at " in line or "Traceback" in line or "File " in line):
                if len(stack_trace) < 8:
                    stack_trace.append(l_strip)

            # Detect pnpm manifest errors
            if "ERR_PNPM" in line and not first_error:
                first_error = l_strip
                suggested_action = "Validate package.json syntax or package version."

        if not first_error:
            # Fallback to last non-empty line
            non_empty = [l.strip() for l in lines if l.strip()]
            first_error = non_empty[-1] if non_empty else "Command failed with non-zero exit code"

        return {
            "command": command,
            "exit_code": exit_code,
            "status": "FAIL",
            "first_error": first_error,
            "failing_test": failing_test,
            "stack_trace": stack_trace,
            "suggested_action": suggested_action,
            "full_log_path": log_path,
            "compact_representation": f"Command: {command}\nExit code: {exit_code}\nFirst Error: {first_error}\nLog: {log_path}"
        }

if __name__ == "__main__":
    sample_err = "ReferenceError: renderCandlestickChartSvg is not defined\n at StockDetailWorkspace.ts:266:158"
    summary = OutputSummarizer.summarize("pnpm test", 1, "", sample_err, ".runtime/logs/test.log")
    print(summary["compact_representation"])
