"""pyOCD-based debug probe (CMSIS-DAP, ST-Link, etc.).

pyOCD (https://pyocd.io/) is a Python library for debugging ARM Cortex-M
MCUs.  It auto-detects CMSIS-DAP, ST-Link, J-Link and other probe hardware
— the user just needs to specify the target chip name.

All pyOCD calls are synchronous and blocking, so they run in a thread-pool
executor to avoid stalling the async event loop (same pattern as the serial
transport uses for pyserial).  Every operation is wrapped in an
``asyncio`` timeout so a wedged SWD transaction can never hang the server.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .base import ChipInfo, DebugProbe, ProbeError

# ---------------------------------------------------------------------------
# CPUID decoding table
# ---------------------------------------------------------------------------

_CPUID_PARTNO: dict[int, str] = {
    0xC20: "Cortex-M0",
    0xC60: "Cortex-M0+",
    0xC21: "Cortex-M1",
    0xC23: "Cortex-M3",
    0xC24: "Cortex-M4",
    0xC27: "Cortex-M7",
    0xD20: "Cortex-M23",
    0xD21: "Cortex-M33",
    0xD22: "Cortex-M55",
    0xD23: "Cortex-M85",
}

_CPUID_IMPL: dict[int, str] = {
    0x41: "ARM",
    0x42: "Broadcom",
    0x43: "Cavium",
    0x44: "DEC",
    0x46: "Freescale",
    0x47: "HiSilicon",
    0x49: "Infineon",
    0x4E: "NVIDIA",
    0x50: "APM",
    0x51: "Qualcomm",
    0x53: "Samsung",
    0x56: "TI",
}

# GD32F303 flash-size (KiB) -> SRAM size (KiB).  The FLM flash algorithm
# needs a default RAM region declared in the memory map; we size it from
# the detected flash so the algo's stack/buffers land in real SRAM.
_GD32F303_FLASH_TO_SRAM_KB: dict[int, int] = {
    256: 48,   # F303RC
    512: 64,   # F303RE
    1024: 96,  # F303RG
}

# Default per-operation timeout (seconds).  Flash operations override to
# a longer value via the ``timeout`` kwarg of _run.
_DEFAULT_TIMEOUT = 30.0
_FLASH_TIMEOUT = 180.0


def _decode_cpuid(cpuid: int) -> str:
    """Decode a Cortex-M CPUID register value into a human-readable name."""
    partno = (cpuid >> 4) & 0xFFF
    return _CPUID_PARTNO.get(partno, f"Cortex-M (part 0x{partno:03X})")


class PyOCDProbe(DebugProbe):
    """Debug probe backed by pyOCD's Python API.

    Supports any probe that pyOCD recognises — CMSIS-DAP, ST-Link,
    J-Link (via pyOCD), and others.  The probe type is auto-detected;
    only the target chip name needs configuration.

    For MCUs without a pyOCD built-in target (GD32, AT32, …), the generic
    ``cortex_m`` target is used and a CMSIS flash algorithm (.FLM) is
    loaded on demand for flash programming.
    """

    name = "pyocd"

    # Path to the GD32 flash algorithm shipped alongside this module.
    _FLM_PATH = Path(__file__).parent / "GD32F30x_HD.FLM"

    def __init__(
        self,
        target: str = "",
        frequency: int = 250_000,
    ) -> None:
        self._target = target or "cortex_m"
        self._frequency = frequency
        self._session: object | None = None  # pyocd.session.Session
        self._lock = asyncio.Lock()
        self._chip_info: ChipInfo | None = None  # cached
        self._flash_ready = False  # FLM algo loaded?

    # ---- helpers ---------------------------------------------------

    @property
    def _sess(self):  # type: ignore[return]
        """Return the pyOCD Session, raising if not connected."""
        if self._session is None:
            raise ProbeError("not connected — call connect() first")
        return self._session

    @property
    def _target_obj(self):
        """Return the pyocd Target object."""
        return self._sess.target

    def _exec(self, fn, *args, **kwargs):
        """Run a pyOCD operation synchronously, normalising errors.

        All pyOCD Session/Target methods are synchronous.  Errors are
        normalised into :class:`ProbeError` so callers catch one type.
        """
        try:
            return fn(*args, **kwargs)
        except ProbeError:
            raise
        except Exception as exc:
            raise ProbeError(str(exc)) from exc

    async def _run(self, fn, *args, timeout: float = _DEFAULT_TIMEOUT, **kwargs):
        """Async + timeout wrapper around a blocking pyOCD call.

        Runs ``fn`` in the thread executor while holding ``_lock`` (pyOCD
        is not re-entrant).  The whole call is bounded by ``timeout`` so a
        wedged SWD transaction surfaces as a :class:`ProbeError` instead of
        hanging the server forever.
        """
        async with self._lock:
            loop = asyncio.get_event_loop()
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, self._exec, fn, *args, **kwargs),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                # A timed-out SWD op usually leaves the probe in a bad
                # state — force a reconnect on the next call.
                self._invalidate_session()
                raise ProbeError(
                    f"probe operation timed out after {timeout:g}s — "
                    "SWD may be wedged, will reconnect on next call"
                ) from exc

    def _invalidate_session(self) -> None:
        """Mark the session stale so the next op reconnects."""
        # Best-effort close; ignore failures.
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        self._session = None
        self._flash_ready = False

    def _maybe_connect_sync(self) -> None:
        """Ensure the session is open (called inside _run)."""
        if self._session is not None and self._session.is_open:
            return
        self._connect_sync()

    def _connect_sync(self) -> None:
        from pyocd.core.session import Session
        from pyocd.probe.aggregator import DebugProbeAggregator

        # Close any stale session first.
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
            self._flash_ready = False

        probes = DebugProbeAggregator.get_all_connected_probes()
        if not probes:
            raise ProbeError(
                "No debug probe found — check USB connection and drivers"
            )

        probe = probes[0]
        # Set the SWD clock before open.  pyOCD's Session `frequency` option
        # also does this, but setting it on the link directly is reliable
        # across probe backends.  Guard with getattr for backend portability.
        try:
            probe._link._frequency = self._frequency  # noqa: SLF001
        except (AttributeError, TypeError):
            pass

        session = Session(
            probe,
            target_override=self._target,
            frequency=self._frequency,
            connect_mode="attach",
            auto_open=False,
        )
        session.open()
        self._session = session
        self._flash_ready = False

    # ---- connect / disconnect / is_alive / describe  -----------------

    async def connect(self) -> None:
        await self._run(self._maybe_connect_sync, timeout=10.0)

    async def disconnect(self) -> None:
        async with self._lock:
            if self._session is not None:
                loop = asyncio.get_event_loop()
                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(None, self._session.close),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    pass
                self._session = None
                self._flash_ready = False

    async def is_alive(self) -> bool:
        try:
            await self._run(
                lambda: self._target_obj.read32(0xE000ED00), timeout=5.0
            )
            return True
        except ProbeError:
            return False

    def describe(self) -> str:
        target = self._target
        freq = self._frequency // 1000
        return f"pyocd://{target}@{freq}kHz"

    # ---- chip_info --------------------------------------------------

    async def chip_info(self) -> ChipInfo:
        # Return cached info if we still have a live session.
        if self._chip_info is not None and self._session is not None:
            return self._chip_info

        def _read() -> ChipInfo:
            target = self._target_obj

            # CPUID at 0xE000ED00 (Cortex-M CPUID register).
            cpuid = target.read32(0xE000ED00)
            cpu = _decode_cpuid(cpuid)
            implementer = (cpuid >> 24) & 0xFF
            vendor = _CPUID_IMPL.get(implementer, f"0x{implementer:02X}")

            # DBGMCU_IDCODE @ 0xE0042000 — works for STM32, GD32, AT32 etc.
            dev_id = ""
            try:
                idcode = target.read32(0xE0042000)
                dev_id = f"0x{idcode:08X}"
            except Exception:
                pass

            flash_kb = self._read_flash_kb_sync()

            # SRAM size: prefer the real memory map; fall back to a
            # flash-size lookup table for GD32F303 variants.
            ram_kb = _GD32F303_FLASH_TO_SRAM_KB.get(flash_kb, 0)

            return ChipInfo(
                target=dev_id,
                vendor=target.vendor if getattr(target, "vendor", "") else vendor,
                family=target.family if getattr(target, "family", "") else cpu,
                cpu=cpu,
                flash_size=flash_kb * 1024,
                ram_size=ram_kb * 1024,
            )

        info = await self._run(_read, timeout=10.0)
        self._chip_info = info
        return info

    def _read_flash_kb_sync(self) -> int:
        """Read flash size in KiB from 0x1FFFF7E0 (STM32/GD32 compatible)."""
        try:
            fval = self._target_obj.read32(0x1FFFF7E0)
            flash_kb = fval & 0xFFFF
            if 0 < flash_kb <= 2048:
                return flash_kb
        except Exception:
            pass
        return 1024  # safe fallback for GD32F303RG

    # ---- execution control ------------------------------------------

    async def reset(self, halt: bool = True) -> None:
        def _reset():
            target = self._target_obj
            if halt:
                target.reset_and_halt()
            else:
                target.reset()

        # Reset invalidates cached state.
        self._chip_info = None
        await self._run(_reset, timeout=10.0)

    async def halt(self) -> None:
        await self._run(lambda: self._target_obj.halt(), timeout=10.0)

    async def resume(self) -> None:
        await self._run(lambda: self._target_obj.resume(), timeout=10.0)

    # ---- memory access ----------------------------------------------

    async def read_mem(self, addr: int, size: int) -> bytes:
        def _read() -> bytes:
            target = self._target_obj
            raw = target.read_memory_block8(addr, size)
            # pyOCD returns list[int]; normalise to bytes.
            if isinstance(raw, (list, bytearray)):
                return bytes(raw)
            return raw  # bytes

        return await self._run(_read, timeout=15.0)

    async def write_mem(self, addr: int, data: bytes) -> None:
        def _write():
            self._target_obj.write_memory_block8(addr, list(data))

        await self._run(_write, timeout=15.0)

    # ---- core registers ---------------------------------------------

    async def read_core_reg(self, reg: str) -> int:
        def _read() -> int:
            return self._target_obj.read_core_register(reg)

        return await self._run(_read, timeout=10.0)

    async def write_core_reg(self, reg: str, value: int) -> None:
        def _write():
            self._target_obj.write_core_register(reg, value)

        await self._run(_write, timeout=10.0)

    # ---- flash ------------------------------------------------------
    #
    # pyOCD's generic ``cortex_m`` target has no flash algorithm, so we
    # inject a FlashRegion backed by the GD32F30x_HD.FLM CMSIS algorithm.
    # The FLM runs *on the target CPU*, which is the reliable way to
    # program GD32 flash — direct SWD writes to the FMC peripheral are
    # unreliable on this probe/chip combination.

    def _setup_flash_sync(self) -> None:
        """Inject + finalise the FLM flash algorithm into the target.

        Idempotent: skips work if ``_flash_ready`` is already set.
        """
        if self._flash_ready:
            return

        from pyocd.core.memory_map import FlashRegion, MemoryType, RamRegion
        from pyocd.target.pack.flash_algo import PackFlashAlgo
        from pyocd.target.pack.flm_region_builder import FlmFlashRegionBuilder

        if not self._FLM_PATH.is_file():
            raise ProbeError(
                f"Flash algorithm not found: {self._FLM_PATH} — "
                "copy GD32F30x_HD.FLM from D:\\Keil_v5\\ARM\\Flash\\"
            )

        target = self._target_obj
        mem_map = target.memory_map
        flash_kb = self._read_flash_kb_sync()
        sram_kb = _GD32F303_FLASH_TO_SRAM_KB.get(flash_kb, 48)

        # 1. The generic cortex_m target ships with eight 512MB placeholder
        #    regions, all marked default=True.  Left in place, the FLM algo
        #    builder picks one and loads the algo to non-existent memory.
        #    Strip every RAM placeholder and install one real SRAM region.
        for r in list(mem_map.regions):
            if r.type == MemoryType.RAM:
                mem_map.remove_region(r)
        mem_map.add_region(
            RamRegion(
                start=0x20000000,
                length=sram_kb * 1024,
                is_default=True,
            )
        )

        # 2. Remove any stale (non-finalised) flash region at 0x08000000.
        existing = mem_map.get_region_for_address(0x08000000)
        if existing is not None:
            mem_map.remove_region(existing)

        # 3. Add the flash region.  Pass a PackFlashAlgo object directly
        #    so FlmFlashRegionBuilder doesn't need to resolve a file path.
        pack_algo = PackFlashAlgo(str(self._FLM_PATH))
        flash_region = FlashRegion(
            start=0x08000000,
            length=flash_kb * 1024,
            sector_size=2048,
            blocksize=2048,
            flm=pack_algo,
            is_boot_memory=True,
            erased_byte_value=0xFF,
        )
        mem_map.add_region(flash_region)

        # 4. Finalise: parse the FLM into an algo dict + sector subregions.
        builder = FlmFlashRegionBuilder(target, mem_map)
        if not builder.finalise_region(flash_region):
            raise ProbeError("Failed to load FLM flash algorithm (finalise_region)")
        if flash_region.algo is None:
            raise ProbeError("FLM did not produce a flash algo dict")

        # 5. Create the Flash instance and bi-bind it to the region, exactly
        #    as the target's `create_flash` init task does.  This makes both
        #    direct Flash calls and FileProgrammer/FlashLoader (which read
        #    `region.flash`) work.
        from pyocd.flash.flash import Flash

        flash_obj = Flash(target, flash_region.algo)
        flash_obj.region = flash_region
        try:
            flash_region.flash = flash_obj
        except (AttributeError, TypeError):
            flash_region._flash = flash_obj  # noqa: SLF001

        self._flash_ready = True

    def _get_flash_obj(self):
        """Return the (Flash, region) bound during _setup_flash_sync."""
        region = self._target_obj.memory_map.get_region_for_address(0x08000000)
        if region is None or region.algo is None:
            raise ProbeError("flash region not set up")
        flash = getattr(region, "flash", None)
        if flash is None:
            raise ProbeError("flash object not bound to region")
        return flash, region

    async def flash(self, local_path: str, base_addr: int = 0) -> None:
        """Program a .bin or .hex file onto the target using the FLM algo.

        The CPU is halted first (the algo requires it).  Sector erase is
        performed automatically for the programmed ranges.
        """
        from pyocd.flash.file_programmer import FileProgrammer

        ext = Path(local_path).suffix.lower()

        def _flash():
            target = self._target_obj
            target.halt()
            self._setup_flash_sync()

            programmer = FileProgrammer(self._sess, chip_erase="sector")
            if ext == ".hex":
                programmer.add_file(local_path, file_format="hex")
            else:
                programmer.add_file(
                    local_path, base_address=base_addr, file_format="bin"
                )
            programmer.commit()

        # Flashing can take a while for large images; allow up to 3 min.
        await self._run(_flash, timeout=_FLASH_TIMEOUT)

    async def erase(self, addr: int | None = None, size: int | None = None) -> None:
        """Erase flash. (None, None) = mass erase; else erase the sector
        range covering [addr, addr+size)."""

        def _erase():
            from pyocd.flash.flash import Flash

            target = self._target_obj
            target.halt()
            self._setup_flash_sync()
            flash, region = self._get_flash_obj()

            flash.init(Flash.Operation.ERASE)
            try:
                if addr is None:
                    flash.erase_all()
                else:
                    # Erase every sector overlapping [addr, addr+size).
                    sector_size = region.sector_size or 2048
                    start = region.start
                    first = (addr - start) // sector_size
                    last = (addr + size - 1 - start) // sector_size
                    for s in range(first, last + 1):
                        flash.erase_sector(start + s * sector_size)
            finally:
                flash.cleanup()

        await self._run(_erase, timeout=_FLASH_TIMEOUT)


__all__ = ["PyOCDProbe"]
