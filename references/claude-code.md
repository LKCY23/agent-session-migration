# Claude Code 会话接续

使用迁移生成的会话 ID，在 CLI 或 Desktop 中继续对话。

## CLI

在目标工作目录中，使用迁移时对应的 `CLAUDE_CONFIG_DIR`：

```sh
claude --resume <会话ID>
```

## Desktop

将会话接入 Claude 应用的 Code 标签页。

| 入口 | 用途 |
|---|---|
| 桌面本地 Code 输入框：`/resume` | 查找、预览并接续会话。 |
| 终端：`claude --desktop --resume <会话ID>` | 用完整 ID 在桌面打开会话。 |

目标桌面已打开时，优先在该实例使用 `/resume`。从终端打开时，使用目标工作目录和迁移时对应的 `CLAUDE_CONFIG_DIR`。

`claude --desktop` 要求 CLI 2.1.285+，适用于 macOS、x64 Windows 和 Claude 订阅登录。接续前确认该会话已退出其他终端或后台运行。

## 结果

- 已转换：目标会话文件已生成。
- 已打开：目标客户端已加载会话，历史和项目目录正确。
- 已续聊：按用户请求继续任务，新回复已保存。

找不到会话时，先核对目标实例的数据目录和会话 ID，再查看导入错误。

[官方说明](https://code.claude.com/docs/en/desktop#coming-from-the-cli)
