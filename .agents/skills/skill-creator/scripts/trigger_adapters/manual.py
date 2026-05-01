"""Manual / interactive trigger adapter (stub).

Intended as a fallback for environments that have neither the Claude Code CLI
nor the Kilo CLI available (e.g. Claude.ai).  Prompts the user to confirm
whether the skill was triggered for each query.
"""

from .base import TriggerAdapter


class ManualAdapter(TriggerAdapter):
    """Trigger adapter that asks the user interactively (not yet implemented)."""

    def check_triggered(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: str | None = None,
    ) -> bool:
        raise NotImplementedError(
            "ManualAdapter is not yet implemented. "
            "Use --adapter claude-code (default) instead."
        )
