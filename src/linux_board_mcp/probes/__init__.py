"""Debug probe implementations and factory."""

from .base import ChipInfo, DebugProbe, ProbeError


def build_probe(cfg) -> DebugProbe:
    """Factory: pick the right debug probe based on config.

    Mirrors `transports.build_transport()` — one place to dispatch on
    the probe type string.
    """
    if cfg.probe_type == "pyocd":
        try:
            from .pyocd import PyOCDProbe
        except ImportError:
            raise ImportError(
                "pyocd is not installed. Install it with:\n"
                "  uv sync --extra mcu\n"
                "or:\n"
                "  pip install pyocd"
            ) from None

        return PyOCDProbe(
            target=cfg.probe_target,
            frequency=cfg.probe_frequency,
        )
    raise ValueError(f"unknown probe type: {cfg.probe_type!r}")


__all__ = ["ChipInfo", "DebugProbe", "ProbeError", "build_probe"]