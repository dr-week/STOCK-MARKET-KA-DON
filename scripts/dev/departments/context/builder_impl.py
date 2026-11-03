import os
import json
import glob
from typing import Dict, Any, List, Optional, Set
from scripts.dev.departments.tasks.storage import RUNTIME_DIR

PACKETS_DIR = os.path.join(RUNTIME_DIR, "packets")

class ContextBuilder:
    """
    Assembles a machine-readable, 4-layer bounded task context packet:
    Layer 1: Project rules (AGENTS.md core excerpt)
    Layer 2: Procedural skill (Single relevant SKILL.md)
    Layer 3: Task packet (Objective, allowed_paths, protected_paths, acceptance criteria)
    Layer 4: Retrieved evidence (Source snippets, caller sites, diffs, relevant tests)
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

    def build_packet(
        self,
        task_id: str,
        objective: str,
        skill_name: str,
        allowed_paths: List[str],
        protected_paths: Optional[List[str]] = None,
        required_behavior: Optional[List[str]] = None,
        verification: Optional[List[str]] = None,
        symbols_to_trace: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        os.makedirs(PACKETS_DIR, exist_ok=True)

        # 1. Project Rules Excerpt
        rules_excerpt = self._get_rules_excerpt()

        # 2. Procedural Skill
        skill_content = self._get_skill_content(skill_name)

        # 3. Retrieved Evidence (File excerpts + Call sites + Diffs)
        evidence = self._retrieve_evidence(allowed_paths, symbols_to_trace or [])

        # Protection is opt-in. Context packets should describe work, not prevent edits.
        protected = protected_paths or []

        packet = {
            "task_id": task_id,
            "objective": objective,
            "selected_skill": skill_name,
            "allowed_paths": allowed_paths,
            "protected_paths": protected,
            "required_behavior": required_behavior or [
                "Make smallest correct change",
                "Preserve existing changes and database files",
                "Never generate synthetic fake data"
            ],
            "verification": verification or [
                "Execute focused test",
                "Verify workspace build"
            ],
            "stop_conditions": [
                "Target file cannot be located",
                "Same tool operation fails twice",
                "Unrelated file must be edited"
            ],
            "context_layers": {
                "layer_1_project_rules": rules_excerpt,
                "layer_2_procedural_skill": skill_content,
                "layer_4_retrieved_evidence": evidence
            }
        }

        # Write to .runtime/packets/<task-id>.json
        packet_path = os.path.join(PACKETS_DIR, f"{task_id}.json")
        packet_str = json.dumps(packet, indent=2)
        # Approximate token estimate (1 token ~= 4 chars)
        approx_tokens = len(packet_str) // 4
        packet["estimated_tokens"] = approx_tokens

        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)

        return packet

    def _get_rules_excerpt(self) -> str:
        agents_md = os.path.join(self.workspace_root, "AGENTS.md")
        if os.path.exists(agents_md):
            with open(agents_md, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[:45])  # First 45 lines contain permission tiers & rules
        return "Operate autonomously under AUTO; ask first for destructive operations."

    def _get_skill_content(self, skill_name: str) -> str:
        skill_path = os.path.join(self.workspace_root, ".agents", "skills", skill_name, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"Standard procedure for {skill_name}"

    def _retrieve_evidence(self, allowed_paths: List[str], symbols: List[str]) -> Dict[str, Any]:
        evidence = {
            "files": {},
            "callers": {},
            "git_diffs": {}
        }

        # Read allowed files (or first 120 lines if large)
        for rel_path in allowed_paths:
            full_path = os.path.join(self.workspace_root, rel_path.replace("/", os.sep))
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content_lines = f.readlines()
                    snippet = "".join(content_lines[:150])
                    evidence["files"][rel_path] = {
                        "total_lines": len(content_lines),
                        "snippet": snippet
                    }

        # Search callers for key symbols
        for sym in symbols:
            matched_lines = []
            for ext in ["*.ts", "*.py"]:
                for root_dir in ["fast-framework/packages/stock-bot-ui/src", "stock-signal-bot/backend/app"]:
                    search_path = os.path.join(self.workspace_root, root_dir, "**", ext)
                    for filepath in glob.glob(search_path, recursive=True):
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                                for idx, line in enumerate(f, 1):
                                    if sym in line:
                                        rel = os.path.relpath(filepath, self.workspace_root).replace(os.sep, "/")
                                        matched_lines.append(f"{rel}:{idx}: {line.strip()}")
                        except Exception:
                            pass
            evidence["callers"][sym] = matched_lines[:10]  # Limit to 10 most relevant call sites

        return evidence

if __name__ == "__main__":
    builder = ContextBuilder()
    pkt = builder.build_packet(
        task_id="SMKD-CHART-001",
        objective="Render real historical candles",
        skill_name="smkd-safe-edit",
        allowed_paths=[
            "fast-framework/packages/stock-bot-ui/src/components/LiveCandleChart.ts",
            "fast-framework/packages/stock-bot-ui/src/departments/StockDetailWorkspace.ts"
        ],
        symbols_to_trace=["renderLiveCandleChart", "candles_5m"]
    )
    print(f"Generated task packet: {pkt['task_id']} with {len(pkt['context_layers']['layer_4_retrieved_evidence']['files'])} files retrieved.")
