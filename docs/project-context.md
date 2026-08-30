# Metri — Project Context

> Documento de contexto do projeto **Metri**: investigação do ambiente,
> plano de implementação e decisões técnicas. Qualquer agente ou contribuidor
> DEVE consultar este documento antes de implementar.

---

## 1. Objetivo

Criar um widget de desktop estilo **Conky**: coletar métricas do sistema Linux
e exibi-las de forma estilizada na área de trabalho, com **transparência real**.

## 2. Investigação do ambiente (2026-08-28)

| Item | Resultado verificado |
|---|---|
| SO | Deepin 25 (Debian), `PRETTY_NAME="Deepin 25"` |
| Sessão gráfica | X11 (`XDG_SESSION_TYPE=x11`), `DISPLAY=:0` |
| Compositor/WM | **kwin_x11** (DDE usa KWin). Suporta transparência RGBA/ARGB. |
| Python 3.12 sistema | `/usr/bin/python3.12` (3.12.13) com **PyGObject 3.48.2** e **GTK3 3.24.41** funcionando (`gi`, `Gdk.Screen` OK) |
| asdf python | `3.14.7` instalado, **sem versão setada**; o shim `python3` quebra o `gi`. Usar `/usr/bin/python3.12` sempre. |
| tkinter | Não instalado (e não dá transparência desktop de qualquer forma) |
| Node/Rust | Não instalados (fora: Electron/Eww) |
| `conky` no apt | Não disponível no repositório do Deepin 25 |
| `psutil`/`yaml` | Não instalados (não usar) |
| Fontes de dados | `/proc` e `/sys` legíveis sem privilégios |

### 2.1 Fontes de dados confirmadas

**Temperaturas** — em `/sys/class/hwmon` (NÃO usar `thermal_zone*`, estão inativas):

| Sensor | Caminho | Exemplo real |
|---|---|---|
| CPU (AMD) | `hwmon4/k10temp/temp1_input` | `82125` (mili°C → 82.1°C) |
| GPU (AMD) | `hwmon3/amdgpu/temp1_input` | `68000` (mili°C → 68.0°C) |
| SSD | `hwmon1/nvme/temp1_input` | `63850` (mili°C → 63.9°C) |

Todos os `temp*_input` estão em **mili°C** (unidade 1000) → dividir por 1000.
Caminhos mapeados pelo rótulo (`/sys/class/hwmon/hwmon1/name` = `nvme`, etc.):
nenhum índice deve ser assumido fixo; descobrir pelo arquivo `name`.

**Bateria** — `/sys/class/power_supply/BAT0`:

| Campo | Exemplo real |
|---|---|
| `status` | `Not charging` |
| `capacity` | `98` (%) |
| `energy_now` | `30746000` (µWh) |
| `energy_full` | `31323000` (µWh) |
| `power_now` | `57000` (µW) |

**Rede** — `/proc/net/dev` (bytes RX/TX por interface). Interfaces: `wlo1`
(Wi-Fi), `enp1s0`, `nordlynx` (VPN), `lo`.

**Demais** — `/proc/stat` (jiffies CPU), `/proc/meminfo` (RAM/swap),
`/proc/uptime`, `/proc/version` + `/etc/os-release`, `os.statvfs()` (disco),
contagem de processos via `os.listdir('/proc')`.

## 3. Decisões técnicas

1. **Stack**: Python 3.12 + GTK3 (PyGObject). Shebang `/usr/bin/python3.12`.
2. **Zero dependências externas**: somente stdlib + `gi`.
3. **Janela desktop** (replicar o comportamento do conky):
   - `Gdk.Screen.get_rgba_visual()` + `set_app_paintable(True)` → transparência real (ARGB no X11 com compositor).
   - `set_decorated(False)` → sem bordas/título.
   - `set_skip_taskbar_hint(True)` e `set_skip_pager_hint(True)` → invisível em barras.
   - `set_type_hint(Gdk.WindowTypeHint.DOCK)`, `set_keep_below(True)`,
     `stick()` e `set_accept_focus(False)` → fixo na área de trabalho, atrás de
     tudo, em todos os workspaces, sem roubar foco.
   - Posicionamento por monitor + canto (configurável).
   - Atualização periódica via `GObject.timeout_add` (intervalo do config).
4. **Estilização**: CSS GTK (painel semi-transparente arredondado, fontes e
   cores configuráveis). Detalhes na skill `widget-desktop-gtk3`.
5. **Coleta**: módulo de sensores puro (sem GTK), retornando dicionários;
   detalhes na skill `metricas-sistema-linux`. **Convenção: coletores retornam
   bytes** (mem/swap/rss convertidos de kB ×1024; disco e rede já em bytes).
6. **`window_type` = DOCK por padrão, configurável** (`dock`|`desktop`):
   - O hint `DESKTOP` sob KWin faz o WM tratar a janela como parte do papel de
     parede. Ao clicar fora da janela (ou no show-desktop), o desktop é ativado
     e a janela é rebaixada para trás do papel — ficando invisível. Relato
     clássico: *"Clicking on desktop makes GTK3 window disappear"*.
   - `DOCK` + `keep_below` manteve o widget sempre visível acima do papel de
     parede (mas abaixo das demais janelas). É o default recomendado.
   - A escolha é feita no `metri.conf` (`window_type`), sem tocar no código.

## 4. Plano do app

```
metri/
├── main.py            # ponto de entrada (shebang /usr/bin/python3.12)
├── metri.conf         # configuração do usuário
├── style.css          # tema CSS GTK
└── metri/
    ├── __init__.py
    ├── app.py         # janela desktop + loop de atualização
    ├── sensors.py     # coletores de métricas (/proc, /sys)
    ├── widgets.py     # seções UI para cada métrica
    └── config.py      # parser do metri.conf
```

### 4.1 Métricas (conjunto completo)

- **CPU**: uso total + por núcleo (diff de jiffies de `/proc/stat`), temperatura (hwmon k10temp).
- **RAM/swap**: `/proc/meminfo` (MemTotal, MemAvailable; SwapTotal/SwapFree).
- **Uptime**: `/proc/uptime`.
- **Disco**: `os.statvfs()` em `/` e `$HOME`.
- **Rede**: `/proc/net/dev` — RX/TX da interface configurada (padrão `wlo1`).
- **Bateria**: `BAT0` (capacidade %, status, padrão de carga W).
- **Processos**: contagem (`/proc`) + top por CPU/memória via `/proc/<pid>/stat` + `/proc/<pid>/status`.
- **Sistema**: hostname, kernel, distribuição.

### 4.2 Configuração (`metri.conf`)

Arquivo texto simples ao lado do app. Ver schema completo na skill
`config-metri`. Campos previstos: `sections` (lista), `position`, `refresh`,
`monitor`, `font`/`font_size`, `colors` (`background`, `text`, `accent`),
`network_iface`, `width`, `margin`, `window_type` (`dock`|`desktop`).

## 5. Riscos e mitigação

- **KWin pode dar foco inicial à janela**: mitigado com `type_hint DOCK` (ou
  DESKTOP, configurável) + `keep_below` + `accept_focus(False)`. Se necessário,
  testar `set_visible`.
- **Posição/cores**: iterativo — tudo via `metri.conf`, sem alterar código.
- **Sensores ausentes** (ex.: máquina sem bateria/GPU nativa): cada seção deve
  se degradar graciosamente (mostrar placeholder ou ocultar seção).
- **Sessão de validação**: nunca derrubar a sessão; testar com `DISPLAY=:0`.