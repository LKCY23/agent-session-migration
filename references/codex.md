# Codex 会话接续

使用迁移生成的会话 ID，在 CLI 或 Desktop 中继续对话。迁移时使用目标客户端对应的 `CODEX_HOME`。

## CLI

```sh
codex resume <会话ID>
```

## Desktop

macOS 打开指定会话：

```sh
open -a Codex "codex://threads/<会话ID>"
```

在 Codex 宿主中，也可调用 `navigate_to_codex_page`：

```json
{"threadId":"目标会话ID"}
```

需要恢复源标题时，调用 `set_thread_title`：

```json
{"threadId":"目标会话ID","title":"源会话标题"}
```

## 验证

核对工作目录、历史消息及工具记录；按用户请求续聊后，确认新回复已保存。

已通过宿主工具验证合成及真实 Claude 会话的桌面打开与历史显示。`open` 命令、续聊及再次恢复尚未实测。
