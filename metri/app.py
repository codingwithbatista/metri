"""Janela desktop do Metri — transparência, ancoragem e loop de atualização."""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GObject, GLib

from . import config as config_mod
from . import sensors
from . import widgets

STYLE_FILE = config_mod.RESOURCE_DIR / "style.css"


def _load_styles(cfg):
    base = Gtk.CssProvider()
    try:
        base.load_from_path(str(STYLE_FILE))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), base,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
    except GLib.Error:
        pass

    colors = cfg["colors"]
    runtime = (
        "window.desktop-widget { background-color: rgba(0, 0, 0, 0); }\n"
        f".panel {{ background-color: {colors['background']}; }}\n"
        f".metric-title {{ color: {colors['accent']}; }}\n"
        f".metric-label {{ color: {colors['dim']}; }}\n"
        f".metric-value {{ color: {colors['text']}; "
        f"font-family: {cfg['font']}; font-size: {cfg['font_size']}px; }}\n"
    )
    provider = Gtk.CssProvider()
    provider.load_from_data(runtime.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
    )


class Widget(Gtk.Window):
    def __init__(self, cfg):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.cfg = cfg
        self._timer_id = None

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        hint = (Gdk.WindowTypeHint.DOCK
                if self.cfg.get("window_type", "dock") == "dock"
                else Gdk.WindowTypeHint.DESKTOP)
        self.set_type_hint(hint)
        self.set_keep_below(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_resizable(False)
        self.stick()
        self.connect("map-event", self._on_map)
        self.connect("destroy", self._on_destroy)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("panel")
        root.set_size_request(cfg["width"], -1)
        self.add(root)

        self._updaters = []
        for name in cfg["sections"]:
            builder = getattr(widgets, f"{name}_section", None)
            if not builder:
                continue
            section, updater = builder(cfg)
            self._updaters.append(updater)
            root.pack_start(section, False, False, 0)
            if name != cfg["sections"][-1]:
                root.pack_start(
                    Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                    False, False, 0,
                )

    def start(self):
        self.show_all()
        self.set_keep_below(True)
        self.stick()
        self._place()
        self._timer_id = GObject.timeout_add(
            int(self.cfg["refresh"] * 1000), self._refresh
        )
        self._refresh()

    def _on_map(self, *_):
        self.set_keep_below(True)
        self.stick()
        return False

    def _place(self):
        screen = Gdk.Screen.get_default()
        n_monitors = screen.get_n_monitors()
        monitor = min(max(0, self.cfg.get("monitor", 0)), n_monitors - 1)
        mon = screen.get_monitor_geometry(monitor)
        width, height = self.get_size()
        margin = self.cfg["margin"]
        position = self.cfg["position"]

        corners = {
            "top-right": (mon.x + mon.width - width - margin, mon.y + margin),
            "top-left": (mon.x + margin, mon.y + margin),
            "bottom-right": (mon.x + mon.width - width - margin,
                             mon.y + mon.height - height - margin),
            "bottom-left": (mon.x + margin,
                            mon.y + mon.height - height - margin),
        }
        x, y = corners.get(position, corners["top-right"])
        self.move(x, y)

    def _refresh(self):
        data = sensors.collect(self.cfg)
        for updater in self._updaters:
            try:
                updater(data)
            except Exception:
                continue
        return True

    def _on_destroy(self, *_):
        if self._timer_id is not None:
            GObject.source_remove(self._timer_id)
            self._timer_id = None