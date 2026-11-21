# ccx

用于 Antigravity Desktop ↔ Claude Code / Codex，也可经 Claude Code JSONL 中转衔接 Pi、DSH。以下基于 `ccx 0.1.7`（macOS 13+）。

## 命令

| 命令 | 用途 |
|---|---|
| `ccx --help` | 查看子命令和参数。 |
| `ccx ls [-q <关键词>]` | 列出各应用会话及关联状态。 |
| `ccx to-claude <会话ID> --from antigravity --no-open --json` | Antigravity Desktop → Claude Code。 |
| `ccx to-codex <会话ID> --from antigravity --no-open --json` | Antigravity Desktop → Codex。 |
| `ccx -C <工作目录> to-antigravity <会话ID> --from <claude\|codex> --no-open --json` | Claude Code / Codex → Antigravity Desktop。 |
| `ccx unlink <会话ID>` | 取消双向关联记录，保留两侧会话。 |

数据根由 `ANTIGRAVITY_HOME`（默认 `~/.gemini/antigravity`）、`CLAUDE_CONFIG_DIR`、`CODEX_HOME`、`CCX_HOME`（默认 `~/.ccx`）决定。一次性迁移不希望留下持续同步关联时，使用临时 `CCX_HOME`，或在迁移后执行 `ccx unlink`。

与 Pi / DSH 互转时，用临时 `CLAUDE_CONFIG_DIR` 和临时 `CCX_HOME` 生成或读取中转 Claude JSONL（`<CLAUDE_CONFIG_DIR>/projects/<slug>/<target.id>.jsonl`），再交给 [harnext](harnext.md) 或 [dsh-chat-import](dsh-chat-import.md)。

## 结果

JSON 输出中 `target.id` 为目标会话 ID，`cwd` 为项目目录，`message` 包含目标提示。

- Claude Code：按[会话接续](claude-code.md)在 CLI 或 Desktop 中打开。
- Codex：按[会话接续](codex.md)在 CLI 或 Desktop 中打开。
- Antigravity：按[会话接续](antigravity.md)在 Desktop 中打开。

## 限制

- 仅支持 macOS 桌面版 Antigravity（依赖本机 `LanguageServerService` 和自带 `bin/agentapi`），不支持独立 Antigravity CLI（`agy`）；读取内容时若 Desktop 未运行会在后台启动它。
- 迁入 Antigravity 时无法写入多轮原生历史：工具会新建会话并将整理后的历史（长会话截留最近约 6 万字符与全部用户提问）作为首条消息发入，等待一轮简短确认回复。
- 从 Antigravity 迁出时，工具调用与输出会被展平为文本记录（`[ran]`、`[edited]`、`[read]`、`[tool ...]`），不保留原生结构化工具块。
- `ccx` 无 `--dry-run` 预览开关；执行迁入 Antigravity 前先核对源会话与目标工作目录。

[上游文档](https://github.com/AaronWong1999/ccx)
