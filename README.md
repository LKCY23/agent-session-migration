# 会话迁移工具安装

供环境准备与版本维护时使用；日常迁移入口为 [SKILL.md](SKILL.md)。各工具锁定版本统一记录在 [tools.json](tools.json)。

## 环境检查、按需安装与更新巡检

```sh
python3 scripts/tools.py doctor                 # 检查本机已装版本与锁定版本
python3 scripts/tools.py install <tool|all>     # 按 tools.json 锁定版本安装（可加 --dry-run 预览）
python3 scripts/tools.py check-updates          # 只读查询上游最新版本，不修改本机工具
python3 scripts/smoke_test.py                   # 隔离临时目录冒烟测试（升级前后回归用）
```

仓库已配置每周自动巡检工作流 [.github/workflows/check-tool-updates.yml](.github/workflows/check-tool-updates.yml)，发现上游新版本时自动创建/更新版本升级 PR（不自动合并）；合并前先跑隔离冒烟测试，并同步文档中的版本号与限制说明。

## session-migrate

需要 uv：

```sh
uv tool install 'session-migrate==0.12.0'
session-migrate --version
```

## harnext

需要 Node.js、npm，以及本机 Pi：

```sh
npm install -g --ignore-scripts --legacy-peer-deps @buildingthefuture/harnext@0.8.2
harnext --version
```

写入 Pi 使用已安装的 `@earendil-works/pi-coding-agent`。自动定位失败时，将 `HARNEXT_PI_PACKAGE` 设为该包目录。

## dsh-chat-import

在承载目标会话的 DSH profile 中安装插件。Web profile：

```sh
dsh plugin --profile web add dsh-chat-import@0.26.2
```

桌面 profile 使用应用的插件管理器安装 `dsh-chat-import@0.26.2`。启用完整工具注入档位，确认宿主提供 `import_chat` 和 `export_chat`。当前调用说明对应 DSH 桌面引擎 `0.2.1-rc.2`。

## ccx

需要 macOS 13+、Python 3、以及本机 Antigravity Desktop（已打开登录过）。推荐使用 CLI-only 锁定版本安装（不装菜单栏插件，也不启用后台自动更新）：

```sh
python3 scripts/tools.py install ccx
ccx --version
```

当前调用说明对应 `ccx 0.1.7`。如需完整桌面菜单栏与实时同步插件，可按上游说明运行 `curl -fsSL https://raw.githubusercontent.com/aaronwong1999/ccx/main/install.sh | sh` 并用 `ccx doctor` 检查。
