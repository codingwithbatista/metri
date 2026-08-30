"""Seções de UI do Metri — cada seção devolve (box, updater)."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

BAR_WIDTH = 14


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_size(nbytes):
    if nbytes is None:
        return "—"
    n = float(nbytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{int(n)} B" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024
    return "—"


def _fmt_rate(bps):
    if bps is None:
        return "—"
    n = float(bps)
    for unit in ("B/s", "KiB/s", "MiB/s", "GiB/s"):
        if abs(n) < 1024 or unit == "GiB/s":
            return f"{n:.1f} {unit}"
        n /= 1024
    return "—"


def _fmt_uptime(seconds):
    if seconds is None:
        return "—"
    d, rem = divmod(int(seconds), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _bar(percent, width=BAR_WIDTH):
    if percent is None:
        return "░" * width
    filled = round(max(0.0, min(100.0, percent)) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _label(css_class):
    label = Gtk.Label(xalign=0, xpad=0)
    label.get_style_context().add_class(css_class)
    label.set_line_wrap(False)
    return label


def _title(text, cfg):
    label = _label("metric-title")
    label.set_markup(f'<span foreground="{_escape(cfg["colors"]["accent"])}">{_escape(text)}</span>')
    return label


def _section_box():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    box.get_style_context().add_class("section")
    return box


# -------------------------------------------------------------------------- seções

def system_section(cfg):
    box = _section_box()
    info = _label("metric-value")
    box.pack_start(_title("SISTEMA", cfg), False, False, 0)
    box.pack_start(info, False, False, 0)

    def update(data):
        system = data.get("system") or {}
        dim = _escape(cfg["colors"]["dim"])
        info.set_markup(
            f"{_escape(system.get('host', '—'))}\n"
            f'<span foreground="{dim}">{_escape(system.get("os", "—"))}'
            f" · {_escape(system.get('kernel', '—'))}</span>\n"
            f"uptime {_fmt_uptime(data.get('uptime'))}"
        )

    return box, update


def cpu_section(cfg):
    box = _section_box()
    total = _label("metric-value")
    cores = _label("metric-label")
    sensors = _label("metric-label")
    box.pack_start(_title("CPU", cfg), False, False, 0)
    box.pack_start(total, False, False, 0)
    box.pack_start(cores, False, False, 0)
    box.pack_start(sensors, False, False, 0)

    def update(data):
        cpu = data.get("cpu") or {}
        accent = _escape(cfg["colors"]["accent"])
        pct = cpu.get("total", 0.0)
        total.set_markup(
            f'<span foreground="{accent}">{_bar(pct)}</span> {pct:4.1f}%'
        )

        core_names = sorted(cpu.get("cores", {}), key=lambda n: int(n[3:]))
        lines, row = [], []
        for idx, name in enumerate(core_names):
            row.append(f"{name[3:]}:{cpu['cores'][name]:3.0f}%")
            if len(row) == 4 or idx == len(core_names) - 1:
                lines.append("  ".join(row))
                row = []
        cores.set_text("\n".join(lines) if core_names else "—")

        temp_map = data.get("temps") or {}
        labels = {"k10temp": "CPU", "amdgpu": "GPU", "nvme": "SSD"}
        parts = [f"{label} {temp_map[key]:.0f}°" for key, label in labels.items() if key in temp_map]
        sensors.set_text(" · ".join(parts) if parts else "")

    return box, update


def memory_section(cfg):
    box = _section_box()
    ram = _label("metric-value")
    swap = _label("metric-label")
    box.pack_start(_title("MEMÓRIA", cfg), False, False, 0)
    box.pack_start(ram, False, False, 0)
    box.pack_start(swap, False, False, 0)

    def update(data):
        mem = data.get("memory")
        if not mem:
            return
        accent = _escape(cfg["colors"]["accent"])
        pct = mem.get("percent", 0.0)
        ram.set_markup(
            f'<span foreground="{accent}">{_bar(pct)}</span> {pct:4.1f}%\n'
            f"{_fmt_size(mem.get('used'))} / {_fmt_size(mem.get('total'))}"
        )
        swap_total = mem.get("swap_total", 0)
        if swap_total:
            swap_used = mem.get("swap_used", 0)
            swap.set_text(f"swap {_fmt_size(swap_used)} / {_fmt_size(swap_total)}"
                          f" ({swap_used * 100.0 / swap_total:.0f}%)")
        else:
            swap.set_text("swap —")

    return box, update


def disk_section(cfg):
    box = _section_box()
    rows = [
        ("/", _label("metric-value")),
        ("~", _label("metric-value")),
    ]
    box.pack_start(_title("DISCO", cfg), False, False, 0)
    for _, label in rows:
        box.pack_start(label, False, False, 0)

    def update(data):
        accent = _escape(cfg["colors"]["accent"])
        for mount, label in rows:
            key = "disk_root" if mount == "/" else "disk_home"
            info = data.get(key)
            if not info:
                label.set_text(f"{mount} —")
                continue
            pct = info.get("percent", 0.0)
            label.set_markup(
                f'<span foreground="{accent}">{_bar(pct)}</span> {pct:4.1f}%  {mount}\n'
                f"{_fmt_size(info.get('used'))} / {_fmt_size(info.get('total'))}"
            )

    return box, update


def network_section(cfg):
    box = _section_box()
    title = _label("metric-title")
    rx = _label("metric-value")
    tx = _label("metric-value")
    box.pack_start(title, False, False, 0)
    box.pack_start(rx, False, False, 0)
    box.pack_start(tx, False, False, 0)

    def update(data):
        net = data.get("network") or {}
        iface = net.get("iface", cfg.get("network_iface", "wlo1"))
        title.set_markup(
            f'<span foreground="{_escape(cfg["colors"]["accent"])}">REDE ({_escape(iface)})</span>'
        )
        rx.set_text(f"▼ {_fmt_rate(net.get('rx'))}")
        tx.set_text(f"▲ {_fmt_rate(net.get('tx'))}")

    return box, update


def battery_section(cfg):
    box = _section_box()
    main = _label("metric-value")
    detail = _label("metric-label")
    box.pack_start(_title("BATERIA", cfg), False, False, 0)
    box.pack_start(main, False, False, 0)
    box.pack_start(detail, False, False, 0)

    def update(data):
        bat = data.get("battery")
        if not bat:
            box.hide()
            return
        box.show()
        accent = _escape(cfg["colors"]["accent"])
        pct = bat.get("percent")
        main.set_markup(
            f'<span foreground="{accent}">{_bar(pct)}</span> {pct:.0f}%'
            if pct is not None
            else "—"
        )
        parts = [str(bat.get("status") or "")]
        if bat.get("power_w"):
            parts.append(f"{bat['power_w']:.1f}W")
        detail.set_text(" · ".join(p for p in parts if p) or "—")

    return box, update


def processes_section(cfg):
    box = _section_box()
    count = _label("metric-label")
    top = _label("metric-value")
    box.pack_start(_title("PROCESSOS", cfg), False, False, 0)
    box.pack_start(count, False, False, 0)
    box.pack_start(top, False, False, 0)

    def update(data):
        procs = data.get("processes") or {}
        count.set_text(f"{procs.get('count', 0)} processos")
        lines = []
        for pid, name, rss in procs.get("top", []):
            lines.append(f"{pid:>6}  {name[:24]:<24} {_fmt_size(rss)}")
        top.set_text("\n".join(lines) if lines else "—")

    return box, update