# Metri — Convenções do Projeto

Widget de desktop estilo Conky: coleta métricas do sistema Linux e as exibe de
forma estilizada na área de trabalho, com transparência real.

## Stack

- **Python 3.12 do sistema** (`/usr/bin/python3.12`) — possui PyGObject (`gi`)
  e GTK3 instalados e funcionando.
- **GTK3 via PyGObject** para a janela e a interface.
- **Zero dependências externas**: nada de `psutil`, `yaml`, requisições, etc.
  Todos os dados vêm de `/proc` e `/sys` (padrão stdlib).
- **IMPORTANTE**: o `python3` do shell é o shim do `asdf` **sem versão setada**
  e quebra o `gi`. Os scripts DEVE usarem `/usr/bin/python3.12` no shebang ou
  invocação explícita. Não criar `.tool-versions` para o app (o `gi` não existe
  no Python do asdf).

## Ambiente alvo (verificado em 2026-08-28)

- Deepin 25 (Debian), sessão **X11**, compositor **kwin_x11** (DDE).
- Hostname `vaio`, kernel `6.6.143-amd64-desktop-hwe`.
- Temperaturas via `/sys/class/hwmon`: `hwmon4/k10temp` (CPU), `hwmon3/amdgpu`
  (GPU), `hwmon1/nvme` (SSD) — valores em **mili°C** (dividir por 1000).
  As `thermal_zone*` estão inativas e NÃO devem ser usadas.
- Bateria em `/sys/class/power_supply/BAT0`.
- Interfaces de rede: `wlo1` (Wi-Fi), `enp1s0`, `nordlynx`, `lo`.

## Estrutura

```
metri/
├── main.py            # ponto de entrada (shebang /usr/bin/python3.12)
├── metri.conf         # configuração do usuário
├── style.css          # tema CSS GTK
├── metri/             # pacote da aplicação
│   ├── __init__.py
│   ├── app.py         # janela desktop + loop de atualização
│   ├── sensors.py     # coletores de métricas (/proc, /sys)
│   ├── widgets.py     # seções UI para cada métrica
│   └── config.py      # parser do metri.conf
└── docs/
    └── project-context.md   # investigação, plano e decisões técnicas
```

## Agentes e skills

- **`metri-dev`** (primário, `mode: all`): implementa o app. Carrega as skills
  conforme a tarefa via tool `skill` (ver o mapa skill→tarefa no corpo do
  agente).
- **`metri-revisor`** (subagente, `edit: deny`): revisa o código antes de
  finalizar, carregando `revisao-metri`.
- Skills: `widget-desktop-gtk3`, `metricas-sistema-linux`, `config-metri`,
  `revisao-metri`.

Antes de implementar, **consultar `docs/project-context.md`**.

## Regras de resposta

- Responder em português, exceto identificadores e nomes de código.
- Comentários apenas quando estritamente necessários.
- Explicar mudanças com referências `arquivo:linha`.
- Ao finalizar qualquer implementação, **executar o app no ambiente real** para
  validar (sem quebrar a sessão) e reportar o resultado.