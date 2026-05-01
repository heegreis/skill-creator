"""Kilo CLI trigger adapter (stub).

Kilo does not yet expose a ``-p`` / non-interactive query mode that is
compatible with the stream-JSON detection used by the Claude Code adapter.
This file is a skeleton that will be filled in once Kilo CLI support is
available.
"""

import sys
from .base import TriggerAdapter


class KiloAdapter(TriggerAdapter):
    """Trigger adapter for the Kilo CLI (not yet implemented)."""

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
            "KiloAdapter is not yet implemented. "
            "Use --adapter claude-code (default) or --adapter manual instead."
        )
