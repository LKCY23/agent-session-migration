# Antigravity 会话接续

使用迁移生成的会话标题和项目目录，在 Antigravity Desktop 中继续对话。

## Desktop

Antigravity Desktop 无按会话 ID 直达的 deep link，打开应用后按项目定位：

```sh
open -a Antigravity
```

在左侧栏对应项目下找到带 `⇄ ` 前缀的目标会话标题（可对照迁移返回的 `target.id` 和 `message`），打开后直接续聊。

## CLI

当前未支持独立 Antigravity CLI（`agy`）的会话迁移。

## 验证

核对项目目录、导入的首条上下文消息及确认回复；按用户请求续聊后，确认新回复已保存。

已通过隔离环境验证 `Antigravity Desktop ↔ Claude Code` 的转换、中转兼容及入库（Antigravity Desktop 2.34.0、`ccx 0.1.7`）；桌面 UI 人工续聊按需现场确认。
