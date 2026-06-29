"""MCU tools for bare-metal debugging via JTAG/SWD debug probes.

Unlike the Linux tools (split into readonly / writable), MCU tools live
in a single class because even "read" operations may require halting the
CPU — a state change.  Tools marked DESTRUCTIVE in their docstrings will
trigger per-call approval in the MCP client.

Input validation happens before the probe is called (same pattern as the
Linux tools: return REJECTED: strings on bad input).  Probe-level errors
return PROBE_UNREACHABLE: so the LLM can distinguish "bad args" from
"board not connected".
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..audit import AuditLog
from ..probes.base import DebugProbe, ProbeError

# ---- constants ----

_MAX_READ_SIZE = 4096  # bytes, to keep responses reasonable
_MAX_WRITE_SIZE = 1024  # bytes per write_mem call
_ADDR_MAX = 0xFFFF_FFFF  # 32-bit address space
_VALID_REG_NAMES: frozenset[str] = frozenset(
    {
        # ARM Cortex-M core registers (the universally available set)
        "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
        "sp", "lr", "pc", "xpsr",
        "msp", "psp",
        "primask", "basepri", "faultmask", "control",
    }
)

_HEX_STRIP_RE = re.compile(r"[\s\n\r]+")


class McuTools:
    """Tools that operate on a bare-metal MCU via a debug probe.

    Constructor receives a DebugProbe ABC (same pattern as the Linux
    tool classes receiving a Transport ABC) — the tools don't know or
    care which probe hardware is on the other end.
    """

    def __init__(self, probe: DebugProbe, audit: AuditLog) -> None:
        self.probe = probe
        self.audit = audit

    # ---- helpers ---------------------------------------------------

    async def _ensure_connected(self) -> str | None:
        """Connect the probe if not already connected.

        Returns None on success, or an error string on failure.
        """
        try:
            if not await self.probe.is_alive():
                await self.probe.connect()
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("_connect", {}, msg, ok=False)
            return msg
        return None

    @staticmethod
    def _check_addr(addr: int, *, label: str = "addr") -> str | None:
        """Return a REJECTED string if the address is out of range, else None."""
        if not isinstance(addr, int) or addr < 0 or addr > _ADDR_MAX:
            return f"REJECTED: {label} must be an integer in [0, 0x{_ADDR_MAX:X}]"
        return None

    def _audit(self, tool: str, args: dict, result: str, *, ok: bool = True) -> None:
        self.audit.write(tool, args, result[:200], ok=ok)

    # ---- chip info -------------------------------------------------

    async def chip_info(self) -> str:
        """Return target chip identity (CPU core, flash/RAM size, vendor).

        Uses the debug probe to read the chip's ROM table and device ID.
        """
        args: dict = {}
        if err := await self._ensure_connected():
            return err
        try:
            info = await self.probe.chip_info()
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_chip_info", args, msg, ok=False)
            return msg
        out = info.format()
        self._audit("mcu_chip_info", args, out, ok=True)
        return out

    # ---- memory read -----------------------------------------------

    async def read_mem(self, addr: int, size: int = 256) -> str:
        """Read a block of memory from the target MCU.

        Returns a hexdump (offset, hex bytes, ASCII preview).
        addr: start address (supports hex notation).
        size: number of bytes to read (clamped to [1, 4096]).
        """
        # Validate.
        err = self._check_addr(addr)
        if err:
            return err
        size = max(1, min(int(size), _MAX_READ_SIZE))
        args = {"addr": hex(addr), "size": size}

        if err := await self._ensure_connected():
            return err
        try:
            data = await self.probe.read_mem(addr, size)
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_read_mem", args, msg, ok=False)
            return msg

        out = self._hexdump(data, base=addr)
        self._audit("mcu_read_mem", args, out[:200], ok=True)
        return out

    # ---- memory write ----------------------------------------------

    async def write_mem(self, addr: int, data_hex: str) -> str:
        """DESTRUCTIVE: write bytes to the target MCU's memory.

        addr: destination address (supports hex notation).
        data_hex: hex-encoded bytes, e.g. "deadbeef" or "00 11 22 ff".
                  Whitespace is stripped automatically.
        """
        err = self._check_addr(addr)
        if err:
            return err

        # Normalise hex input: strip whitespace, validate chars.
        clean = _HEX_STRIP_RE.sub("", data_hex.strip())
        if len(clean) % 2 != 0:
            return "REJECTED: data_hex must have an even number of hex digits"
        if not re.match(r"^[0-9a-fA-F]+$", clean):
            return "REJECTED: data_hex contains non-hex characters"
        size = len(clean) // 2
        if size > _MAX_WRITE_SIZE:
            return f"REJECTED: data_hex too large (max {_MAX_WRITE_SIZE} bytes)"
        if size == 0:
            return "REJECTED: data_hex is empty"

        args = {"addr": hex(addr), "data_hex": data_hex[:80], "size": size}
        if err := await self._ensure_connected():
            return err
        try:
            data = bytes.fromhex(clean)
            await self.probe.write_mem(addr, data)
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_write_mem", args, msg, ok=False)
            return msg

        out = f"OK: wrote {size} bytes to 0x{addr:08X}"
        self._audit("mcu_write_mem", args, out, ok=True)
        return out

    # ---- register read / write ------------------------------------

    async def read_reg(self, reg: str) -> str:
        """Read a CPU core register from the target MCU.

        Valid registers for ARM Cortex-M:
        r0-r15, sp, lr, pc, xpsr, msp, psp, primask, basepri, faultmask, control.
        """
        reg_norm = reg.strip().lower()
        if reg_norm not in _VALID_REG_NAMES:
            return (
                f"REJECTED: unknown register {reg!r}. "
                f"Valid names: {', '.join(sorted(_VALID_REG_NAMES))}"
            )
        args = {"reg": reg_norm}
        if err := await self._ensure_connected():
            return err
        try:
            value = await self.probe.read_core_reg(reg_norm)
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_read_reg", args, msg, ok=False)
            return msg

        out = f"{reg_norm} = 0x{value:08X} ({value})"
        self._audit("mcu_read_reg", args, out, ok=True)
        return out

    async def write_reg(self, reg: str, value: int) -> str:
        """DESTRUCTIVE: write a value to a CPU core register.

        Valid registers for ARM Cortex-M:
        r0-r15, sp, lr, pc, xpsr, msp, psp, primask, basepri, faultmask, control.
        """
        reg_norm = reg.strip().lower()
        if reg_norm not in _VALID_REG_NAMES:
            return (
                f"REJECTED: unknown register {reg!r}. "
                f"Valid names: {', '.join(sorted(_VALID_REG_NAMES))}"
            )
        if not isinstance(value, int) or value < 0 or value > _ADDR_MAX:
            return f"REJECTED: value must be a 32-bit unsigned integer"

        args = {"reg": reg_norm, "value": hex(value)}
        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.write_core_reg(reg_norm, value)
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_write_reg", args, msg, ok=False)
            return msg

        out = f"OK: {reg_norm} = 0x{value:08X}"
        self._audit("mcu_write_reg", args, out, ok=True)
        return out

    # ---- execution control ----------------------------------------

    async def reset(self, halt: bool = True) -> str:
        """DESTRUCTIVE: reset the target MCU.

        If halt=True (default), the CPU stops at the reset vector after
        reset so you can inspect initial state before the firmware runs.
        If halt=False, the firmware starts executing immediately.
        """
        args = {"halt": halt}
        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.reset(halt=halt)
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_reset", args, msg, ok=False)
            return msg

        suffix = " (halted)" if halt else ""
        out = f"OK: target reset{suffix}"
        self._audit("mcu_reset", args, out, ok=True)
        return out

    async def halt(self) -> str:
        """DESTRUCTIVE: halt (pause) the target CPU.

        After halting you can read memory, registers, and inspect state.
        Use mcu_resume to continue execution.
        """
        args: dict = {}
        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.halt()
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_halt", args, msg, ok=False)
            return msg

        out = "OK: CPU halted"
        self._audit("mcu_halt", args, out, ok=True)
        return out

    async def resume(self) -> str:
        """DESTRUCTIVE: resume the target CPU from a halted state."""
        args: dict = {}
        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.resume()
        except ProbeError as e:
            msg = f"PROBE_UNREACHABLE: {e}"
            self._audit("mcu_resume", args, msg, ok=False)
            return msg

        out = "OK: CPU resumed"
        self._audit("mcu_resume", args, out, ok=True)
        return out

    # ---- flash ----------------------------------------------------

    async def flash(self, local_path: str, base_addr: int = 0) -> str:
        """DESTRUCTIVE: program firmware onto the target MCU.

        local_path: firmware file on the developer machine (.bin or .hex).
        base_addr: base address for the firmware image (default 0).

        The tool auto-detects .bin (raw binary) vs .hex (Intel Hex) by
        extension.  For .bin files the base_addr is used directly.
        """
        if not os.path.isfile(local_path):
            return f"REJECTED: local file {local_path!r} not found"

        ext = Path(local_path).suffix.lower()
        if ext not in (".bin", ".hex"):
            return f"REJECTED: firmware must be .bin or .hex, got {ext!r}"

        err = self._check_addr(base_addr, label="base_addr")
        if err:
            return err

        args = {"local_path": local_path, "base_addr": hex(base_addr)}
        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.flash(local_path, base_addr)
        except ProbeError as e:
            msg = f"FLASH_FAILED: {e}"
            self._audit("mcu_flash", args, msg, ok=False)
            return msg

        try:
            size = os.path.getsize(local_path)
        except OSError:
            size = -1
        if ext == ".hex":
            # .hex carries its own addresses; base_addr is ignored.
            out = f"OK: flashed {local_path} ({size} bytes, hex — addresses from file)"
        else:
            out = (
                f"OK: flashed {local_path} at 0x{base_addr:08X} "
                f"({size} bytes, bin)"
            )
        self._audit("mcu_flash", args, out, ok=True)
        return out

    async def erase(self, addr: int | None = None, size: int | None = None) -> str:
        """DESTRUCTIVE: erase flash memory on the target MCU.

        No arguments: chip mass erase (erases everything).
        addr + size: erase the sector/region covering [addr, addr+size).
        """
        args: dict
        is_mass = addr is None and size is None

        if is_mass:
            args = {"mass_erase": True}
            if err := await self._ensure_connected():
                return err
        else:
            if addr is None or size is None:
                return "REJECTED: pass both addr and size, or neither (for mass erase)"
            err = self._check_addr(addr)
            if err:
                return err
            if size <= 0:
                return "REJECTED: size must be positive"
            if addr + size > _ADDR_MAX:
                return f"REJECTED: addr+size exceeds 0x{_ADDR_MAX:X}"
            args = {"addr": hex(addr), "size": hex(size)}

        if err := await self._ensure_connected():
            return err
        try:
            await self.probe.erase(addr, size)
        except ProbeError as e:
            msg = f"ERASE_FAILED: {e}"
            self._audit("mcu_erase", args, msg, ok=False)
            return msg

        if is_mass:
            out = "OK: mass erase complete"
        else:
            out = f"OK: erased {size} bytes at 0x{addr:08X}"
        self._audit("mcu_erase", args, out, ok=True)
        return out

    # ---- hexdump formatter ----------------------------------------

    @staticmethod
    def _hexdump(data: bytes, base: int = 0) -> str:
        """Format bytes as a classic hexdump: offset, hex, ASCII."""
        lines: list[str] = []
        for offset in range(0, len(data), 16):
            chunk = data[offset : offset + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            # Pad hex to 48 chars (16 * 3 - 1).
            hex_part = hex_part.ljust(47)
            ascii_part = "".join(
                chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk
            )
            lines.append(f"{base + offset:08X}: {hex_part} |{ascii_part}|")
        return "\n".join(lines)