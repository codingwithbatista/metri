"""Parser do metri.conf — 100% stdlib."""

import sys
from pathlib import Path

RESOURCE_DIR = Path(__file__).resolve().parent.parent
USER_CONFIG_DIR = Path.home() / ".config" / "metri"
USER_CONFIG_FILE = USER_CONFIG_DIR / "metri.conf"
SHARE_CONFIG_FILE = Path("/usr/share/metri/metri.conf")


def _template_config_file():
    """Template do metri.conf: na raiz (dev) ou em /usr/share/metri (instalado)."""
    local = RESOURCE_DIR / "metri.conf"
    if local.exists():
        return local
    return SHARE_CONFIG_FILE

VALID_SECTIONS = {"system", "cpu", "memory", "disk", "network", "battery", "processes"}

DEFAULTS = {
    "position": "top-right",
    "refresh": 1.0,
    "width": 260,
    "margin": 20,
    "monitor": 0,
    "font": "Sans",
    "font_size": 12,
    "colors": {
        "background": "rgba(20, 20, 24, 0.65)",
        "text": "#e8e8e8",
        "accent": "#61afef",
        "dim": "#8a919f",
    },
    "sections": [
        "system", "cpu", "memory", "disk", "network", "battery", "processes",
    ],
    "network_iface": "wlo1",
    "window_type": "dock",
}

_INT_KEYS = {"width", "margin", "font_size", "monitor"}
_FLOAT_KEYS = {"refresh"}


def _coerce(key, value):
    if key in _INT_KEYS:
        try:
            return int(value)
        except ValueError:
            return value
    if key in _FLOAT_KEYS:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _deep_merge(base, override):
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _ensure_user_config():
    """Na primeira execução, cria o metri.conf do usuário a partir do template."""
    template = _template_config_file()
    try:
        if not USER_CONFIG_DIR.exists():
            USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not USER_CONFIG_FILE.exists() and template.exists():
            USER_CONFIG_FILE.write_text(template.read_text())
    except OSError:
        pass


def _resolve_config_path(path):
    """Define onde o metri.conf será lido: CLI > usuário > template."""
    if path:
        return Path(path)
    if not USER_CONFIG_FILE.exists():
        _ensure_user_config()
    if USER_CONFIG_FILE.exists():
        return USER_CONFIG_FILE
    return _template_config_file()


def load(path=None):
    """Lê o metri.conf e devolve a config fundida com os defaults."""
    cfg_path = _resolve_config_path(path)
    override = {}
    try:
        with open(cfg_path) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"')
                if not key:
                    continue
                target = override
                parts = key.split(".")
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = _coerce(parts[-1], value)
    except OSError:
        if path is not None:
            print(f"Metri: aviso — config não encontrado em {path}, usando defaults",
                  file=sys.stderr)

    merged = _deep_merge(DEFAULTS, override)

    for key in _INT_KEYS | _FLOAT_KEYS:
        if not isinstance(merged[key], (int, float)):
            merged[key] = DEFAULTS[key]
    if merged["refresh"] < 0.1:
        merged["refresh"] = DEFAULTS["refresh"]

    sections = merged["sections"]
    if isinstance(sections, str):
        sections = [s.strip() for s in sections.split(",") if s.strip()]
    merged["sections"] = [s for s in sections if s in VALID_SECTIONS]
    if not merged["sections"]:
        merged["sections"] = list(DEFAULTS["sections"])

    initials = ["top-right", "top-left", "bottom-right", "bottom-left"]
    if merged["position"] not in initials:
        merged["position"] = DEFAULTS["position"]

    monitor = merged["monitor"]
    if not isinstance(monitor, int) or monitor < 0:
        merged["monitor"] = DEFAULTS["monitor"]

    if merged["window_type"] not in {"dock", "desktop"}:
        merged["window_type"] = DEFAULTS["window_type"]

    return merged