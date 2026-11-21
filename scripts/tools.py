#!/usr/bin/env python3
"""Manage pinned session migration tools: doctor, install, check-updates."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TOOLS_FILE = ROOT / "tools.json"
SEMVER_RE = re.compile(r"\b(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\b")


def load_tools() -> dict[str, dict[str, Any]]:
    return json.loads(TOOLS_FILE.read_text(encoding="utf-8"))


def parse_version(text: str) -> str | None:
    m = SEMVER_RE.search(text or "")
    return m.group(1) if m else None


def version_key(ver: str) -> tuple[tuple[int, ...], int, str]:
    core, _, pre = ver.lstrip("v").partition("-")
    nums = tuple(int(x) for x in core.split(".") if x.isdigit())
    # Stable release sorts after pre-release of the same core version.
    return (nums, 1 if not pre else 0, pre)


def is_newer(latest: str, pinned: str) -> bool:
    if latest.lstrip("v") == pinned.lstrip("v"):
        return False
    return version_key(latest) > version_key(pinned)


def http_json(url: str, *, github: bool = False) -> Any:
    headers = {"User-Agent": "agent-session-migration-tools/1.0", "Accept": "application/json"}
    if github:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_latest(spec: dict[str, Any]) -> tuple[str | None, str | None]:
    src = spec["source"]
    try:
        if src == "pypi":
            pkg = urllib.parse.quote(spec["package"])
            data = http_json(f"https://pypi.org/pypi/{pkg}/json")
            return data["info"]["version"], None
        if src == "npm":
            pkg = urllib.parse.quote(spec["package"], safe="@/")
            data = http_json(f"https://registry.npmjs.org/{pkg}/latest")
            return data["version"], None
        if src == "github-release":
            repo = spec["repo"]
            try:
                data = http_json(f"https://api.github.com/repos/{repo}/releases/latest", github=True)
                tag = data.get("tag_name") or ""
                ver = parse_version(tag) or tag.lstrip("v")
                return (ver or None), None
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
            tags = http_json(f"https://api.github.com/repos/{repo}/tags?per_page=10", github=True)
            for item in tags:
                ver = parse_version(item.get("name") or "")
                if ver:
                    return ver, None
            return None, "no release or semver tag found"
        return None, f"unsupported source: {src}"
    except Exception as exc:
        return None, str(exc)


def probe_tool(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    pinned = spec["version"]
    cmd = spec.get("command")
    path = shutil.which(cmd) if cmd else None

    if name == "dsh-chat-import":
        return {
            "name": name,
            "pinned": pinned,
            "installed": None,
            "path": path,
            "status": "manual" if path else "missing-host",
            "note": "DSH 插件按 profile 管理，需在 web/desktop profile 内核对版本",
        }

    if not path:
        return {
            "name": name,
            "pinned": pinned,
            "installed": None,
            "path": None,
            "status": "missing",
            "note": f"未找到命令 `{cmd}`",
        }

    args = spec.get("version_args", ["--version"])
    try:
        proc = subprocess.run([path, *args], capture_output=True, text=True, timeout=15)
        raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
        installed = parse_version(raw)
    except Exception as exc:
        return {
            "name": name,
            "pinned": pinned,
            "installed": None,
            "path": path,
            "status": "error",
            "note": str(exc),
        }

    if not installed:
        status = "unknown"
        note = "无法解析版本号"
    elif installed == pinned:
        status = "ok"
        note = ""
    else:
        status = "mismatch"
        note = f"已装 {installed}，锁定 {pinned}"

    return {
        "name": name,
        "pinned": pinned,
        "installed": installed,
        "path": path,
        "status": status,
        "note": note,
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    tools = load_tools()
    results = [probe_tool(name, spec) for name, spec in tools.items()]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"{'Tool':<18} {'Pinned':<10} {'Installed':<10} {'Status':<14} Note")
        print("-" * 76)
        for r in results:
            inst = r["installed"] or "-"
            print(f"{r['name']:<18} {r['pinned']:<10} {inst:<10} {r['status']:<14} {r['note']}")
    return 0


def run_step(cmd: list[str], *, dry_run: bool) -> int:
    print("+", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def install_one(name: str, spec: dict[str, Any], *, dry_run: bool, force: bool) -> int:
    ver = spec["version"]
    if name == "session-migrate":
        cmd = ["uv", "tool", "install"]
        if force:
            cmd.append("--force")
        cmd.append(f"{spec['package']}=={ver}")
        return run_step(cmd, dry_run=dry_run)

    if name == "harnext":
        return run_step(
            ["npm", "install", "-g", "--ignore-scripts", "--legacy-peer-deps", f"{spec['package']}@{ver}"],
            dry_run=dry_run,
        )

    if name == "dsh-chat-import":
        rc = run_step(["dsh", "plugin", "--profile", "web", "add", f"dsh-chat-import@{ver}"], dry_run=dry_run)
        print(f"提示：桌面 profile 请在 DSH 插件管理器中安装 dsh-chat-import@{ver}。")
        return rc

    if name == "ccx":
        dest = Path(spec["cli_dir"]).expanduser()
        tag = f"{spec.get('tag_prefix', 'v')}{ver}"
        repo_url = f"https://github.com/{spec['repo']}.git"
        bin_dir = Path.home() / ".local" / "bin"
        link = bin_dir / "ccx"
        target = dest / "plugins" / "ccx" / "bin" / "ccx"

        if dest.exists():
            if not force:
                print(f"已存在 {dest}；如需重新检出 {tag}，请加 --force。")
            else:
                print(f"+ rm -rf {dest}")
                if not dry_run:
                    shutil.rmtree(dest)

        if not dest.exists() or (force and dry_run):
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
            rc = run_step(["git", "clone", "--depth", "1", "--branch", tag, repo_url, str(dest)], dry_run=dry_run)
            if rc != 0:
                return rc

        print(f"+ ln -sf {target} {link}")
        if not dry_run:
            bin_dir.mkdir(parents=True, exist_ok=True)
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(target)
        print("提示：已以 CLI-only 锁定模式安装 ccx（不装菜单栏与自动更新）；请确保 ~/.local/bin 在 PATH 中。")
        return 0

    print(f"未知工具：{name}", file=sys.stderr)
    return 2


def cmd_install(args: argparse.Namespace) -> int:
    tools = load_tools()
    targets = list(tools.keys()) if args.target == "all" else [args.target]
    for name in targets:
        if name not in tools:
            print(f"未知工具：{name}（可选：{', '.join(tools)} 或 all）", file=sys.stderr)
            return 2
        rc = install_one(name, tools[name], dry_run=args.dry_run, force=args.force)
        if rc != 0:
            return rc
    return 0


def cmd_check_updates(args: argparse.Namespace) -> int:
    tools = load_tools()
    rows: list[dict[str, Any]] = []
    for name, spec in tools.items():
        latest, err = fetch_latest(spec)
        pinned = spec["version"]
        update = bool(latest and is_newer(latest, pinned))
        rows.append(
            {
                "name": name,
                "pinned": pinned,
                "latest": latest,
                "update_available": update,
                "releases_url": spec.get("releases_url", ""),
                "error": err,
            }
        )

    has_updates = any(r["update_available"] for r in rows)

    if args.json:
        print(json.dumps({"has_updates": has_updates, "tools": rows}, ensure_ascii=False, indent=2))
    elif args.markdown:
        print("| 工具 | 当前锁定 | 上游最新 | 状态 | 发布页 |")
        print("|---|---|---|---|---|")
        for r in rows:
            latest = r["latest"] or f"查询失败（{r['error']}）"
            state = "有新版本" if r["update_available"] else ("查询失败" if r["error"] else "已最新")
            link = f"[releases]({r['releases_url']})" if r["releases_url"] else "-"
            print(f"| `{r['name']}` | `{r['pinned']}` | `{latest}` | {state} | {link} |")
    else:
        print(f"{'Tool':<18} {'Pinned':<10} {'Latest':<10} {'Status':<10} Releases")
        print("-" * 80)
        for r in rows:
            latest = r["latest"] or "error"
            state = "UPDATE" if r["update_available"] else ("ERROR" if r["error"] else "ok")
            extra = r["error"] or r["releases_url"]
            print(f"{r['name']:<18} {r['pinned']:<10} {latest:<10} {state:<10} {extra}")

    if args.fail_on_updates and has_updates:
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="agent-session-migration 工具检查、安装与版本巡检")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_doc = sub.add_parser("doctor", help="检查本机已安装工具与锁定版本")
    p_doc.add_argument("--json", action="store_true", help="以 JSON 输出")
    p_doc.set_defaults(func=cmd_doctor)

    p_inst = sub.add_parser("install", help="按 tools.json 锁定版本安装指定工具或全部工具")
    p_inst.add_argument("target", help="工具名（session-migrate / harnext / dsh-chat-import / ccx / all）")
    p_inst.add_argument("--dry-run", action="store_true", help="仅打印安装命令，不实际执行")
    p_inst.add_argument("--force", action="store_true", help="覆盖重装已有版本")
    p_inst.set_defaults(func=cmd_install)

    p_chk = sub.add_parser("check-updates", help="检查上游最新版本，与 tools.json 对比（只读）")
    p_chk.add_argument("--json", action="store_true", help="以 JSON 输出")
    p_chk.add_argument("--markdown", action="store_true", help="以 Markdown 表格输出")
    p_chk.add_argument("--fail-on-updates", action="store_true", help="发现新版本时返回退出码 1")
    p_chk.set_defaults(func=cmd_check_updates)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
