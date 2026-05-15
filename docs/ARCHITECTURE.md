# 技术框架与实现原理

这份文档是给**要改这个工程**的人看的。如果你只是想跑通用一下，看 [README.md](README.md) 就够。

下面按"从外到内"的顺序讲：先讲 MCP 协议本身，再讲我们的层次设计，最后讲每一层的实现细节和你想扩展时该看哪里。

---

## 1. 全局视图

```
┌────────────────────────────────────────────────────────────────┐
│ Claude Code / Cline / Cursor (MCP client)                      │
│   - 读 mcp.json，按需启动我们这个 stdio MCP server 子进程       │
│   - 把 tool list 给 LLM；LLM 决定调谁、传什么参数               │
└──────────────┬─────────────────────────────────────────────────┘
               │  JSON-RPC over stdio
               ▼
┌────────────────────────────────────────────────────────────────┐
│ linux_board_mcp (本工程)                                       │
│                                                                │
│   server.py  ──── 注册 17 个工具，每个一行 docstring 给 LLM   │
│       │                                                        │
│       ▼                                                        │
│   tools/readonly.py        tools/writable.py                  │
│       │                          │                             │
│       └──────────┬───────────────┘                             │
│                  ▼                                             │
│   transports/ (Transport ABC) ── safety.py ── audit.py        │
│       │                                                        │
│       ▼                                                        │
│   SshTransport (asyncssh)  |  AdbTransport (subprocess)       │
└──────────────┬─────────────────────────────────────────────────┘
               │  SSH / ADB
               ▼
┌────────────────────────────────────────────────────────────────┐
│ Target board (your embedded Linux DUT)                         │
│   - sshd  OR  adbd                                             │
│   - /sys, /proc, /dev, kernel modules, user binaries           │
└────────────────────────────────────────────────────────────────┘
```

**核心抽象就两个**：

1. **Transport** —— 把"在板子上跑命令"这件事抽象成 `run(cmd) → (stdout, stderr, rc)` + 文件 push/pull
2. **Tool** —— 一个语义化的板子操作（如 `read_dmesg`），内部组合 transport 调用 + 安全校验 + 审计日志

工具不直接调用 transport——它们通过 `safety.py` 校验参数、通过 `audit.py` 记录调用。

---

## 2. MCP 协议简介（30 秒理解）

[Model Context Protocol](https://modelcontextprotocol.io/) 是 Anthropic 2024 年开源的协议，解决"让 Agent 调外部能力"的问题。

**关键概念**：

| 角色 | 干什么 |
|------|--------|
| MCP client | 内置在 Claude Code / Cline / Cursor 等里，从 mcp.json 读 server 配置，按需拉起子进程 |
| MCP server | 一个进程，暴露 **tools** / **resources** / **prompts** 三类能力 |
| transport（协议层） | JSON-RPC 2.0 over stdio（最常用）/ SSE / HTTP |

我们这个 server 走 **stdio 模式**——MCP client 拉起 `uv run python -m linux_board_mcp` 子进程，client 写 stdin、server 写 stdout，互相发 JSON-RPC 消息。stderr 是日志通道，不参与协议。

**消息流大致是这样**：

```
client → server   {"method": "tools/list"}
server → client   {"result": {"tools": [{"name": "read_dmesg", ...}, ...]}}
client → server   {"method": "tools/call", "params": {"name": "read_dmesg", "arguments": {"lines": 50}}}
server → client   {"result": {"content": [{"type": "text", "text": "..."}]}}
```

我们用的是官方 Python SDK 的 [FastMCP](https://github.com/modelcontextprotocol/python-sdk) 高层 API——只要写带 `@mcp.tool()` 装饰器的 async 函数，schema、JSON-RPC、序列化全自动。

---

## 3. 分层设计

按"读 / 改的代价"从低到高：

| 层 | 文件 | 改动代价 | 何时改 |
|----|------|---------|--------|
| 配置 | [`config.py`](src/linux_board_mcp/config.py) | 极低 | 加新的环境变量 |
| 安全 | [`safety.py`](src/linux_board_mcp/safety.py) | 低 | 调白名单 / 新增危险路径 |
| 审计 | [`audit.py`](src/linux_board_mcp/audit.py) | 低 | 换日志格式 |
| Transport | [`transports/`](src/linux_board_mcp/transports/) | 中 | 加新连接方式（telnet / serial） |
| Tool | [`tools/`](src/linux_board_mcp/tools/) | 中 | 加 / 改具体工具 |
| Server | [`server.py`](src/linux_board_mcp/server.py) | 低 | 注册新工具 |
| Entry | [`__main__.py`](src/linux_board_mcp/__main__.py) | 极低 | 几乎不动 |

**关键原则**：

- Transport **不知道** safety / audit 存在——它只关心连接和命令执行
- Tool **不知道** 具体是 ssh 还是 adb——它只持有一个 `Transport` ABC 引用
- safety 是**纯函数**，没有 I/O——好测试、好复用
- audit 失败**不阻塞**工具调用——避免日志故障搞死整个 server

---

## 4. Transport 抽象

### 4.1 接口（`transports/base.py`）

```python
class Transport(ABC):
    name: str
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def run(self, cmd: str, timeout: float | None) -> CommandResult: ...
    async def push(self, local_path: str, remote_path: str) -> None: ...
    async def pull(self, remote_path: str, local_path: str) -> None: ...
    async def is_alive(self) -> bool: ...
    def describe(self) -> str: ...

@dataclass
class CommandResult:
    stdout: str
    stderr: str
    rc: int
```

`cmd` 是一个 **shell 字符串**（不是 argv 列表）。这是个有意识的取舍：

- **SSH** 远端走 shell（`bash -c "<cmd>"`）
- **ADB** `adb shell <cmd>` 也是远端 sh 解释
- **两边都会做 shell 解析**——所以无论我们传 argv 还是 string，最终都还是被 shell 重新分词

既然如此，与其在 transport 层硬塞 argv 抽象，不如把"安全 quoting"的责任明确丢给调用方：**任何来自用户/LLM 的字符串都必须 `safety.quote()` 过再拼进 cmd**。

### 4.2 SSH 实现（`transports/ssh.py`）

底层用 [asyncssh](https://asyncssh.readthedocs.io/)。**短连接**模式——每个 `run()` 调用打开一个新连接、关掉。原因：

1. asyncssh 连接 ~5ms，跟嵌入式板子命令本身耗时比可忽略
2. 板子重启 / 网络抖动后不用关心"复用"还活不活
3. 简化错误恢复——没有持久状态

代价是密集小命令时会有累积开销。如果你的场景是"50 次 `read_sysfs` 连发"，可以改成池化。

```python
async def _open(self):
    return await asyncio.wait_for(
        asyncssh.connect(**self._connect_kwargs()),
        timeout=self.default_timeout,
    )

async def run(self, cmd, timeout=None):
    async with await self._open() as conn:
        r = await asyncio.wait_for(conn.run(cmd, check=False), timeout=to)
        return CommandResult(stdout=r.stdout, stderr=r.stderr, rc=r.exit_status)
```

`known_hosts=None` 故意关掉了 host key 验证——嵌入式板子的 host key 经常 reflash 后变化，配 `known_hosts` 反而是常态问题。**这是开发用工具，不是生产 SSH 客户端**。

### 4.3 ADB 实现（`transports/adb.py`）

包装系统 `adb` 二进制（`subprocess`）。**不用 Python adb 库**，理由：

1. Google 官方 `adb` 是 reference 实现，所有嵌入式 vendor 都按它测
2. Python adb 库（pure-python-adb、ppadb）在 adb 协议新特性上经常落后
3. TLS pairing / Android 11+ wireless debugging 在 Python 库里支持得不全

**USB 模式**：

```python
argv = ["adb", "-s", self.serial, "shell", cmd]
```

`-s <serial>` 锁定设备。没设 serial 且只有一台设备时，adb 自动选；多设备时报错。

**WiFi 模式**：

```python
# connect() 阶段：
await self._adb(["connect", "192.168.1.2:5555"])
await self._adb(["wait-for-device"])

# run() 阶段：
await self._adb(["-s", "192.168.1.2:5555", "shell", cmd])
```

WiFi 模式下设备 serial 就是 `host:port`——adb 内部就这样表示。

**已知坑**（README 里也提了）：老版本 adb (<23) 不透传远端 exit code，**所有 `adb shell <cmd>` 的 rc 都是 0**。判断成功/失败要看 stdout/stderr 内容。我们的工具 code 没在这一点上强假设——`CommandResult.rc` 当参考用。

### 4.4 加一个新 transport

举例：加个 telnet 用的 `TelnetTransport`：

1. 在 `transports/telnet.py` 写一个继承 `Transport` 的类，实现 `connect / disconnect / run / push / pull / is_alive / describe`
2. 在 `transports/__init__.py` 的 `build_transport()` 工厂里加分支
3. 在 `config.py` 的 `Transport` Literal 类型里加 `"telnet"`
4. 在 `mcp.template.json` 加对应 server 块（可选）

完事。Tool 层和 Server 层一行不用改。

---

## 5. 安全模型

[`safety.py`](src/linux_board_mcp/safety.py) 是核心。三套白名单 + 一套黑名单 + 一组路径校验：

### 5.1 Shell 命令白名单（给 `run_shell`）

```python
ALLOW_SHELL_PREFIXES = ("dmesg", "uname", "cat /proc/", "cat /sys/",
                       "ls /sys/", "lsmod", "modinfo", "iio_info",
                       "ip addr", "getprop", ...)
```

规则：

- **前缀匹配**——比 startswith 严格；不允许整词等价 (`dmesg` 允许，`dmesg2` 不允许）
- **任何 shell metacharacter 一律拒绝**：`;` `|` `&` `&&` `||` 换行符
- **deny 模式叠加**：`rm` `dd` `mkfs` `reboot` `rmmod` `insmod` `modprobe` `fastboot` `fuse` `sudo` `eval` 等无条件拒
- **重定向 `> /` 也拒**——任何往绝对路径的写不许

实际校验逻辑：

```python
def check_shell_command(cmd, extra_allowed_prefixes):
    if any(p.search(cmd) for p in DENY_PATTERNS): return False, "denied"
    if any(bad in cmd for bad in (";","|","&","&&","||","\n","\r")):
        return False, "metacharacter"
    if not any(cmd.strip().startswith(p) for p in ALLOW + extra):
        return False, "no allow-list prefix"
    return True, ""
```

### 5.2 路径白名单（给 `read_sysfs` / `read_proc` / `write_sysfs`）

```python
SYSFS_READ_ROOTS  = ("/sys/class/", "/sys/bus/", "/sys/devices/", "/sys/module/",
                    "/sys/kernel/debug/", "/sys/firmware/devicetree/",
                    "/proc/device-tree/")
PROC_READ_ROOTS   = ("/proc/",)
SYSFS_WRITE_ROOTS = ("/sys/class/gpio/", "/sys/class/leds/", "/sys/class/pwm/",
                    "/sys/bus/iio/devices/", "/sys/kernel/debug/tracing/")
```

写白名单**远比读白名单严格**——读 `/sys/firmware/efi/efivars/` 没事，**写**它一不留神就把 UEFI 烤了。

`check_path()` 额外校验：

- 必须绝对路径
- 不能有 `..`（防止 path traversal）
- 不能有 `\0` `\n` 等控制字符

写操作再加一层 `HIGH_RISK_SYSFS_FRAGMENTS` 子串检查：

```python
HIGH_RISK_SYSFS_FRAGMENTS = ("/efi/", "/efivars/", "/fuse", "/otp",
                             "/cpufreq/scaling_max_freq",
                             "/thermal_throttle", "watchdog/disable")
```

哪怕路径在 write allowlist 里，命中这些片段也拒。**这是双重保险**：万一某天某人把 `/sys/class/thermal/` 加进写白名单忘了想清楚，这层拦着。

### 5.3 Quoting

```python
def quote(arg: str) -> str:
    return shlex.quote(arg)
```

每个工具拼接命令时用：

```python
cmd = f"cat {safety.quote(path)}"
```

`shlex.quote()` 会处理空格、特殊字符、引号——拼接到 shell 里就安全。

### 5.4 三件套 = 三层防御

1. **MCP client approval prompt** —— 写操作让人按 yes 才执行（Claude Code 默认行为）
2. **`safety.py` 白名单 + 黑名单** —— 即使 client 误批，工具也拒
3. **`audit.py` 全调用日志** —— 哪怕真出事了，知道是哪条命令、何时、什么参数

要重申：**这是开发用工具，不是面向不可信攻击者的生产服务**。设计假设是"LLM 有时会瞎搞，我们防它创造性误操作"，不是"防有人拿 RCE 进来"。

---

## 6. 工具实现模式

工具分两个文件：[`tools/readonly.py`](src/linux_board_mcp/tools/readonly.py) / [`tools/writable.py`](src/linux_board_mcp/tools/writable.py)。

### 6.1 类组织

```python
class ReadOnlyTools:
    def __init__(self, transport, audit, extra_prefixes=()):
        self.t = transport
        self.audit = audit
        self.extra_prefixes = extra_prefixes

    async def _run(self, cmd, *, tool, args, timeout=None) -> str:
        try:
            r = await self.t.run(cmd, timeout=timeout)
        except TransportError as e:
            msg = f"BOARD_UNREACHABLE: {e}"
            self.audit.write(tool, args, msg, ok=False)
            return msg
        out = r.format()
        self.audit.write(tool, args, out[:200], rc=r.rc, ok=(r.rc == 0))
        return out
```

每个工具走 `_run()`，统一拿到：

- transport 异常 → 返回带前缀的错误字符串（**不抛**——MCP 工具的约定是错误也是结果）
- 成功 → 格式化后返回
- 任意分支都写一条 audit

### 6.2 命名约定

LLM 看 docstring 决定调谁。**docstring 是 LLM 的 API 文档**，重要：

- 第一行：一句话说明，会作为 tool 的 `description`
- 参数说明用 Google / numpy style 都行，FastMCP 会解析
- 破坏性工具 docstring 一律以 `DESTRUCTIVE:` 开头——客户端用这个识别

```python
@mcp.tool()
async def install_module(ko_path: str, params: str = "") -> str:
    """DESTRUCTIVE: push a local .ko to the board and insmod it.

    ko_path is on the developer machine. It will be transferred to
    /tmp/<basename> on the board before insmod.
    """
    return await rw.install_module(ko_path, params)
```

### 6.3 错误返回的约定

**前缀化错误**——LLM 看到这种前缀会自然调整策略：

| 前缀 | 含义 | LLM 通常会 |
|------|------|----------|
| `BOARD_UNREACHABLE:` | transport 失败 | 改用别的工具或建议用户检查 |
| `REJECTED:` | safety 拦截 | 不重试同一调用，改换路径 |
| `PUSH_FAILED:` | 文件传输失败 | 检查本地文件存在性 |
| `ERROR:` | 工具内部逻辑错误 | 看具体消息 |

**故意不抛 Python 异常**。抛异常 FastMCP 会包成 JSON-RPC error，LLM 拿到的就只是个泛泛的 "tool failed"，没法判断怎么恢复。返回字符串则 LLM 能读到完整上下文。

### 6.4 加新工具的最小步骤

举例：加 `read_interrupts` 工具，读 `/proc/interrupts`：

1. 在 `tools/readonly.py` 加方法：

```python
async def read_interrupts(self) -> str:
    """Read /proc/interrupts (per-CPU IRQ counters)."""
    return await self._run("cat /proc/interrupts",
                           tool="read_interrupts", args={})
```

2. 在 `server.py` 注册：

```python
@mcp.tool()
async def read_interrupts() -> str:
    """Show per-CPU interrupt counters from /proc/interrupts."""
    return await ro.read_interrupts()
```

完事。docstring 写清楚 LLM 自然会用。

### 6.5 加破坏性工具的额外要求

照 [`tools/writable.py`](src/linux_board_mcp/tools/writable.py) 的样子：

- docstring 必须 `DESTRUCTIVE:` 开头
- 参数全部 sanitize，参考既有 `_MOD_NAME_RE` / `check_sysfs_write_target` 模式
- 任何能导致 board 永久损坏的（fuse / OTP / bootloader）**坚决拒**——不要"加个开关"
- audit 写两次：一次进入、一次结果（如果时间长）

---

## 7. 配置层

[`config.py`](src/linux_board_mcp/config.py) 是个 dataclass：

```python
@dataclass
class Config:
    transport: Literal["ssh","adb-usb","adb-wifi"]
    server_name: str
    ssh_host: str
    ssh_user: str
    ssh_key: str | None
    adb_serial: str | None
    adb_wifi_host: str | None
    default_timeout: float
    audit_log_path: Path
    allow_extra_shell_prefixes: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config": ...
```

**全部从环境变量**读，没有 yaml / toml 配置文件。原因：

1. MCP 协议本来就是 client 通过 `env` 块给 server 注入配置
2. 多 server 共存时（mcp.json 里三套），环境变量天然隔离
3. 不引入额外的配置格式 = 不引入新的故障面

要看完整的环境变量清单：[README §关键环境变量](README.md#关键环境变量) 或者直接读源码——50 行不到。

---

## 8. 启动流程（从 setup.bat 到接受第一个工具调用）

```
1. 双击 setup.bat
   └─→ powershell -ExecutionPolicy Bypass -File setup.ps1
       └─→ 1) 检测/安装 uv
           2) uv sync（读 pyproject.toml → 创建 .venv → 装依赖 + 本工程 editable）
           3) 读 mcp.template.json，{{PROJECT_DIR}} 替换成绝对路径，写 mcp.json
           4) uv run python -c "import linux_board_mcp"（自检）

2. Claude Code 启动
   └─→ 读 .mcp.json / --mcp-config 指定的 mcp.json
       └─→ 看到 "command": "uv", "args": ["--directory", "...", "run", "python", "-m", "linux_board_mcp"]
           └─→ spawn 子进程，注入 env 块里的变量

3. linux_board_mcp 进程启动
   └─→ __main__.py:main()
       └─→ Config.from_env() ── 读环境
       └─→ build_server(cfg)
           └─→ build_transport(cfg) ── 选 SSH 或 ADB（这一步不连，只是构造对象）
           └─→ ReadOnlyTools(transport, audit)
           └─→ WritableTools(transport, audit)
           └─→ FastMCP("linux-board-xxx")
           └─→ 17 个 @mcp.tool() 装饰器注册
           └─→ stderr 打印 "[linux_board_mcp] ready: ..."
       └─→ mcp.run() ── 进入 stdio 循环

4. LLM 第一次调工具（比如 board_info）
   └─→ Claude Code 通过 stdin 发 tools/call
       └─→ FastMCP 路由到 board_info() 函数
           └─→ ReadOnlyTools.board_info()
               └─→ Transport.run("uname -a")  ← transport 第一次真连
                   └─→ SshTransport: asyncssh.connect(...)
                   └─→ AdbTransport: subprocess.exec("adb shell uname -a")
               └─→ 返回 stdout
           └─→ audit.write(...)
       └─→ stdout 发 JSON-RPC result
   └─→ Claude Code 把 result 喂回 LLM 上下文
```

**注意 transport 连接是 lazy 的**——server 启动时不连板子。原因是 server 可能跑在板子断开/重启的状态下，启动期失败会让 MCP client 报"server 拉不起来"，反而看不到错误细节。Lazy 连接让 `board_info` 这种诊断工具能成功返回明确的错误信息。

---

## 9. 怎么扩展

### 9.1 加新工具

照 [§6.4](#64-加新工具的最小步骤) 走。两个文件改一改，FastMCP 自动暴露给 LLM。

### 9.2 加新 transport

照 [§4.4](#44-加一个新-transport) 走。Tool 层不用改。

### 9.3 加新板子 / 多板子并存

mcp.json 里直接加新的 server 块——`linux-board-board-A` / `linux-board-board-B`。`BOARD_NAME` 让 LLM 知道哪个工具属于哪台板子。

如果你的 LLM client 工具列表显示工具时把 server 名字加进去，那 LLM 会自然区分 `linux-board-board-A__read_dmesg` vs `linux-board-board-B__read_dmesg`。

### 9.4 把它接到 CI

不要直接挂 Claude Code 在 CI 里。CI 直接调底层 `Transport` 和 `Tools` 类即可：

```python
from linux_board_mcp.config import Config
from linux_board_mcp.transports import build_transport
from linux_board_mcp.tools.readonly import ReadOnlyTools
from linux_board_mcp.audit import AuditLog

cfg = Config.from_env()
t = build_transport(cfg)
await t.connect()
ro = ReadOnlyTools(t, AuditLog(cfg.audit_log_path))
dmesg = await ro.read_dmesg(lines=200)
```

参考 [docs/mcp-hardware-regression-testing.md](../docs/mcp-hardware-regression-testing.md) 里的 `pytest-mcp` fixture 写法——本质就是这样。

### 9.5 给工具加 metrics / tracing

最干净的方式：在 `audit.py` 里加一个 sink 接口，AuditLog 现在写文件——可以同时写 OpenTelemetry / StatsD / Prometheus。

---

## 10. 设计取舍

下面列了几个"为什么这么做、不那么做"的判断：

| 取舍 | 选 A | 没选 B | 原因 |
|------|------|-------|------|
| Tool 错误 | 返回字符串前缀 | 抛 Python 异常 | LLM 看字符串能改策略，看 JSON-RPC error 改不了 |
| Transport 连接 | 短连接每次重建 | 持久连接池 | 嵌入式板子重启频繁，复杂复用得不偿失 |
| ADB 后端 | 系统 `adb` 二进制 | pure-python-adb | Google 官方是 reference impl，新协议特性优先支持 |
| 命令传递 | shell 字符串 | argv 数组 | 远端反正走 shell 解析，傻装无意义 |
| 配置 | 环境变量 | yaml 文件 | MCP 协议天然走 env，多 server 隔离也容易 |
| 启动连接 | lazy | eager | 板子可能没开机，eager 报错会让 client 直接放弃 |
| Safety 模型 | 白名单为主 | 黑名单为主 | LLM 偶尔会构造你想不到的等价命令，白名单挡得住 |
| Audit 失败 | swallow | propagate | 日志故障不该挂掉真活儿 |

---

## 11. 还没做 / 故意没做

- **`capture_serial`** —— 抓 USB-UART，跟 transport 正交，得另一套通道
- **`flash_image`** —— dd 块设备风险太大，量产请走 vendor 工具
- **OpenTelemetry tracing** —— 现阶段 audit JSON 够用，需要再加
- **persistent SSH connection pool** —— 单板子场景下不值
- **MCP resources / prompts** —— 这俩 MCP 概念我们暂时用不上，只用了 tools
- **TLS-pairing 的 Android 11+ wireless debugging** —— 用户得先 `adb pair` 一次，工具不替代

---

## 12. 引用

- MCP 规范：<https://modelcontextprotocol.io/>
- Python MCP SDK：<https://github.com/modelcontextprotocol/python-sdk>
- asyncssh：<https://asyncssh.readthedocs.io/>
- 文章原型（中文）：[docs/embedded-mcp-server-with-claude.md](../docs/embedded-mcp-server-with-claude.md)
- 配套自动化测试模式：[docs/mcp-hardware-regression-testing.md](../docs/mcp-hardware-regression-testing.md)
