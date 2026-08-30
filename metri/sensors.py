"""Coletores de métricas via /proc e /sys — somente stdlib, sem GTK."""

import glob
import os
import time


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


# --------------------------------------------------------------------------- CPU

_CPU_PREV = {}


def _cpu_sample():
    sample = {}
    try:
        with open("/proc/stat") as f:
            for line in f:
                if not line.startswith("cpu"):
                    break
                parts = line.split()
                vals = [int(v) for v in parts[1:]]
                idle = vals[3] + vals[4]
                sample[parts[0]] = (idle, sum(vals))
    except (OSError, ValueError):
        pass
    return sample


def cpu():
    """Uso % por núcleo via diff de jiffies entre duas amostras."""
    global _CPU_PREV
    current = _cpu_sample()
    usage = {}
    for name, (idle, total) in current.items():
        prev = _CPU_PREV.get(name)
        if prev:
            idle_delta = idle - prev[0]
            total_delta = total - prev[1]
            usage[name] = (total_delta - idle_delta) * 100.0 / total_delta if total_delta else 0.0
        else:
            usage[name] = 0.0
    _CPU_PREV = current
    total = usage.pop("cpu", 0.0)
    cores = {name: max(0.0, min(100.0, pct)) for name, pct in usage.items()}
    return {"total": max(0.0, min(100.0, total)), "cores": cores}


# ------------------------------------------------------------------------- Memória

def memory():
    data = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    fields = parts[1].strip().split()
                    if fields:
                        data[parts[0]] = int(fields[0])
    except (OSError, ValueError):
        return None

    total = data.get("MemTotal", 0) * 1024
    available = data.get("MemAvailable", data.get("MemFree", 0)) * 1024
    swap_total = data.get("SwapTotal", 0) * 1024
    swap_free = data.get("SwapFree", 0) * 1024
    used = total - available
    return {
        "total": total,
        "available": available,
        "used": used,
        "percent": used * 100.0 / total if total else 0.0,
        "swap_total": swap_total,
        "swap_used": swap_total - swap_free,
    }


def uptime():
    raw = _read("/proc/uptime")
    if not raw:
        return None
    try:
        return float(raw.split()[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------- Disco

def disk(path=os.sep):
    try:
        sv = os.statvfs(path)
    except OSError:
        return None
    total = sv.f_blocks * sv.f_frsize
    free = sv.f_bavail * sv.f_frsize
    used = total - free
    return {
        "path": path,
        "total": total,
        "used": used,
        "free": free,
        "percent": used * 100.0 / total if total else 0.0,
    }


# ----------------------------------------------------------------------------- Rede

_NET_PREV = None
_NET_TIME = None


def network(iface):
    """Taxa RX/TX (bytes/s) da interface via diff de /proc/net/dev."""
    global _NET_PREV, _NET_TIME
    now = time.monotonic()
    sample = {}
    try:
        with open("/proc/net/dev") as f:
            lines = f.readlines()[2:]
        for line in lines:
            name, rest = line.split(":")
            parts = rest.split()
            sample[name.strip()] = (int(parts[0]), int(parts[8]))
    except (OSError, ValueError, IndexError):
        return {"rx": 0.0, "tx": 0.0, "iface": iface, "present": False}

    result = {"rx": 0.0, "tx": 0.0, "iface": iface, "present": iface in sample}
    if not result["present"]:
        return result

    rx, tx = sample[iface]
    if _NET_PREV is not None and iface in _NET_PREV and _NET_TIME is not None:
        elapsed = now - _NET_TIME
        if elapsed > 0:
            prev_rx, prev_tx = _NET_PREV[iface]
            result["rx"] = max(rx - prev_rx, 0) / elapsed
            result["tx"] = max(tx - prev_tx, 0) / elapsed

    _NET_PREV = sample
    _NET_TIME = now
    return result


# --------------------------------------------------------------------------- Bateria

def _battery_base():
    bases = glob.glob("/sys/class/power_supply/BAT*")
    return bases[0] if bases else None


def battery():
    base = _battery_base()
    if not base:
        return None

    def value(name):
        raw = _read(f"{base}/{name}")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return raw

    energy_full = value("energy_full")
    energy_now = value("energy_now")
    capacity = value("capacity")
    power_now = value("power_now")

    if isinstance(capacity, int):
        percent = capacity
    elif isinstance(energy_full, int) and isinstance(energy_now, int) and energy_full:
        percent = energy_now * 100.0 / energy_full
    else:
        percent = None

    return {
        "status": _read(f"{base}/status"),
        "percent": percent,
        "power_w": power_now / 1e6 if isinstance(power_now, (int, float)) else None,
    }


# ---------------------------------------------------------------------- Temperaturas

def temps():
    out = {}
    for hw in glob.glob("/sys/class/hwmon/hwmon[0-9]*"):
        name = _read(f"{hw}/name")
        if not name:
            continue
        inputs = sorted(glob.glob(f"{hw}/temp*_input"))
        if not inputs:
            continue
        raw = _read(inputs[0])
        if raw:
            try:
                out[name] = int(raw) / 1000.0
            except ValueError:
                continue
    return out


# ---------------------------------------------------------------------- Processos

def _proc_name(pid):
    raw = _read(f"/proc/{pid}/stat")
    if not raw:
        return "?"
    try:
        return raw[raw.index("(") + 1:raw.rindex(")")]
    except ValueError:
        return "?"


def processes(top=3):
    count = 0
    rows = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        count += 1
        try:
            with open(f"/proc/{entry}/status") as f:
                rss = None
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss = int(line.split()[1])
                        break
            if rss:
                rows.append((entry, _proc_name(entry), rss * 1024))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda row: row[2], reverse=True)
    return {"count": count, "top": rows[:top]}


# -------------------------------------------------------------------------- Sistema

def _os_release():
    raw = _read("/etc/os-release")
    if not raw:
        return None
    for line in raw.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def system():
    return {
        "host": _read("/etc/hostname") or os.uname().nodename,
        "os": _os_release() or "Linux",
        "kernel": os.uname().release,
    }


# -------------------------------------------------------------------- Agregador

def collect(config):
    """Coleta todas as métricas num dict único, tolerante a falhas isoladas."""
    iface = config.get("network_iface", "wlo1")
    data = {}
    for key, collector in (
        ("system", system),
        ("cpu", cpu),
        ("memory", memory),
        ("uptime", uptime),
        ("disk_root", lambda: disk(os.sep)),
        ("disk_home", lambda: disk(os.path.expanduser("~"))),
        ("network", lambda: network(iface)),
        ("battery", battery),
        ("temps", temps),
        ("processes", processes),
    ):
        try:
            data[key] = collector()
        except Exception:
            data[key] = None
    return data