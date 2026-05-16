# CLAUDE.md

本文件指导 Claude Code 在这个工作区的工作方式。

## 这个工作区是什么

`linux_board_mcp` —— 一个 MCP server,让 Claude 直接操作嵌入式 Linux 板子(经 SSH / ADB)。
源码结构、架构原理见 [README.md](README.md) 与 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

同时这个工作区被配置成**板子调试环境**:

- 经项目级 `.mcp.json` 注册了 `linux-board-mcp` 这个 MCP server(安装步骤见 README)。
- `.claude/skills/` 下有一批嵌入式 Linux / Rockchip 调试 skill。

**当 `linux-board-mcp` 的工具可用时,调试板子按下面的「工作方式」来。**

## 调试板子的工作方式 ★

Claude 是大脑和编排者:**选 skill 的是 Claude,调 MCP 工具的也是 Claude**。MCP server 和 skill 彼此不通信,全靠 Claude 串起来。遇到任何板子相关问题,按这个流程:

### 1. 先确认连通

开工先调 `board_info`,确认 transport / uname / uptime。连不上,先解决连接,别往下走。

### 2. 主动用 MCP 工具采集现象 —— 不要让用户手敲命令贴日志

板子就在 MCP 工具的另一头,Claude 应当**自己去采数据**,而不是要用户复制粘贴:

| 工具 | 用途 |
|------|------|
| `read_dmesg(lines, grep)` | 内核日志 |
| `read_proc(path)` / `read_sysfs(path)` | 运行状态 |
| `list_dir` / `lsmod` / `modinfo` / `dump_devicetree` | 文件、模块、设备树 |
| `read_gpio` / `read_iio` | GPIO / IIO 传感器 |
| `run_shell(cmd)` | 白名单内的 shell 命令 |
| `pull_file` / `adb_devices` | 拉文件回开发机 / adb 连接诊断 |

只有当某信息 MCP 工具确实拿不到(白名单外、需要物理操作)时,才请用户协助。

### 3. 让对应领域的 skill 接管

根据现象领域,对应 skill 会按 description 自动触发;**主动跟随它的方法论**,在其指导下继续调 MCP 工具深挖。现象 → skill 对照:

| 现象 | skill |
|------|-------|
| 开机卡住 / 启动慢 / 启动日志分析 | `linux_boot_debug` |
| dmesg 报错 / panic / call trace / 内核崩溃 | `linux_kernel_debug` |
| 驱动 probe 失败 / 设备不工作 / deferred probe | `linux_driver_debug` |
| 设备树 / dts / compatible / pinctrl | `devicetree_rk`(RK 平台优先)/ `devicetree_common` |
| 没声音 / 录音 / ALSA / codec | `linux_audio` |
| 显示 / 屏幕 / VOP / HDMI / MIPI DSI | `rk_display` |
| 摄像头 / sensor / MIPI CSI | `rk_camera`;ISP 画质调优 `rk_isp` |
| 网络不通 / 网速 / WiFi / 以太网 | `linux_network` |
| USB 不识别 / OTG / Type-C | `linux_usb` |
| 卡顿 / 性能 / 发热降频 | `perf_rk`(RK 优先)/ `perf_common` |
| OOM / 内存泄漏 / 内存越界 | `linux_memory_debug` |
| 休眠唤醒 / 待机功耗 | `linux_low_power` |
| PMIC / regulator / DVFS 调频调压 | `rk_pmic` |
| DDR 频率 / 带宽 / 拷机 | `rk_ddr` |
| U-Boot / 引导 / 烧写 | `rk_uboot` |
| NPU / RKNN / 模型部署 | `rk_npu` |
| 视频编解码 / MPP / RGA / GStreamer | `rk_mpp` |
| 看芯片手册 / datasheet / 寄存器定义 | `datasheet_reader` |

已实测板子:**EmbedFire LubanCat-1(RK3566,4×Cortex-A55,内核 4.19,Ubuntu 20.04)**。

### 4. 闭环

MCP 工具的**输出**会暴露现象 —— 据此触发或切换 skill;skill 又指导下一步该调哪个工具。这个「采数据 → 选 skill → 再采」的循环,中间那一环始终是 Claude。

## 破坏性操作

下面这些工具会改动板子状态,MCP 客户端**每次都会弹窗要用户批准**,不要假设已获批:

`install_module` / `remove_module` / `write_sysfs` / `set_gpio` / `export_gpio` / `reboot_board`

执行前先向用户说清楚:要做什么、风险是什么。

## 注意事项

- **ADB exit code 不可靠**:老版本 adb 不透传远端 exit code,返回码常年是 0。判断成败要看 `stdout` / `stderr` 内容,别只看 `rc`。
- **`run_shell` 白名单是死的**:超出白名单的命令会被拒。临时放宽用环境变量 `BOARD_EXTRA_SHELL_PREFIXES`,长期就改 `src/linux_board_mcp/safety.py`。
- **板子要在线**:调工具前确认板子已连接(USB adb 时 `adb devices` 能看到 serial)。

## 改 MCP server 本身

如果是改这个 server 的代码(加工具 / 加 transport / 调白名单),而不是调试板子:工具实现在 `src/linux_board_mcp/tools/`,传输层在 `src/linux_board_mcp/transports/`,扩展方式见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。
