"""GitHub Actions failed runs → unified `ci_failure` events.

Input: `{"run": <gh run view <id> --json ...>, "log_failed": <gh run view <id> --log-failed>}`.
`fetch()` pulls a real failed run with the `gh` CLI (the one optional live source).
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime

from .base import local_hhmm, register, resolve_sender

RUN_FIELDS = "databaseId,headBranch,displayTitle,createdAt,url,workflowName"
_PYTEST_HEADER = re.compile(r"_{3,} (\S+) _{3,}")
_PYTEST_FAILED = re.compile(r"FAILED \S+::(\S+)")
MAX_LOG_LINES = 40


def _tail(log: str) -> str:
    lines = log.rstrip().splitlines()
    for i, line in enumerate(lines):
        if "FAILURES" in line or "##[error]" in line or "Error" in line:
            lines = lines[max(0, i - 2):]
            break
    return "\n".join(lines[-MAX_LOG_LINES:])


@register
class GithubActionsAdapter:
    source = "github_actions"
    event_type = "ci_failure"

    def to_event(self, raw: dict, people: dict) -> dict:
        run, log = raw["run"], raw.get("log_failed", "")
        m = _PYTEST_HEADER.search(log) or _PYTEST_FAILED.search(log)
        created = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
        return {
            "id": f"gha-{run['databaseId']}",
            "time": local_hhmm(created),
            "type": "ci_failure",
            "source": "github_actions",
            "sender": resolve_sender("github", "github-actions[bot]", people),
            "branch": run["headBranch"],
            "test_name": m.group(1) if m else run.get("workflowName", "build"),
            "commit_message": run.get("displayTitle", ""),
            "log_tail": _tail(log),
            "url": run.get("url"),
        }

    def fetch(self, run_id: str | int, repo: str | None = None) -> list[dict]:
        args = ["gh", "run", "view", str(run_id)] + (["-R", repo] if repo else [])
        run = json.loads(subprocess.run(args + ["--json", RUN_FIELDS], check=True, capture_output=True, text=True).stdout)
        log = subprocess.run(args + ["--log-failed"], check=True, capture_output=True, text=True).stdout
        return [{"run": run, "log_failed": log}]
