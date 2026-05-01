"""Claude Code CLI trigger adapter.

Uses ``claude -p --output-format stream-json`` to detect whether a skill
description causes the model to read the skill file.  Replaces the original
``select``/``os.read`` approach with ``readline()``-based streaming so the
code works on Windows as well as POSIX.
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from .base import TriggerAdapter


class ClaudeCodeAdapter(TriggerAdapter):
    """Trigger adapter that drives the ``claude`` CLI (Claude Code)."""

    def check_triggered(
        self,
        query: str,
        skill_name: str,
        skill_description: str,
        timeout: int,
        project_root: str,
        model: str | None = None,
    ) -> bool:
        """Run a single query via ``claude -p`` and return whether the skill was triggered."""
        unique_id = uuid.uuid4().hex[:8]
        clean_name = f"{skill_name}-skill-{unique_id}"
        project_commands_dir = Path(project_root) / ".claude" / "commands"
        command_file = project_commands_dir / f"{clean_name}.md"

        try:
            project_commands_dir.mkdir(parents=True, exist_ok=True)
            # Use YAML block scalar to avoid breaking on quotes in description
            indented_desc = "\n  ".join(skill_description.split("\n"))
            command_content = (
                f"---\n"
                f"description: |\n"
                f"  {indented_desc}\n"
                f"---\n\n"
                f"# {skill_name}\n\n"
                f"This skill handles: {skill_description}\n"
            )
            command_file.write_text(command_content)

            cmd = [
                "claude",
                "-p", query,
                "--output-format", "stream-json",
                "--verbose",
                "--include-partial-messages",
            ]
            if model:
                cmd.extend(["--model", model])

            # Remove CLAUDECODE env var to allow nesting claude -p inside a
            # Claude Code session.
            env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=project_root,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # line-buffered
            )

            result_holder: list[bool] = [False]
            done_event = threading.Event()

            def _read_output() -> None:
                triggered = False
                pending_tool_name: str | None = None
                accumulated_json = ""

                try:
                    for raw_line in process.stdout:  # type: ignore[union-attr]
                        if done_event.is_set():
                            break
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Early detection via stream events
                        if event.get("type") == "stream_event":
                            se = event.get("event", {})
                            se_type = se.get("type", "")

                            if se_type == "content_block_start":
                                cb = se.get("content_block", {})
                                if cb.get("type") == "tool_use":
                                    tool_name = cb.get("name", "")
                                    if tool_name in ("Skill", "Read"):
                                        pending_tool_name = tool_name
                                        accumulated_json = ""
                                    else:
                                        result_holder[0] = False
                                        done_event.set()
                                        return

                            elif se_type == "content_block_delta" and pending_tool_name:
                                delta = se.get("delta", {})
                                if delta.get("type") == "input_json_delta":
                                    accumulated_json += delta.get("partial_json", "")
                                    if clean_name in accumulated_json:
                                        result_holder[0] = True
                                        done_event.set()
                                        return

                            elif se_type in ("content_block_stop", "message_stop"):
                                if pending_tool_name:
                                    result_holder[0] = clean_name in accumulated_json
                                    done_event.set()
                                    return
                                if se_type == "message_stop":
                                    result_holder[0] = False
                                    done_event.set()
                                    return

                        # Fallback: full assistant message
                        elif event.get("type") == "assistant":
                            message = event.get("message", {})
                            for content_item in message.get("content", []):
                                if content_item.get("type") != "tool_use":
                                    continue
                                tool_name = content_item.get("name", "")
                                tool_input = content_item.get("input", {})
                                if tool_name == "Skill" and clean_name in tool_input.get("skill", ""):
                                    triggered = True
                                elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                                    triggered = True
                                result_holder[0] = triggered
                                done_event.set()
                                return

                        elif event.get("type") == "result":
                            result_holder[0] = triggered
                            done_event.set()
                            return
                finally:
                    done_event.set()

            reader = threading.Thread(target=_read_output, daemon=True)
            reader.start()

            # Wait for result or timeout
            timed_out = not done_event.wait(timeout=timeout)
            if timed_out:
                print(
                    f"Warning: query timed out after {timeout}s — {query[:60]}",
                    file=sys.stderr,
                )

            # Terminate process regardless
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            except OSError:
                pass

            reader.join(timeout=2)
            return result_holder[0]

        finally:
            if command_file.exists():
                command_file.unlink()
