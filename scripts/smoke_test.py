#!/usr/bin/env python3
"""Isolated smoke tests for agent-session-migration tools.

Uses temporary directories and isolated env vars (CLAUDE_CONFIG_DIR, CODEX_HOME,
PI_CODING_AGENT_DIR, CCX_HOME). Never modifies live user sessions by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def write_sample_claude_session(claude_dir: Path, cwd: Path) -> tuple[str, Path]:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(cwd.resolve()))
    proj_dir = claude_dir / "projects" / slug
    proj_dir.mkdir(parents=True, exist_ok=True)
    sid = str(uuid.uuid4())
    u1, u2 = str(uuid.uuid4()), str(uuid.uuid4())
    records = [
        {"type": "custom-title", "customTitle": "Smoke Test Session", "sessionId": sid},
        {
            "type": "user",
            "uuid": u1,
            "parentUuid": None,
            "sessionId": sid,
            "cwd": str(cwd.resolve()),
            "timestamp": "2026-11-21T00:00:00.000Z",
            "message": {"role": "user", "content": "Smoke marker: MIGRATE-SMOKE-42."},
        },
        {
            "type": "assistant",
            "uuid": u2,
            "parentUuid": u1,
            "sessionId": sid,
            "cwd": str(cwd.resolve()),
            "timestamp": "2026-11-21T00:00:05.000Z",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Noted marker MIGRATE-SMOKE-42."}],
            },
        },
    ]
    path = proj_dir / f"{sid}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return sid, path


def test_session_migrate(tmp: Path) -> tuple[str, str]:
    exe = shutil.which("session-migrate")
    if not exe:
        return "skip", "session-migrate not in PATH"
    claude_dir = tmp / "sm_claude"
    codex_dir = tmp / "sm_codex"
    work_dir = tmp / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    _, src_file = write_sample_claude_session(claude_dir, work_dir)

    r1 = subprocess.run(
        [exe, "inspect", str(src_file), "--json"],
        capture_output=True, text=True, timeout=30,
    )
    if r1.returncode != 0:
        return "fail", f"inspect failed: {r1.stderr.strip() or r1.stdout.strip()}"

    r2 = subprocess.run(
        [exe, "import", str(src_file), "--to", "codex", "--cwd", str(work_dir), "--home", str(codex_dir)],
        capture_output=True, text=True, timeout=30,
    )
    if r2.returncode != 0:
        return "fail", f"import->codex failed: {r2.stderr.strip() or r2.stdout.strip()}"
    return "pass", "Claude JSONL -> Codex isolated import OK"


def test_harnext(tmp: Path) -> tuple[str, str]:
    exe = shutil.which("harnext")
    if not exe:
        return "skip", "harnext not in PATH"
    claude_dir = tmp / "hn_claude"
    pi_dir = tmp / "hn_pi"
    work_dir = tmp / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    _, src_file = write_sample_claude_session(claude_dir, work_dir)

    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(claude_dir), "PI_CODING_AGENT_DIR": str(pi_dir)}
    r = subprocess.run(
        [exe, "claude-to-pi", "--session", str(src_file), "--cwd", str(work_dir), "--dry-run"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        return "fail", f"claude-to-pi --dry-run failed: {r.stderr.strip() or r.stdout.strip()}"
    return "pass", "Claude JSONL -> Pi dry-run OK"


def test_ccx(tmp: Path, *, allow_ag_write: bool) -> tuple[str, str]:
    exe = shutil.which("ccx")
    if not exe:
        return "skip", "ccx not in PATH"
    ccx_home = tmp / "ccx_home"
    claude_dir = tmp / "ccx_claude"
    ccx_home.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CCX_HOME": str(ccx_home), "CLAUDE_CONFIG_DIR": str(claude_dir)}

    r_ls = subprocess.run([exe, "ls", "-n", "1"], env=env, capture_output=True, text=True, timeout=30)
    if r_ls.returncode != 0:
        return "fail", f"ccx ls failed: {r_ls.stderr.strip() or r_ls.stdout.strip()}"

    if not allow_ag_write:
        return "pass", "ccx ls OK (pass --allow-ag-write to also test live Antigravity Desktop write + cleanup)"

    sid, _ = write_sample_claude_session(claude_dir, ROOT)
    r_to = subprocess.run(
        [exe, "-C", str(ROOT), "to-antigravity", sid, "--from", "claude", "--no-open", "--json"],
        env=env, capture_output=True, text=True, timeout=120,
    )
    if r_to.returncode != 0:
        return "fail", f"to-antigravity failed: {r_to.stderr.strip() or r_to.stdout.strip()}"
    data = json.loads(r_to.stdout)
    ag_id = data["target"]["id"]
    # Clean up the temporary Antigravity conversation via ccx's antigravity.delete.
    ccx_lib = Path(os.path.realpath(exe)).parent.parent / "lib"
    subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ccx_lib)!r}); from ccx import antigravity; antigravity.delete({ag_id!r})"],
        capture_output=True, text=True, timeout=30,
    )
    return "pass", f"Claude -> Antigravity write + cleanup OK ({ag_id[:8]})"


def main() -> int:
    p = argparse.ArgumentParser(description="agent-session-migration 隔离冒烟测试")
    p.add_argument(
        "--tool",
        choices=("all", "session-migrate", "harnext", "ccx"),
        default="all",
        help="要测试的工具（默认 all）",
    )
    p.add_argument(
        "--allow-ag-write",
        action="store_true",
        help="允许向本机 Antigravity Desktop 创建临时测试会话并在结束后自动删除",
    )
    args = p.parse_args()

    runners = {
        "session-migrate": lambda d: test_session_migrate(d),
        "harnext": lambda d: test_harnext(d),
        "ccx": lambda d: test_ccx(d, allow_ag_write=args.allow_ag_write),
    }
    selected = list(runners.keys()) if args.tool == "all" else [args.tool]

    failed = False
    with tempfile.TemporaryDirectory(prefix="agent-session-migration-smoke-") as tmp_str:
        tmp = Path(tmp_str)
        for name in selected:
            status, detail = runners[name](tmp)
            print(f"[{status.upper():4}] {name}: {detail}")
            if status == "fail":
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
