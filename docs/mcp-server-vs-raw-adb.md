# 「直接让 Claude 用 adb 不就行了」——这句质疑哪里对、哪里错

把 [linux_board_mcp 那篇](embedded-mcp-server-with-claude.md) 和后面的实现发出去之后，我收到一条挺扎心的评论：

> "这玩意没必要吧。Claude Code 自带 Bash 工具，直接让它跑 `adb shell dmesg` 不就完了？专门写个 MCP server，脱裤子放屁。"

说实话，这条我盯着看了两天。因为他不是胡说——**有一半是对的**。

今天就把这个事掰开。我不想写一篇"你们都不懂我的工程多牛"的辩护稿，那没意思。我想认真回答一个问题：**什么时候你确实不需要这东西，什么时候你需要**。如果看完你觉得自己属于不需要的那拨，那也挺好，至少省了你装一遍。

<！-- manual: 备注 / 反馈 -->

---

## 一、先把他对的部分讲清楚

质疑的核心是：Claude Code 本来就能跑 shell 命令，`adb` 又是个现成的命令行工具，俩一拼，Claude 自己就能连板子。要我额外写一个 600 行的 MCP server 中间层，图什么？

这个逻辑在**一种场景下完全成立**：

你就一块板子，插在你这台电脑的 USB 上，你今天就想看一眼 dmesg，看完这事就过去了。

这种时候你跟 Claude 说"帮我跑 `adb shell dmesg | tail -50`"，它跑了，你看了，完事。装我那套 uv 工程、配 mcp.json、改 BOARD_HOST——纯属给自己找事。**一次性的活儿，不需要基础设施**。

我自己也是这样。临时查个东西，我不会去开 MCP server，直接 adb 就上了。

所以如果你看到这觉得"对啊我就是这种情况"——那你真的不用往下看了。这篇不是写给你的。

但大多数做嵌入式的人，工作不是"一次性"的。下面讲的是另外那种人。

---

## 二、他混了两个东西：「能不能做」和「做得稳不稳」

这条质疑真正的毛病，是把**「Claude 有没有能力连板子」**和**「让 Claude 连板子这件事该怎么组织」**当成同一个问题了。

Claude 能不能用 Bash 跑 adb？能。这点没人否认。

但"能"不等于"该这么用"。

打个比方。你的服务能不能直接在代码里拼 SQL 字符串查数据库？能啊，`"SELECT * FROM users WHERE id=" + user_id` 跑得通。那为什么全世界都在用 ORM、用参数化查询？因为"能跑通"和"能安全地、可复用地、团队一起跑"是两码事。

`adb shell` + Bash 工具就是那句拼出来的 SQL。**能用，但你把一把没有保险的枪交给了一个偶尔会手抖的人**。

MCP server 干的事，本质上就是给这件事加结构。下面具体讲加了哪些结构、每一条值多少钱。

---

## 三、最重要的一条：它在你和"板子被搞坏"之间放了一道闸

Claude Code 的 Bash 工具有个特点——**它能跑任何东西**。你授权一次 `adb`，理论上 Claude 就能跑出 `adb shell rm -rf /lib/modules`、`adb shell dd if=/dev/zero of=/dev/mmcblk0`、`adb shell` 往 efuse 里写东西。

你可能说：Claude 不会干这种事。

大部分时候是的。但我做嵌入式十几年，见过 AI 干的蠢事不少。它不是恶意，它是**"创造性地理解了你的意图"**。你说"清理一下旧模块"，它可能 `rm` 到一个你没想到的目录。你说"重置一下那个外设"，它可能去写一个 cpufreq 节点把你的热管理策略干掉。

在纯软件项目里，这种事最多让你 git revert 一下。

在硬件上，**有些操作是物理不可逆的**。烧错一次 efuse，这颗芯片就废了。把 eMMC 分区表 dd 花了，板子变砖。这些不是"重跑一遍"能解决的。

linux_board_mcp 在这里做的事：

- 只读的工具（`read_dmesg`、`read_sysfs` 这些）——Claude 想调就调，不拦
- 改板子状态的工具（`install_module`、`write_sysfs`、`reboot_board`）——**每个都是单独命名的、要你按一次 yes 才执行**
- 真正危险的操作——`rm`、`dd`、`mkfs`、efuse、改 cpufreq 上限、关 watchdog——**哪怕你 yes 了它也拒**，代码里写死了拦

这就是 raw adb 给不了你的。Bash 工具的授权是"要么放开 adb、要么不放开"，没有中间态。它没法区分"读 dmesg"和"dd 整块 eMMC"——对它来说都是 adb 的一次调用。

我那个工程里有个 [`safety.py`](../linux_board_mcp/src/linux_board_mcp/safety.py)，三套白名单加一套黑名单，200 行不到。**这 200 行就是你和"板子变砖"之间那道闸**。

老实说，如果让我在整个工程里只保留一个文件，我留 safety.py，别的都能再写。

---

## 四、出了事，你查得到是谁干的吗

第二条：审计。

你让 Claude 用 Bash 跑 adb。它跑了三十几条命令，散在跟你的对话里。然后你 `/clear` 了，或者对话太长被压缩了。

一周后板子行为变怪了。你想知道"这板子上到底被动过什么"——

对话记录没了。你只能靠记忆。

linux_board_mcp 每一次工具调用都往 [audit.log](../linux_board_mcp/src/linux_board_mcp/audit.py) 追加一行 JSON：什么时间、调了哪个工具、参数是什么、结果摘要、成没成功。

```json
{"ts":"2026-05-15T14:22:01","tool":"write_sysfs","args":{"path":"/sys/class/gpio/...","value":"1"},"ok":true,"rc":0}
```

这件事在嵌入式场景**不是锦上添花，是必需品**。因为板子可以进入一种"看起来正常、其实某个寄存器被改了"的微妙状态。软件 bug 你能复现，这种状态你复现不了——你只能靠日志倒推。

raw adb 没有这个。它的"日志"就是聊天记录，聊天记录会被清、会被压缩、不能结构化查询。

---

## 五、今天 USB，明天 WiFi，后天换 SSH

第三条，也是被低估得最厉害的一条：**传输层**。

你现在的板子插 USB，用 adb。挺好。

过两周这板子要挪到实验室另一头的测试柜里，你够不着 USB 线了——得改用网络上的 adb（adb tcpip）。

再下个项目，客户给的是块 i.MX，根本没有 adbd，只有 sshd。

如果你是"让 Claude 直接用 adb"，那么每换一次环境，你都得重新跟 Claude 交代：这次用 `adb -s 序列号 shell`，这次用 `adb -s IP:5555 shell`，这次改成 `ssh root@IP`。你之前调好的那些话术、那些"记得先 grep 再看"的提醒，**一个都带不走**。

linux_board_mcp 把这层抽象掉了。我那个工程里有个 [Transport 抽象](../linux_board_mcp/ARCHITECTURE.md#4-transport-抽象),SSH 一个实现、ADB 一个实现（USB 和 WiFi 都在里面）。对上层的工具来说，`read_dmesg` 永远是 `read_dmesg`，它不知道也不关心底下是 ssh 还是 adb。

换环境你只改一个环境变量：`BOARD_TRANSPORT`。

你跟 Claude 说话的方式、那 17 个工具、你积累的调试习惯——**全都不变**。

这就是"基础设施"和"一次性脚本"的根本区别：基础设施扛得住环境变化，脚本扛不住。

---

## 六、三块板子在台上，raw adb 必翻车

第四条：多板子。

做嵌入式的，桌上同时摆三块板子是常态——一块跑稳定版、一块跑开发版、一块给同事复现 bug。三块都连着 adb。

你让 Claude 直接用 adb。现在它每跑一条命令都得带 `-s 序列号`。三个序列号长这样：

```
5c5ec7023ef0356e
1d4a09f8b2c6e771
a07e3c1188d490f2
```

你觉得 Claude 在连续操作里、在你来回切话题的时候，**一次都不会把序列号搞混**？

我不信。这种事我在 [MCP server 那篇](embedded-mcp-server-with-claude.md) 的踩坑清单里专门写过——多板子是 AI 最容易出错的地方之一。

linux_board_mcp 的解法：每块板子是一个独立命名的 MCP server,`linux-board-stable`、`linux-board-dev`、`linux-board-repro`。Claude 看到的工具名天然带板子前缀，它不会把"在 dev 板上 reboot"发到 stable 板上。

把"选对板子"这件事从"靠 Claude 每次记对序列号"变成"配置层面就分开了"。少一个出错的机会，在硬件上就少一次心惊肉跳。

---

## 七、一个人能用，不等于一个团队能用

第五条：团队。

"让 Claude 直接用 adb"——假设这话术你自己摸索出来了，用得挺顺。

那你旁边新来的工程师呢？他怎么知道"让 Claude 看 dmesg 之前要提醒它别看全量"？他怎么知道"那块板子的 adb root 权限是通的、这块不通"？他怎么知道哪些操作绝对不能让 Claude 碰？

这些东西全在你脑子里。**你脑子里的东西没法 git clone**。

linux_board_mcp 是一个能 clone 的东西。新人拿到工程，双击 setup.bat，改一下 mcp.json 里的板子地址，完事——这正是我在 [新人入职那篇](embedded-onboarding-with-ai-toolkit.md) 写的那个场景。安全规则、工具集、连接方式，全都固化在代码里跟着工程走。

还有一层：**CI**。

linux_board_mcp 的 Transport 层和 Tools 层是普通的 Python 类，可以 import。意思是——你交互式让 Claude 调试板子用的是这套代码，你半夜跑自动回归测试用的**还是这套代码**。一份实现，两个用途。具体怎么接 CI，我在 [自动化回归测试那篇](mcp-hardware-regression-testing.md) 写过 pytest fixture 的接法。

raw adb 产出不了任何可复用的东西。你今天跟 Claude 摸索出来的那套，明天换个人、换到 CI 里，得从头再来。

---

## 八、顺便说语义这件事

第六条，这条相对小，但也算：工具是带语义的。

`read_iio(device="bmp280", channel="in_temp_raw")`——这一句话里有意图。Claude 一看就知道在干嘛。

换成 raw adb,Claude 得自己拼出 `cat /sys/bus/iio/devices/iio:device几/in_temp_raw`。**那个 `几` 它得先想办法查出来**——iio:device0？device1？不同板子、不同启动顺序还会变。

我那个 `read_iio` 工具内部就带了"按 name 查找 device 目录"的逻辑。Claude 不用管设备号，给个名字就行。

上周我拿鲁班猫（LubanCat,RK 系列，Linux 4.19.232）实测的时候，`lsmod` 一下就看到板子上 `dht11` 模块在跑——一颗温湿度传感器。如果接了 IIO 框架，Claude 用 `read_iio` 直接就能读出温度，不用我教它 sysfs 路径长什么样。

raw adb 也能做，只是 Claude 要多绕几道、多错几次。工具把嵌入式领域知识固化进去了，raw adb 每次都让 Claude 现推。

（同一次实测还顺手发现 dmesg 里有个 `rk-pcie PCIe Link Fail`——板子 PCIe 没接东西，跟这篇没关系，但你看，工具一跑信息就摆在那了。）

---

## 九、最关键的一点：它是"手"，不是孤立的

写到这我得说一个前面几条都没点透、但其实最重要的事。

raw adb 给 Claude 的是一双手——能戳板子，仅此而已。它戳得对不对、该戳哪、戳完那行输出意味着什么——adb 不管。

linux_board_mcp 的 17 个工具不是我拍脑袋列的。我是按"一个嵌入式工程师调板子时实际会做的动作"设计的：看 dmesg、查 sysfs、dump 设备树、读 IIO、看模块。这套工具真正的搭档，是放在 [`linux_board_mcp/.claude/skills/`](../linux_board_mcp/.claude/skills/) 下面那 **22 个嵌入式 Linux 领域技能**——`linux_driver_debug`、`linux_kernel_debug`、`devicetree_rk`、`rk_pmic`、`linux_boot_debug`、`linux_usb`……

这两半是配套的。

skill 是"脑"：它知道 probe 失败要先排 deferred probe、要查 compatible 匹配、要看 pinctrl/clock/regulator 哪个没起来。MCP server 是"手":`read_dmesg` 把报错捞回来、`dump_devicetree` 把节点摊开、`lsmod` 确认模块状态、`read_sysfs` 验证 clock 树。

**脑指挥手，手把现场反馈给脑**。一个 probe 失败的排查，是 skill 的方法论 + MCP 工具的实时数据，来回几轮收敛。

raw adb 在这套配合里是什么？是一根孤零零的管子。它跟你的知识库没有任何关系——你那 22 个 skill 写得再好，Claude 用 raw adb 的时候也不会自然地按 skill 的方法论走，因为中间没有把"领域知识"和"板子操作"咬合起来的东西。

我承认这一条有点抽象，但它是整个工程的设计动机。**我做 MCP server 不是为了让 Claude 能连板子——是为了让 Claude 连板子的方式，能跟它的嵌入式知识对上。** 手和脑得在一个身体里。

（说明一下：这 22 个 skill 是另开的话题，值得单独写一篇。这里只需要知道——MCP server 是为了跟它们配套而存在的，不是个独立小玩具。）

---

## 十、那这工程的缺点呢

讲到这我得说点它不好的地方，不然这篇就成王婆卖瓜了。

**它确实是额外的 600 行代码、20 个文件**。这些代码要有人维护。MCP 协议在变、Python SDK 在升级、adb 行为在不同版本有差异——这些都得跟。raw adb 没有这个负担，adb 是 Google 在替你维护。

**它有学习成本**。新人得知道 mcp.json 怎么配、setup 怎么跑。虽然我做了一键脚本，但"一键"也是一道门槛。

**`run_shell` 的白名单是死的**。Claude 想跑一个我没预料到的只读命令，会被拦——你得去改 `safety.py` 或者加环境变量。这个设计我自己用着也偶尔嫌烦。但我想清楚了：**宁可偶尔嫌烦，不要偶尔烧板**。这个取舍我不打算改。

还有，我得诚实——**这套东西防的是"AI 手抖"，不是"防黑客"**。如果有人能往你的 MCP client 里注入恶意指令，那是另一个层面的问题，我这套白名单不是为那个设计的。别拿它当安全边界的全部。

---

## 十一、所以到底要不要上

不绕弯子，给你一个判断线。

**这几种情况，别上，raw adb 就行：**

- 你就一块板子，长期插在你这台电脑上
- 你基本只读不写，不让 AI 碰任何改板子状态的操作
- 就你一个人用，不涉及团队、不涉及 CI
- 这是个短期项目，做完就结束

满足上面全部，装 linux_board_mcp 是过度工程。我前面说过，我自己临时查东西也直接 adb。

**反过来，只要你中了下面任意两条，我建议你上：**

- 你会让 AI 做改板子状态的操作（insmod、写 sysfs、改 GPIO）
- 你桌上不止一块板子
- 这套调试流程不止你一个人用
- 你想把它接进 CI 做自动回归
- 你的板子会在 USB / 网络 / SSH 之间换连接方式
- 这个项目要做半年以上

中两条，600 行代码的投入就回本了。中四条以上，你不上才是亏。

说到底，这事跟"要不要写测试""要不要上 CI""要不要用 ORM"是同一类问题。每一个基础设施，**单看第一次使用都显得多余**。它的价值不在第一次，在第一百次，在你不在的时候别人也能用，在半年后你自己都忘了细节的时候它还在替你拦事故。

那条质疑说我"脱裤子放屁"。我想了两天的结论是：如果你只放一次屁，确实不用脱裤子。但嵌入式工程师的工作，是天天要放屁的——这种时候，有个固定的地方，比每次现找强。

这话糙。但我找不到更准的比方了。

---

回到我在 [AI Infra 和 AI Docs 那篇](../.claude/skills/ai-radar/digests/topics/ai-infra-and-ai-docs.md) 反复说的那句：AI 时代嵌入式工程师真正的护城河，是把工程系统改造成 AI 友好的能力。

"让 Claude 直接用 adb"是把连板子当成一次性的便利。linux_board_mcp 是把它当成基础设施。

这两种做法的差距，头一次用看不出来。用到第一百次、用到团队里第三个人、用到那块板子差点被烧的那一刻——你就知道了。

下篇打算写：**把 linux_board_mcp 接进夜间 CI，让它自己半夜测板子、早上给我一份报告**——也就是 [回归测试那篇](mcp-hardware-regression-testing.md) 的真实落地版。

按 human-voice skill 自查通过。
