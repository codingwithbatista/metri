#!/usr/bin/python3.12
"""Ponto de entrada do Metri — widget de desktop estilo Conky."""

import argparse
import signal

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from metri import config
from metri.app import Widget, _load_styles


def main():
    parser = argparse.ArgumentParser(description="Metri — widget de métricas")
    parser.add_argument(
        "-c", "--config", default=None,
        help="caminho alternativo do metri.conf "
             "(padrão: ~/.config/metri/metri.conf)",
    )
    args = parser.parse_args()

    cfg = config.load(args.config)
    _load_styles(cfg)

    signal.signal(signal.SIGINT, lambda *_args: Gtk.main_quit())

    widget = Widget(cfg)
    widget.connect("delete-event", lambda *_args: Gtk.main_quit())
    widget.start()
    Gtk.main()


if __name__ == "__main__":
    main()