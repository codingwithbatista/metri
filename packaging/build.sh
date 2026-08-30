#!/bin/sh
# Empacota o Metri em um pacote .deb
#
# Uso: ./packaging/build.sh [versão]
#   versão (opcional): sobrescreve a versão do pacote (padrão: do control)

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILES="$ROOT/packaging/files"
DEB="$ROOT/packaging/deb"

VERSION="${1:-$(sed -n 's/^Version: //p' "$FILES/DEBIAN/control")}"

PKG="metri_${VERSION}_amd64.deb"
OUT="$ROOT/dist/$PKG"

echo "==> Gerando pacote $PKG"

# 1. Limpa e remonta a árvore final
rm -rf "$DEB"
mkdir -p "$DEB"

# 2. Arquivos de empacotamento estáticos
cp -a "$FILES/." "$DEB/"

# 3. Código da aplicação (a partir da raiz do projeto)
mkdir -p "$DEB/usr/lib/metri/metri"
cp "$ROOT/main.py"        "$DEB/usr/lib/metri/main.py"
cp "$ROOT/style.css"      "$DEB/usr/lib/metri/style.css"
cp "$ROOT/metri/"*.py     "$DEB/usr/lib/metri/metri/"

# 4. Permissões executáveis
chmod 755 \
    "$DEB/usr/bin/metri" \
    "$DEB/DEBIAN/postinst" \
    "$DEB/DEBIAN/postrm"

# 5. Empacota com dono root
mkdir -p "$ROOT/dist"
dpkg-deb --build --root-owner-group "$DEB" "$OUT" >/dev/null

echo "==> Pronto: $OUT"
