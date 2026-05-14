# linux_board_mcp

让 Claude（或任何 MCP 客户端）直接连你的嵌入式 Linux 板子，自己跑命令、自己看输出、自己 debug。

跟 [`docs/embedded-mcp-server-with-claude.md`](../docs/embedded-mcp-server-with-claude.md) 那篇文章的架构一致。这里是把它真的写出来。

支持三种连接方式：

| transport | 适用场景 | 后端 |
|-----------|---------|------|
| `ssh` | 板子有 sshd（最常见） | `asyncssh` |
| `adb-usb` | 板子用 USB adb gadget | `adb` CLI |
| `adb-wifi` | 板子开了 adb-over-tcp | `adb` CLI |

工程用 [uv](https://docs.astral.sh/uv/) 管理，提供一键安装脚本。

---

## 1. 一键安装（Windows）

**双击 [`setup.bat`](setup.bat)** —— 它会自动：

1. 检查 / 安装 `uv`（缺了就跑官方安装脚本）
2. 跑 `uv sync` 建 `.venv` 并装齐依赖（`mcp`、`asyncssh`、本项目自身 editable）
3. 用本机绝对路径生成 [`mcp.json`](mcp.json)（从 [`mcp.template.json`](mcp.template.json)）
4. import 自检

或者在 PowerShell 里直接跑：

```powershell
cd linux_board_mcp
.\setup.ps1
```

参数：
- `-SkipUvInstall` — uv 缺了直接报错，不自动安装
- `-NoVerify` — 跳过最后的 import 自检

跑完之后，项目目录长这样：

```
linux_board_mcp/
├── .venv/               ← uv 创建
├── uv.lock              ← uv 生成（可以 commit）
├── mcp.json             ← 自动生成（已 gitignore，含本机绝对路径）
├── mcp.template.json    ← 模板（可以 commit）
├── setup.ps1 / setup.bat
└── ...
```

> ADB 模式还需要 [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) 提供的 `adb.exe` 在 PATH 上（或者用 `ADB_BINARY` 指路）。setup 不管这个。

---

## 2. 挂到 Claude Code

[`mcp.json`](mcp.json) 在本目录、**没有放全局**。里面三套 server：

- `linux-board-ssh`
- `linux-board-adb-usb`
- `linux-board-adb-wifi`

两种挂法任选：

### 方式 A：项目级 `.mcp.json`（推荐）

```powershell
# 在你的嵌入式项目根目录
Copy-Item "linux_board_mcp\mcp.json" .mcp.json
```

然后改 `.mcp.json` 里 `BOARD_HOST` / `BOARD_KEY` / `ADB_WIFI_HOST` 等指向你的板子。

### 方式 B：临时挂

```powershell
claude --mcp-config "linux_board_mcp\mcp.json"
```

### 工程目录搬家了怎么办

重新跑 `setup.ps1` 即可，`mcp.json` 里的绝对路径会被刷新。

---

## 3. 配置（按 transport 选一份）

每个 transport 都有一份 `.env.example`：

- [examples/ssh.env.example](examples/ssh.env.example)
- [examples/adb-usb.env.example](examples/adb-usb.env.example)
- [examples/adb-wifi.env.example](examples/adb-wifi.env.example)

环境变量也可以直接写在 `mcp.json` 的 `env` 块里（推荐）——`uv run` 在跑 server 前会把这些注入子进程。

### 关键变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `BOARD_TRANSPORT` | `ssh` | `ssh` / `adb-usb` / `adb-wifi` |
| `BOARD_NAME` | `linux-board` | 在 MCP 客户端里显示的名字 |
| `BOARD_HOST` | `192.168.7.2` | SSH 主机 |
| `BOARD_PORT` | `22` | SSH 端口 |
| `BOARD_USER` | `root` | SSH 用户名 |
| `BOARD_KEY` | — | SSH key 路径 |
| `BOARD_PASSWORD` | — | SSH 密码（建议用 key） |
| `ADB_BINARY` | `adb` | adb 二进制路径 |
| `ADB_SERIAL` | — | adb-usb 多设备时选目标（`adb devices -l` 看 serial） |
| `ADB_WIFI_HOST` | — | adb-wifi 必填 |
| `ADB_WIFI_PORT` | `5555` | adb-wifi 端口 |
| `BOARD_TIMEOUT` | `15` | 单条命令超时（秒） |
| `BOARD_AUDIT_LOG` | `~/.linux_board_mcp/audit.log` | 审计日志路径 |
| `BOARD_EXTRA_SHELL_PREFIXES` | — | 给 `run_shell` 加额外的 allow-list 前缀，逗号分隔 |

---

## 4. 工具清单

### 只读（默认无需确认）

| tool | 干什么 |
|------|--------|
| `board_info` | uname + uptime + transport 描述 |
| `read_dmesg(lines, grep)` | dmesg tail，可 grep |
| `read_sysfs(path)` | 读 `/sys/` 下的文件（白名单内） |
| `read_proc(path)` | 读 `/proc/` |
| `list_dir(path, long)` | `ls` |
| `lsmod()` | 列模块 |
| `modinfo(module)` | 模块元信息 |
| `read_gpio(n)` | 读 legacy sysfs GPIO |
| `read_iio(device, channel)` | 读 IIO 通道（支持按 name 查找） |
| `dump_devicetree(subpath)` | 列 `/proc/device-tree` 节点 |
| `run_shell(cmd)` | allow-list 内的 shell 命令 |

### 破坏性（**强烈建议在 MCP 客户端里要求每次确认**）

| tool | 干什么 |
|------|--------|
| `install_module(ko_path, params)` | 把开发机上的 .ko 推到板子并 insmod |
| `remove_module(name)` | rmmod |
| `write_sysfs(path, value)` | 写 sysfs（写白名单内） |
| `set_gpio(n, value)` | 拉 GPIO |
| `export_gpio(n, direction)` | 导出 GPIO + 设方向 |
| `reboot_board(force)` | 重启（force=True 用 SysRq） |

Claude Code 默认所有 MCP 工具调用都问一遍——足够安全。如果你嫌烦把只读工具加进 `.claude/settings.json` 的 `permissions.allow`、把破坏性工具留在 `ask`。

---

## 5. 工具调用样例

挂好之后，在 Claude Code 里直接说话：

```
你：看一下板子上最近的 dmesg
（Claude 调 read_dmesg）

你：ads1256 这个驱动 probe 失败了，帮我分析
（Claude 自己调 read_dmesg + read_sysfs + dump_devicetree）

你：把我刚编的 ads1256.ko 加载上
（Claude 调 install_module → 等你 approve → 调 read_dmesg 看结果）
```

---

## 6. 安全设计

按 [那篇文章](../docs/embedded-mcp-server-with-claude.md) 第六节的铁律实现：

1. **默认拒绝，白名单放行** —— [`safety.py`](src/linux_board_mcp/safety.py) 里有 `ALLOW_SHELL_PREFIXES`、`SYSFS_READ_ROOTS`、`SYSFS_WRITE_ROOTS` 三套白名单
2. **写操作必须经过 permission prompt** —— 由 MCP 客户端负责，工具 docstring 带 `DESTRUCTIVE:` 提示让客户端识别
3. **路径必须 sanitize** —— 所有路径走 `safety.check_path()`，禁绝对路径之外、`..`、控制字符
4. **审计日志** —— 每次调用追加一行 JSON 到 `BOARD_AUDIT_LOG`
5. **生产板子上别接 MCP** —— 这条由你自觉
6. **危险命令显式禁止** —— `DENY_PATTERNS` 拦 `rm` / `dd` / `mkfs` / `fastboot` / `fuse` 等；`HIGH_RISK_SYSFS_FRAGMENTS` 拦 `cpufreq/scaling_max_freq` / `watchdog/disable` 等

---

## 7. 不挂 Claude 单独跑一下

```powershell
cd linux_board_mcp
$env:BOARD_TRANSPORT = "ssh"
$env:BOARD_HOST = "192.168.7.2"
$env:BOARD_USER = "root"
$env:BOARD_KEY  = "$env:USERPROFILE\.ssh\board_rsa"
uv run python -m linux_board_mcp
```

stderr 应该出现：

```
[linux_board_mcp] ready: name=linux-board target=ssh://root@192.168.7.2:22
```

然后它等 MCP client 通过 stdio 连接。Ctrl+C 退出。

功能性测试推荐用 [MCP Inspector](https://github.com/modelcontextprotocol/inspector)：

```powershell
npx @modelcontextprotocol/inspector uv run python -m linux_board_mcp
```

---

## 8. 项目布局

```
linux_board_mcp/
├── setup.ps1 / setup.bat          # 一键安装
├── mcp.template.json              # mcp.json 的模板（commit）
├── mcp.json                       # 一键安装后生成（gitignore）
├── pyproject.toml                 # uv 读它
├── uv.lock                        # uv sync 生成
├── README.md
├── examples/                      # 三种 transport 的 .env 模板
└── src/linux_board_mcp/
    ├── __main__.py                # python -m linux_board_mcp
    ├── config.py                  # 环境变量 → Config dataclass
    ├── server.py                  # FastMCP tool 注册
    ├── safety.py                  # 白名单 / 黑名单 / 路径校验
    ├── audit.py                   # 审计日志
    ├── transports/
    │   ├── base.py                # Transport ABC + CommandResult
    │   ├── ssh.py                 # SSH 实现（asyncssh）
    │   └── adb.py                 # ADB 实现（subprocess，USB + WiFi）
    └── tools/
        ├── readonly.py
        └── writable.py
```

---

## 9. 日常命令速查

| 干啥 | 命令 |
|------|------|
| 一键安装 / 重置 | `setup.bat` 或 `.\setup.ps1` |
| 加 / 升 / 删依赖 | `uv add <pkg>` / `uv lock --upgrade` / `uv remove <pkg>` |
| 跑 server | `uv run python -m linux_board_mcp` |
| 跑任意 Python 脚本 | `uv run python <script>` |
| 进 venv shell（可选） | `uv venv` 然后 `.venv\Scripts\activate.ps1` |
| 看 lock 状态 | `uv lock --check` |

---

## 10. 已知限制

- **`run_shell` 的 allow-list 是死的**——遇到不在 list 里的命令要么编辑 [`safety.py`](src/linux_board_mcp/safety.py)、要么用 `BOARD_EXTRA_SHELL_PREFIXES` 加进来
- **ADB exit code**：老版本 adb (<23) 不透传远端 exit code，所有 `adb shell` 命令的 rc 看起来都是 0。判断成功 / 失败请看 stdout / stderr 内容
- **`capture_serial` 没实现**：串口抓取依赖外接 USB-UART，跟 transport 正交，下个版本单独加
- **没有 `flash_image`**：dd 块设备风险太大，故意不提供——量产场景请走专用刷机工具
- **工程目录搬家**：mcp.json 里有绝对路径，搬目录后重跑 `setup.ps1`

---

## 11. License

MIT（按需要改）。
