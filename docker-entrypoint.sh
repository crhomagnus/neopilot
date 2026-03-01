#!/bin/bash
set -e

# Inicia Xvfb para suporte a apps GUI sem display físico
if [ -n "$DISPLAY" ] && ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    Xvfb "$DISPLAY" -screen 0 1920x1080x24 &
    sleep 1
    echo "Xvfb iniciado em $DISPLAY"
fi

# Inicia LibreOffice server em background se necessário
if [ "${NEOPILOT_ENABLE_LIBREOFFICE:-true}" = "true" ]; then
    soffice --headless \
        --accept="socket,host=localhost,port=2002;urp;StarOffice.ServiceManager" \
        --norestore \
        --nocrashreport &
    echo "LibreOffice server iniciado (porta 2002)"
fi

exec "$@"
