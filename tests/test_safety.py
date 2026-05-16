"""Tests for the safety allowlist / denylist logic.

These are pure-function tests — no board, no network — so they run anywhere.
`safety` is security-critical: a regression here can open a shell-injection
hole, so keep coverage tight.
"""

from linux_board_mcp import safety
from linux_board_mcp.safety import (
    check_path,
    check_shell_command,
    check_sysfs_write_target,
)

# ----- check_shell_command: allowed -----

class TestShellAllowed:
    def test_plain_allowlisted_commands(self):
        for cmd in [
            "dmesg",
            "uname -a",
            "uptime",
            "free -h",
            "df -h",
            "ps aux",
            "lsmod",
            "lscpu",
            "top -bn1",
            "vmstat 1 1",
        ]:
            ok, reason = check_shell_command(cmd)
            assert ok, f"{cmd!r} should be allowed, got: {reason}"

    def test_systemd_readonly_subcommands(self):
        for cmd in [
            "systemctl --failed",
            "systemctl status sshd",
            "systemctl list-units",
            "journalctl -b -p err",
            "systemd-analyze blame",
        ]:
            ok, reason = check_shell_command(cmd)
            assert ok, f"{cmd!r} should be allowed, got: {reason}"

    def test_scoped_cat(self):
        for cmd in [
            "cat /proc/cpuinfo",
            "cat /sys/class/thermal/thermal_zone0/temp",
            "cat /etc/os-release",
        ]:
            ok, reason = check_shell_command(cmd)
            assert ok, f"{cmd!r} should be allowed, got: {reason}"

    def test_search_tools(self):
        for cmd in ["find /sys -name rtc", "grep -r foo /proc"]:
            ok, reason = check_shell_command(cmd)
            assert ok, f"{cmd!r} should be allowed, got: {reason}"

    def test_extra_prefixes(self):
        ok, _ = check_shell_command(
            "custom-tool --flag", extra_allowed_prefixes=("custom-tool",)
        )
        assert ok


# ----- check_shell_command: denied -----

class TestShellDenied:
    def test_non_allowlisted_prefix(self):
        ok, _ = check_shell_command("rm -rf /")
        assert not ok

    def test_systemctl_state_changing(self):
        for cmd in ["systemctl restart sshd", "systemctl stop x", "systemctl enable y"]:
            ok, _ = check_shell_command(cmd)
            assert not ok, f"{cmd!r} must be denied"

    def test_deny_patterns(self):
        for cmd in ["modprobe foo", "insmod x.ko", "rmmod y"]:
            ok, _ = check_shell_command(cmd)
            assert not ok, f"{cmd!r} must be denied"

    def test_injection_via_metachar(self):
        for cmd in ["dmesg; rm -rf /", "uname | sh", "df & reboot"]:
            ok, _ = check_shell_command(cmd)
            assert not ok, f"{cmd!r} must be denied"

    def test_redirects_denied(self):
        # a relative-path redirect must not slip past the absolute-path deny
        for cmd in ["dmesg > junk", "dmesg > /tmp/x", "cat /proc/x < y"]:
            ok, _ = check_shell_command(cmd)
            assert not ok, f"{cmd!r} must be denied"

    def test_find_destructive_flags(self):
        for cmd in ["find / -delete", "find / -exec rm {} +"]:
            ok, _ = check_shell_command(cmd)
            assert not ok, f"{cmd!r} must be denied"

    def test_journalctl_vacuum(self):
        ok, _ = check_shell_command("journalctl --vacuum-size=1M")
        assert not ok

    def test_command_substitution(self):
        ok, _ = check_shell_command("cat /proc/$(whoami)")
        assert not ok

    def test_empty(self):
        ok, _ = check_shell_command("")
        assert not ok


# ----- check_path -----

class TestCheckPath:
    def test_proc_allowed(self):
        ok, _ = check_path("/proc/cpuinfo", safety.PROC_READ_ROOTS)
        assert ok

    def test_sysfs_allowed(self):
        ok, _ = check_path("/sys/class/net/eth0/address", safety.SYSFS_READ_ROOTS)
        assert ok

    def test_relative_rejected(self):
        ok, _ = check_path("proc/cpuinfo", safety.PROC_READ_ROOTS)
        assert not ok

    def test_dotdot_rejected(self):
        ok, _ = check_path("/proc/../etc/shadow", safety.PROC_READ_ROOTS)
        assert not ok

    def test_outside_root_rejected(self):
        ok, _ = check_path("/etc/shadow", safety.SYSFS_READ_ROOTS)
        assert not ok

    def test_control_char_rejected(self):
        ok, _ = check_path("/proc/cpu\ninfo", safety.PROC_READ_ROOTS)
        assert not ok


# ----- check_sysfs_write_target -----

class TestSysfsWrite:
    def test_gpio_allowed(self):
        ok, _ = check_sysfs_write_target("/sys/class/gpio/export")
        assert ok

    def test_leds_allowed(self):
        ok, _ = check_sysfs_write_target("/sys/class/leds/led0/brightness")
        assert ok

    def test_outside_write_root_rejected(self):
        ok, _ = check_sysfs_write_target("/sys/kernel/foo")
        assert not ok

    def test_high_risk_fragment_rejected(self):
        # under a write root, but contains a high-risk fragment
        ok, _ = check_sysfs_write_target("/sys/class/leds/watchdog/disable")
        assert not ok

    def test_dotdot_rejected(self):
        ok, _ = check_sysfs_write_target("/sys/class/gpio/../../kernel/x")
        assert not ok
