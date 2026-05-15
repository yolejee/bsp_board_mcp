# linux_board_mcp

让 Claude（或任何 MCP 客户端）直接连你的嵌入式 Linux 板子，自己跑命令、自己看输出、自己 debug。不用再手动 ssh / adb shell + 复制粘贴。

支持三种连接方式，**同一份 server，env 切换**：

| transport | 适用场景 | 后端 |
|-----------|---------|------|
| `ssh` | 板子有 sshd（典型 i.MX / TI 嵌入式 Linux） | `asyncssh` |
| `adb-usb` | 板子用 USB adb gadget（Rockchip / Allwinner / Android 设备） | `adb` CLI |
| `adb-wifi` | 板子开了 adb-over-tcp | `adb` CLI |

> 已实测：**鲁班猫 LubanCat (RK 系列, Linux 4.19, aarch64) over adb-usb**。读 dmesg / sysfs / proc / IIO 全通。

工程用 [uv](https://docs.astral.sh/uv/) 管理，**清华源默认走 PyPI 镜像**——国内安装从几小时降到几秒。

技术细节 / 架构原理见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 快速开始（Windows，5 步）

### 1. 一键安装

双击 [`setup.bat`](setup.bat)，或者 PowerShell：

```powershell
cd linux_board_mcp
.\setup.bat                          # 推荐
# 或： .\setup.ps1                   # 需要先放行执行策略，见下文
```

它会：检查/安装 `uv` → `uv sync` 建 `.venv` → 从模板生成 [`mcp.json`](mcp.json) → import 自检。

第一次跑约 **10-30 秒**。

> 如果 `.\setup.ps1` 报 "禁止运行脚本"：用 `.\setup.bat`，或 `powershell -ExecutionPolicy Bypass -File .\setup.ps1`，或一次性放行：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. 选 transport，改 `mcp.json`

打开 [`mcp.json`](mcp.json)，里面三套预置 server。**只改你要用的那套的 `env`**：

**SSH**：

```json
"BOARD_HOST": "192.168.x.x",
"BOARD_USER": "root",
"BOARD_KEY":  "C:\\Users\\你\\.ssh\\board_rsa"
```

**ADB USB**：先 `adb devices -l` 找 serial，填进去：

```json
"ADB_SERIAL": "5c5ec7023ef0356e"
```

**ADB WiFi**：板子上先开 `adb tcpip 5555`，然后：

```json
"ADB_WIFI_HOST": "192.168.x.x",
"ADB_WIFI_PORT": "5555"
```

> JSON 里 Windows 路径用 `\\`。

### 3. 烟雾测试（不挂 Claude）

```powershell
cd e:\linux_board_mcp
uv run python -m linux_board_mcp
```

stderr 看到这行就对：

```
[linux_board_mcp] ready: name=linux-board-adb-usb target=adb-usb://5c5ec7023ef0356e
```

Ctrl+C 退出。要更彻底地手动调工具，用 MCP Inspector：

```powershell
npx @modelcontextprotocol/inspector uv run python -m linux_board_mcp
```

### 4. 挂到 Claude Code

**项目级（推荐）**——拷成你嵌入式项目根目录的 `.mcp.json`：

```powershell
cd <你的嵌入式项目>
Copy-Item e:\linux_board_mcp\mcp.json .mcp.json
```

**临时挂**：

```powershell
claude --mcp-config "e:\linux_board_mcp\mcp.json"
```

### 5. 用起来

挂上后，在 Claude Code 里直接说话：

```
你：看一下板子最近 20 行 dmesg
（Claude 调 read_dmesg）

你：lsmod 看看
（Claude 调 lsmod）

你：把我刚编的 dht11.ko 推上去 insmod
（Claude 调 install_module → 你 approve → 调 read_dmesg 验证）
```

---

## 工具清单

### 只读（默认无需确认）

| tool | 干什么 |
|------|--------|
| `board_info` | uname + uptime + transport 描述（先调这个验证连通） |
| `read_dmesg(lines, grep)` | dmesg tail，可 grep |
| `read_sysfs(path)` | 读 `/sys/`（白名单内） |
| `read_proc(path)` | 读 `/proc/` |
| `list_dir(path, long)` | `ls` |
| `lsmod()` / `modinfo(module)` | 内核模块 |
| `read_gpio(n)` | 读 legacy sysfs GPIO |
| `read_iio(device, channel)` | 读 IIO 通道（支持按 name 查找） |
| `dump_devicetree(subpath)` | 列 `/proc/device-tree` 节点 |
| `run_shell(cmd)` | allow-list 内的 shell 命令 |

### 破坏性（MCP 客户端会要求每次 approve）

| tool | 干什么 |
|------|--------|
| `install_module(ko_path, params)` | 推 .ko 到板子并 insmod |
| `remove_module(name)` | rmmod |
| `write_sysfs(path, value)` | 写 sysfs（写白名单内） |
| `set_gpio(n, value)` / `export_gpio(n, direction)` | 操作 GPIO |
| `reboot_board(force)` | 重启 |

详细的工具签名、安全约束、扩展方式 → [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 关键环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `BOARD_TRANSPORT` | `ssh` | `ssh` / `adb-usb` / `adb-wifi` |
| `BOARD_NAME` | `linux-board` | MCP 客户端里显示的名字 |
| `BOARD_HOST` / `BOARD_PORT` / `BOARD_USER` / `BOARD_KEY` / `BOARD_PASSWORD` | — | SSH 参数 |
| `ADB_BINARY` | `adb` | adb 路径（不在 PATH 就写绝对路径） |
| `ADB_SERIAL` | — | adb-usb 多设备时锁定目标 |
| `ADB_WIFI_HOST` / `ADB_WIFI_PORT` | — / `5555` | adb-wifi 必填 |
| `BOARD_TIMEOUT` | `15` | 单命令超时（秒） |
| `BOARD_AUDIT_LOG` | `~/.linux_board_mcp/audit.log` | 审计日志 |
| `BOARD_EXTRA_SHELL_PREFIXES` | — | `run_shell` 额外允许的前缀，逗号分隔 |

完整模板见 `examples/*.env.example`。

---

## 常见故障

| 现象 | 原因 / 解法 |
|------|------|
| `.\setup.ps1` 禁止运行 | 用 `.\setup.bat`，或 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `uv sync` 卡死 / 几十分钟没动 | 镜像问题，换一个：`.\setup.ps1 -Mirror aliyun`（可选 `tsinghua` / `aliyun` / `ustc` / `tencent` / `pypi`） |
| `adb` 找不到 | 装 [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools)，或把 `ADB_BINARY` 改成绝对路径如 `D:\\platform-tools\\adb.exe` |
| `adb devices` 一直 offline / unauthorized | 板子上没接受 USB 调试授权 / 没切 USB 模式到 adb |
| Claude 调工具卡住 | 看 audit.log；ssh 模式常见是 `known_hosts` 或 key passphrase 卡住——用免密码 key |
| `read_dmesg` 返回 `Operation not permitted` | adb shell 不是 root，要么 `adb root`，要么换 ssh 用 root 登录 |
| 工程目录搬家 | 重跑 `setup.bat`，mcp.json 里的绝对路径会刷新 |

---

## 日常命令速查

| 干啥 | 命令 |
|------|------|
| 一键安装 / 重置 | `.\setup.bat` |
| 换镜像重装 | `.\setup.ps1 -Mirror aliyun` |
| 加 / 升 / 删依赖 | `uv add <pkg>` / `uv lock --upgrade` / `uv remove <pkg>` |
| 跑 server（本地调试） | `uv run python -m linux_board_mcp` |
| 进 venv shell | `.venv\Scripts\activate.ps1` |
| 看审计日志 | `Get-Content audit.log -Wait` |

---

## 项目布局

```
linux_board_mcp/
├── setup.ps1 / setup.bat          # 一键安装入口
├── mcp.template.json              # mcp.json 模板（commit）
├── mcp.json                       # 一键安装后生成（gitignore，含本机绝对路径）
├── pyproject.toml                 # uv 读它，含清华镜像配置
├── uv.lock                        # uv sync 生成（可 commit）
├── README.md
├── ARCHITECTURE.md                # 技术框架 + 实现原理
├── examples/                      # 三种 transport 的 .env 模板
└── src/linux_board_mcp/
    ├── __main__.py / server.py / config.py / safety.py / audit.py
    ├── transports/                # base / ssh / adb（USB + WiFi）
    └── tools/                     # readonly / writable
```

---

## 我想……

| 想做的事 | 看哪 |
|---------|------|
| 改某个工具的行为 | [src/linux_board_mcp/tools/](src/linux_board_mcp/tools/) + [ARCHITECTURE.md §6](ARCHITECTURE.md#6-工具实现模式) |
| 加一个新工具 | [ARCHITECTURE.md §6 + §9](ARCHITECTURE.md#9-怎么扩展) |
| 加一个新 transport（比如 telnet / serial） | [ARCHITECTURE.md §4](ARCHITECTURE.md#4-transport-抽象) |
| 放宽 `run_shell` 的白名单 | 改 [`safety.py`](src/linux_board_mcp/safety.py) 或设 `BOARD_EXTRA_SHELL_PREFIXES` |
| 接 CI / 跑自动回归 | 参考 [docs/mcp-hardware-regression-testing.md](../docs/mcp-hardware-regression-testing.md) 的 pytest-mcp 模式 |
| 出故障想看审计 | `Get-Content audit.log -Wait` |

---

## 限制

- **`run_shell` 白名单是死的**：用 `BOARD_EXTRA_SHELL_PREFIXES` 临时加，长期就改 `safety.py`
- **ADB exit code**：老版本 adb (<23) 不透传远端 exit code，rc 看起来都是 0。判断成功 / 失败请看 stdout / stderr 内容
- **没有 `capture_serial`**：抓 USB-UART 跟 transport 正交，未实现
- **没有 `flash_image`**：dd 块设备风险太大，故意不提供
- **mcp.json 含绝对路径**：搬目录后必须重跑 `setup.bat`

---

## License

MIT
