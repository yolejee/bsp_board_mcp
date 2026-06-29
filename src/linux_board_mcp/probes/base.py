"""DebugProbe abstract base for JTAG/SWD debug probes.

This mirrors the Transport ABC pattern — it defines the interface that
every debug probe backend (pyOCD, OpenOCD, J-Link) must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProbeError(Exception):
    """Raised when the debug probe fails to communicate with the target."""


@dataclass
class ChipInfo:
    """Target chip identification returned by chip_info()."""

    target: str  # e.g. "stm32f407vet6"
    vendor: str  # e.g. "STMicroelectronics"
    family: str  # e.g. "STM32F4"
    cpu: str  # e.g. "Cortex-M4"
    flash_size: int  # bytes
    ram_size: int  # bytes

    def format(self) -> str:
        return (
            f"target:     {self.target}\n"
            f"vendor:     {self.vendor}\n"
            f"family:     {self.family}\n"
            f"cpu:        {self.cpu}\n"
            f"flash_size: {self.flash_size // 1024} KiB\n"
            f"ram_size:   {self.ram_size // 1024} KiB"
        )


class DebugProbe(ABC):
    """Abstract interface for CMSIS-DAP / J-Link / OpenOCD debug probes.

    This is the MCU equivalent of Transport — it abstracts JTAG/SWD
    communication so McuTools doesn't care which probe hardware is used.
    Implementations are in probes/pyocd.py (and future openocd / jlink).
    """

    name: str = "base"

    @abstractmethod
    async def connect(self) -> None:
        """Open the debug probe and attach to the target."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Detach from target and close the probe."""

    @abstractmethod
    async def is_alive(self) -> bool:
        """Return True if the probe is connected and the target is responsive."""

    @abstractmethod
    def describe(self) -> str:
        """Short human-readable string for audit logs / error messages."""

    # ---- chip identity ----

    @abstractmethod
    async def chip_info(self) -> ChipInfo:
        """Return target chip identification (cpu, flash/ram size, etc.)."""

    # ---- execution control ----

    @abstractmethod
    async def reset(self, halt: bool = True) -> None:
        """Reset the target MCU. If halt=True, stop at the reset vector."""

    @abstractmethod
    async def halt(self) -> None:
        """Halt (pause) the CPU core."""

    @abstractmethod
    async def resume(self) -> None:
        """Resume execution from the current PC."""

    # ---- memory access ----

    @abstractmethod
    async def read_mem(self, addr: int, size: int) -> bytes:
        """Read `size` bytes from `addr`. Raises ProbeError on fault."""

    @abstractmethod
    async def write_mem(self, addr: int, data: bytes) -> None:
        """Write `data` to `addr`. Raises ProbeError on fault."""

    # ---- core register access ----

    @abstractmethod
    async def read_core_reg(self, reg: str) -> int:
        """Read a CPU core register.

        Typical register names for ARM Cortex-M:
        r0-r15, sp, lr, pc, xpsr, msp, psp, control, primask, basepri, faultmask.
        """

    @abstractmethod
    async def write_core_reg(self, reg: str, value: int) -> None:
        """Write a value to a CPU core register."""

    # ---- flash programming ----

    @abstractmethod
    async def flash(self, local_path: str, base_addr: int = 0) -> None:
        """Program firmware (bin/hex/elf) onto the target.

        local_path is the firmware file on the developer machine.
        base_addr is the offset where programming starts (default 0).
        """

    @abstractmethod
    async def erase(self, addr: int | None = None, size: int | None = None) -> None:
        """Erase flash.

        (None, None):   chip mass erase.
        (addr, size):   sector/region erase starting at addr for size bytes.
        """