#!/bin/bash
# Doble clic: arranca el motor y abre la consola en el navegador. Cierra esta ventana para detenerlo.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Portinatx Nowcast necesita Python 3.\nAbre Terminal y ejecuta: xcode-select --install" buttons {"OK"}'
  exit 1
fi
exec python3 MeteoPortinatx.pyz
