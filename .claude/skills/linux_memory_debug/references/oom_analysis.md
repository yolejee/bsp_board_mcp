# OOM Killer 完整分析手册

## 1. OOM 评分算法详解

### 1.1 oom_badness() 计算
```
内核 oom_badness() 函数的计算逻辑:

1. 基础分 = 进程 RSS + Swap 使用 + 页表页面
2. 根据 oom_score_adj 调整:
   adj = oom_score_adj  (范围 -1000 到 1000)
   if adj == -1000 → OOM 免杀 (直接跳过)
   点数 = 基础分 * (1000 + adj) / 1000
3. 最终 /proc/PID/oom_score 是归一化到 0-1000 的值

关键推论:
- oom_score_adj = 0: 按实际内存消耗排序
- oom_score_adj = -500: 实际评分减半 (更不易被杀)
- oom_score_adj = 500: 实际评分提高 50% (更易被杀)
- oom_score_adj = -1000: 完全免杀
- oom_score_adj = 1000: 最先被杀
```

### 1.2 OOM 候选选择过程
```
1. 检查是否有进程正在退出 → 等待而非杀新进程
2. 遍历所有进程, 计算 oom_badness()
3. 跳过:
   - oom_score_adj == -1000 的进程
   - init 进程 (PID 1)
   - 内核线程
4. 选择 oom_badness 最大的进程
5. 杀死该进程及其子进程 (同一 thread group)
```

## 2. Cgroup 内存限制与 OOM

### 2.1 Memory Cgroup (v2)
```bash
# 创建内存 cgroup:
mkdir /sys/fs/cgroup/my_group

# 设置内存限制:
echo 256M > /sys/fs/cgroup/my_group/memory.max

# 设置高水位警告:
echo 200M > /sys/fs/cgroup/my_group/memory.high

# 将进程加入 cgroup:
echo <PID> > /sys/fs/cgroup/my_group/cgroup.procs

# 查看状态:
cat /sys/fs/cgroup/my_group/memory.current     # 当前使用
cat /sys/fs/cgroup/my_group/memory.events      # 事件统计 (含 oom_kill 次数)
```

### 2.2 Cgroup OOM 行为
```bash
# Cgroup v2 OOM 控制:
echo 0 > /sys/fs/cgroup/my_group/memory.oom.group
# 0 = 只杀 cgroup 内评分最高的进程 (默认)
# 1 = 杀掉 cgroup 内所有进程

# 注意:
# cgroup 内 OOM 不会杀 cgroup 外的进程
# cgroup 外的全局 OOM 可以杀 cgroup 内进程
```

## 3. OOM 日志完整模板解析

```
# 完整 OOM 日志示例 (注释标注各部分含义):

# ── 触发者信息 ──
video_decode invoked oom-killer: gfp_mask=0x24200ca(GFP_HIGHUSER_MOVABLE),
order=0, oom_score_adj=0
# → 谁触发: video_decode 进程
# → 分配类型: HIGHUSER_MOVABLE (用户态页分配)
# → order=0: 只需要 1 页 (4KB)

# ── 调用栈 (谁触发了分配) ──
Call trace:
 dump_backtrace+0x.../0x...
 show_stack+0x.../0x...
 oom_kill_process+0x.../0x...
 out_of_memory+0x.../0x...
 __alloc_pages_slowpath+0x.../0x...

# ── 内存统计 ──
Mem-Info:
active_anon:12345 inactive_anon:6789 ...
active_file:1023 inactive_file:512 ...
Node 0 Normal free:1024kB min:2048kB low:4096kB high:6144kB
# → free < min → 触发 OOM

# ── 进程列表 (简化) ──
[  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
[  1234 ]     0  1234   123456    98765       524288        0             0 my_app
[  5678 ]  1000  5678    56789    45678       262144        0             0 video_decode

# ── 最终决定 ──
Out of memory: Killed process 1234 (my_app) total-vm:493824kB,
anon-rss:395060kB, file-rss:0kB, shmem-rss:0kB, UID:0, pgtables:512kB,
oom_score_adj:0
# → 被杀进程: my_app, 因为它的 RSS 最大
```

## 4. 嵌入式系统 OOM 防护策略

```bash
# 策略 1: 关键进程保护
echo -1000 > /proc/$(pidof critical_app)/oom_score_adj

# 策略 2: 内存限额 (cgroup)
mkdir /sys/fs/cgroup/noncritical
echo 128M > /sys/fs/cgroup/noncritical/memory.max
echo $(pidof noncritical_app) > /sys/fs/cgroup/noncritical/cgroup.procs

# 策略 3: 提前预警
# 监控 MemAvailable, 低于阈值时主动清理
while true; do
    avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    if [ "$avail" -lt 65536 ]; then  # < 64MB
        echo "WARNING: Low memory $avail kB"
        # 执行清理: drop_caches, 重启非关键进程等
    fi
    sleep 10
done

# 策略 4: panic_on_oom + watchdog 重启
sysctl -w vm.panic_on_oom=1    # OOM 时直接 panic
# 配合硬件 watchdog → panic → watchdog reset → 系统重启
```
