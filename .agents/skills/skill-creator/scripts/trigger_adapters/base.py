"""Abstract base class for trigger detection adapters."""

from abc import ABC, abstractmethod


class TriggerAdapter(ABC):
    """Interface for detecting whether a skill description causes a model to trigger.

    Implementations wrap different execution environments (Claude Code CLI,
    Kilo CLI, manual/interactive fallback, etc.) behind a uniform API so that
    ``run_eval.py`` is not hard-wired to any specific tool.
    """

    @abstractmethod
    def check_triggered(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: str | None = None,
    ) -> bool:
        """Return True if the model reads the skill for the given query.

        Args:
            query: The user prompt to test.
            skill_name: The skill's name (used to create a temporary command file).
            skill_description: The description to inject into the command file.
            timeout: Maximum seconds to wait for a result.
            project_root: Absolute path to the project root (where ``.claude/`` lives).
            model: Optional model override passed to the underlying CLI.

        Returns:
            ``True`` if the skill was triggered, ``False`` otherwise.
        """
