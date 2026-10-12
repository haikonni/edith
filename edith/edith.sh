#!/bin/bash
# Edith - Personal AI Assistant Web Server
# Usage: edith.sh [start|stop|status|restart]

cd /opt/data/edith
PIDFILE="/tmp/edith.pid"
LOG="/tmp/edith.log"

start() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat $PIDFILE) 2>/dev/null; then
        echo "Edith já está rodando (PID $(cat $PIDFILE))"
        return
    fi
    echo "Iniciando Edith..."
    if [ -f /opt/data/.env ]; then set -a; . /opt/data/.env; set +a; fi
    /opt/data/.hermes/venv-edith/bin/python3 server.py > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2
    if kill -0 $(cat $PIDFILE) 2>/dev/null; then
        echo "✓ Edith iniciada em http://localhost:5000"
        echo "  PID: $(cat $PIDFILE)"
    else
        echo "✗ Falha ao iniciar"
        cat "$LOG"
    fi
}

stop() {
    if [ -f "$PIDFILE" ]; then
        kill $(cat $PIDFILE) 2>/dev/null
        rm -f "$PIDFILE"
        echo "Edith parada"
    else
        echo "Edith não está rodando"
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat $PIDFILE) 2>/dev/null; then
        echo "✓ Edith rodando (PID $(cat $PIDFILE))"
        echo "  Acesso: http://localhost:5000"
    else
        echo "✗ Edith não está rodando"
    fi
}

case "${1:-status}" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 {start|stop|status|restart}" ;;
esac
