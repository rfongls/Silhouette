import os
import time
from typing import Callable, Tuple, Any, Dict

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def get_cpu_load() -> float:
    """Return current system CPU load percentage."""
    if psutil:
        return psutil.cpu_percent(interval=None)
    try:
        return os.getloadavg()[0]
    except Exception:  # pragma: no cover - platform dependent
        return 0.0


class PerformanceProfiler:
    """Profile CPU, memory and IO usage for a function call."""

    def profile(self, func: Callable[..., Any], *args, **kwargs) -> Tuple[Any, Dict[str, float]]:
        start = time.perf_counter()
        if psutil:
            proc = psutil.Process(os.getpid())
            cpu_start = proc.cpu_times()
            mem_start = proc.memory_info()
            io_start = proc.io_counters() if hasattr(proc, "io_counters") else None
        else:  # pragma: no cover - psutil not installed
            proc = None
            cpu_start = mem_start = io_start = None
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        metrics = {"duration": duration}
        if psutil and proc:
            cpu_end = proc.cpu_times()
            mem_end = proc.memory_info()
            metrics["cpu_time"] = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
            metrics["memory_mb"] = (mem_end.rss - mem_start.rss) / (1024 ** 2)
            if io_start:
                io_end = proc.io_counters()
                metrics["io_read_mb"] = (io_end.read_bytes - io_start.read_bytes) / (1024 ** 2)
                metrics["io_write_mb"] = (io_end.write_bytes - io_start.write_bytes) / (1024 ** 2)
        return result, metrics
