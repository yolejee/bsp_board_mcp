# 内存泄漏检测完整手册

## 1. kmemleak 深入使用指南

### 1.1 工作原理
```
kmemleak 通过以下方式检测泄漏:
1. 记录所有 kmalloc/vmalloc/kmem_cache_alloc 分配
2. 周期性扫描内核数据段、栈、已分配对象中的指针
3. 如果某个分配的对象没有被任何指针引用 → 报告为泄漏

注意:
- 误报可能发生 (指针被编码或存在非标准引用方式)
- 仅检测内核态分配, 不检测用户态 malloc
```

### 1.2 高级配置
```bash
# 内核参数控制扫描行为:
# kmemleak=on/off                  # 启用/禁用 (默认 on, 如果编译了)

# 运行时控制:
echo scan=10 > /sys/kernel/debug/kmemleak    # 设置扫描间隔 10s
echo stack=off > /sys/kernel/debug/kmemleak  # 不扫描栈 (减少误报)

# 过滤特定分配 (减少噪音):
echo "not_leak 0xffff..." > /sys/kernel/debug/kmemleak   # 标记非泄漏

# 在驱动代码中标记:
kmemleak_not_leak(ptr);      // 告诉 kmemleak 这个不是泄漏
kmemleak_ignore(ptr);        // 完全忽略这个分配
kmemleak_scan_area(ptr, size); // 扫描特定区域
```

### 1.3 实战: 驱动泄漏排查流程
```bash
# Step 1: 激活 kmemleak
echo clear > /sys/kernel/debug/kmemleak

# Step 2: 触发怀疑泄漏的操作 (如: 反复加载/卸载模块)
for i in $(seq 1 10); do
    insmod my_driver.ko
    rmmod my_driver
done

# Step 3: 扫描并读取报告
echo scan > /sys/kernel/debug/kmemleak
cat /sys/kernel/debug/kmemleak

# Step 4: 分析 backtrace, 定位未释放的分配
```

## 2. slub_debug 高级用法

### 2.1 per-cache 精确调试
```bash
# 仅对可疑的 slab cache 开启调试:
# bootargs: slub_debug=FZPU,kmalloc-256

# 多个 cache:
# bootargs: slub_debug=FZ,dentry slub_debug=FZU,inode_cache

# 动态开启 (部分内核支持):
echo 1 > /sys/kernel/slab/kmalloc-256/sanity_checks
echo 1 > /sys/kernel/slab/kmalloc-256/trace
```

### 2.2 调用栈 trace 分析
```bash
# 开启 slub_debug=U 后:
cat /sys/kernel/slab/kmalloc-256/alloc_calls
# 输出格式:
#   <count> <caller> <age>
#   128 my_driver_alloc+0x1c/0x40 [my_driver] age=120/240/360

# 释放调用栈:
cat /sys/kernel/slab/kmalloc-256/free_calls

# 如果 alloc_calls 中某个调用计数远大于 free_calls → 泄漏嫌疑
```

## 3. 用户态泄漏检测

### 3.1 Valgrind 交叉编译 (嵌入式)
```bash
# 下载 valgrind 源码:
wget https://sourceware.org/pub/valgrind/valgrind-3.21.0.tar.bz2

# 交叉编译 (以 aarch64 为例):
./configure --host=aarch64-linux-gnu --prefix=/opt/valgrind-arm64
make -j$(nproc)
make install DESTDIR=/tmp/valgrind-install

# 部署到目标板:
scp -r /tmp/valgrind-install/opt/valgrind-arm64 root@target:/opt/

# 使用:
export VALGRIND_LIB=/opt/valgrind-arm64/lib/valgrind
/opt/valgrind-arm64/bin/valgrind --tool=memcheck --leak-check=full ./my_app
```

### 3.2 mtrace (glibc 内置)
```c
#include <mcheck.h>

int main() {
    mtrace();        // 开始追踪
    // ... 程序逻辑 ...
    muntrace();      // 停止追踪
    return 0;
}
// 编译: gcc -g my_app.c -o my_app
// 运行: MALLOC_TRACE=/tmp/mtrace.log ./my_app
// 分析: mtrace ./my_app /tmp/mtrace.log
```

### 3.3 /proc/PID/smaps 分析
```bash
# 查看进程详细内存映射:
cat /proc/<PID>/smaps | grep -E "^[0-9a-f]|Size:|Rss:|Pss:|Private"

# 汇总:
cat /proc/<PID>/smaps_rollup

# 周期性监控:
while true; do
    echo "=== $(date) ==="
    cat /proc/<PID>/status | grep -E "VmRSS|VmSize|VmSwap"
    sleep 30
done
```
