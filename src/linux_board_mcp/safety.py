"""Safety helpers: allowlists, denied patterns, path sanitization.

Default posture is DENY. Anything not explicitly allowed gets rejected.
"""

from __future__ import annotations

import re
import shlex

# ---- Read-only shell command prefixes (used by `run_shell`).
ALLOW_SHELL_PREFIXES: tuple[str, ...] = (
    # system / kernel info
    "dmesg",
    "uname",
    "uptime",
    "lscpu",
    "nproc",
    "lsmod",
    "modinfo",
    # resource / process snapshot
    "free",
    "df",
    "du",
    "ps",
    "top -bn",         # batch, iteration-limited: `top -bn1`, `top -bn 1`
    "top -b -n",       # batch, iteration-limited: `top -b -n 1`
    "vmstat",
    # systemd (read-only subcommands only — start/stop/restart stay denied)
    "systemctl status",
    "systemctl --failed",
    "systemctl list-",     # list-units / list-unit-files / list-dependencies
    "systemctl is-",       # is-active / is-enabled / is-failed
    "systemctl show",
    "systemctl cat",
    "systemd-analyze",
    "journalctl",
    # storage / filesystem
    "lsblk",
    "findmnt",
    "blkid",
    "stat",
    # buses / devices
    "lsusb",
    "lspci",
    "iio_info",
    "iio_readdev",
    # network
    "ip addr",
    "ip route",
    "ip link",
    "ip neigh",
    "ifconfig",
    "ss",
    "netstat",
    # file reads (scoped) + text tools
    "cat /proc/",
    "cat /sys/",
    "cat /etc/",
    "cat /var/log/",
    "ls /proc/",
    "ls /sys/",
    "ls /dev/",
    "ls -l",
    "ls -la",
    "head",
    "tail",
    "find",
    "grep",
    # android boards
    "getprop",
    "logcat -d",       # dump only
    "cat /vendor/",    # android read-only system partitions
    "cat /system/",
)


# Things that are explicitly forbidden even if they appear to match a prefix.
# (Belt-and-suspenders; allowlist is the real defense.)
DENY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s"),
    re.compile(r"\bdd\s"),
    re.compile(r"\bmkfs"),
    re.compile(r"\breboot\b"),
    re.compile(r"\bpoweroff\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\bhalt\b"),
    re.compile(r"\brmmod\b"),
    re.compile(r"\binsmod\b"),
    re.compile(r"\bmodprobe\b"),
    re.compile(r"\bfastboot\b"),
    re.compile(r"\bfuse\b"),
    re.compile(r"[`$]\("),     # command substitution
    re.compile(r"\beval\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bsu\s"),
    re.compile(r">\s*/"),       # any redirect to a path
    re.compile(r">>\s*/"),
    # Destructive flags on otherwise read-only commands (find / journalctl / ss).
    re.compile(r"-exec\b"),     # find -exec / -execdir: runs arbitrary commands
    re.compile(r"-delete\b"),   # find -delete: removes matched files
    re.compile(r"--vacuum"),    # journalctl --vacuum-*: deletes journal files
    re.compile(r"--rotate\b"),  # journalctl --rotate
    re.compile(r"--kill\b"),    # ss --kill: terminates sockets
)


# sysfs / proc read whitelisted roots.
SYSFS_READ_ROOTS: tuple[str, ...] = (
    "/sys/class/",
    "/sys/bus/",
    "/sys/devices/",
    "/sys/module/",
    "/sys/kernel/debug/",       # debugfs — useful for IIO / drm tracing
    "/sys/firmware/devicetree/",
    "/proc/device-tree/",       # alias to above on most boards
)
PROC_READ_ROOTS: tuple[str, ...] = ("/proc/",)


# sysfs write whitelisted prefixes. Far more restrictive than read.
SYSFS_WRITE_ROOTS: tuple[str, ...] = (
    "/sys/class/gpio/",
    "/sys/class/leds/",
    "/sys/class/pwm/",
    "/sys/bus/iio/devices/",
    "/sys/kernel/debug/tracing/",
)


def check_shell_command(
    cmd: str,
    extra_allowed_prefixes: tuple[str, ...] = (),
) -> tuple[bool, str]:
    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return False, "empty command"

    # Reject if any deny pattern hits anywhere in the command (catches
    # shell injection attempts like `dmesg; rm -rf /`).
    for pat in DENY_PATTERNS:
        if pat.search(cmd_stripped):
            return False, f"matches deny pattern {pat.pattern!r}"

    # Reject shell metacharacters that would alter command flow or write
    # files. `>` / `<` are included so a relative-path redirect like
    # `dmesg > junk` can't slip past the absolute-path deny patterns.
    for bad in (";", "|", "&", "&&", "||", ">", "<", "\n", "\r"):
        if bad in cmd_stripped:
            return False, f"contains shell metacharacter {bad!r}"

    allowed = ALLOW_SHELL_PREFIXES + tuple(extra_allowed_prefixes)
    if not any(cmd_stripped.startswith(p) for p in allowed):
        head = cmd_stripped.split()[0]
        return False, f"no allow-list prefix matches {head!r} (see safety.ALLOW_SHELL_PREFIXES)"

    return True, ""


def check_path(path: str, allowed_roots: tuple[str, ...]) -> tuple[bool, str]:
    if not path.startswith("/"):
        return False, "path must be absolute"
    if ".." in path.split("/"):
        return False, "path must not contain '..'"
    if "\0" in path or "\n" in path:
        return False, "path contains control characters"
    if not any(path.startswith(r) for r in allowed_roots):
        return False, f"path must start with one of {allowed_roots}"
    return True, ""


def quote(arg: str) -> str:
    """Shell-quote a single argument for splicing into a remote shell command."""
    return shlex.quote(arg)


# Block writes to these even if the prefix is otherwise allowed.
HIGH_RISK_SYSFS_FRAGMENTS: tuple[str, ...] = (
    "/efi/",
    "/efivars/",
    "/firmware/efi",
    "/fuse",
    "/otp",
    "/secure_boot",
    "/cpufreq/scaling_max_freq",   # thermal abuse
    "/thermal_throttle",
    "watchdog/disable",
)


def check_sysfs_write_target(path: str) -> tuple[bool, str]:
    ok, reason = check_path(path, SYSFS_WRITE_ROOTS)
    if not ok:
        return False, reason
    low = path.lower()
    for frag in HIGH_RISK_SYSFS_FRAGMENTS:
        if frag in low:
            return False, f"path contains high-risk fragment {frag!r}"
    return True, ""
