# Metri

Widget de desktop estilo **Conky** para Linux que coleta métricas do sistema e
as exibe de forma estilizada na área de trabalho, com **transparência real**.

![Licença](https://img.shields.io/badge/licença-MIT-blue)

## Recursos

- **Zero dependências externas** — apenas stdlib + PyGObject (GTK3).
  Nada de `psutil`, `yaml` ou requisições. Dados vêm direto de `/proc` e `/sys`.
- **Transparência real** via visual RGBA/ARGB no X11 (com compositor).
- **Janela desktop**: sem decoração, fixa atrás de tudo, em todos os workspaces,
  sem roubar foco.
- **Métricas**: sistema, CPU (uso + temperatura), memória/swap, disco, rede
  (RX/TX), bateria, temperatura e processos.
- **Configurável** via `metri.conf`: posição, cor, fonte, seções, interface de
  rede, largura e margem — sem tocar no código.
- Degrada graciosamente quando um sensor não existe (ex.: sem bateria → oculta
  a seção).

## Requisitos / ambiente alvo

- **Python 3.12 do sistema** com **PyGObject** (`gi`) e **GTK3**.
  Use `/usr/bin/python3.12` (o `python3` do shell pode ser um shim sem `gi`).
- Sessão **X11** com um compositor que suporte transparência (testado com
  Deepin 25 / KWin / X11).

```
sudo apt install python3-gi gir1.2-gtk-3.0
```

## Uso

```sh
./main.py
# ou
/usr/bin/python3.12 main.py
```

## Configuração

O arquivo `metri.conf` fica ao lado do app. Exemplo:

```ini
# canto da tela: top-right | top-left | bottom-right | bottom-left
position = top-right
# intervalo de atualização em segundos
refresh = 1.0
# largura do painel e distância da borda (px)
width = 260
margin = 20
# monitor (0 = primário)
monitor = 0

# aparência
font = "Sans, monospace"
font_size = 12
colors.background = rgba(20, 20, 24, 0.65)
colors.text = #e8e8e8
colors.accent = #61afef
colors.dim = #8a919f

# conteúdo
sections = system, cpu, memory, disk, network, battery, processes
network_iface = wlo1
```

Veja o arquivo `metri.conf` incluído no projeto para todas as opções comentadas.

## Estrutura do projeto

```
metri/
├── main.py            # ponto de entrada (shebang /usr/bin/python3.12)
├── metri.conf         # configuração do usuário
├── style.css          # tema CSS GTK
├── metri/             # pacote da aplicação
│   ├── app.py         # janela desktop + loop de atualização
│   ├── sensors.py     # coletores de métricas (/proc, /sys)
│   ├── widgets.py     # seções UI para cada métrica
│   └── config.py      # parser do metri.conf
└── docs/
    └── project-context.md   # investigação, plano e decisões técnicas
```

## Licença

[MIT](LICENSE)
