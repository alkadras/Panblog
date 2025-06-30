#!/bin/bash

PID_FILE="/storage/emulated/0/www/panblog/server.pid"
PUBLIC_DIR="/storage/emulated/0/www/panblog/public"
PORT=8000

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null; then
            echo "Sunucu zaten çalışıyor (PID: $PID)."
            exit 1
        else
            echo "Eski PID dosyası bulundu, ancak işlem çalışmıyor. Temizleniyor..."
            rm "$PID_FILE"
        fi
    fi

    echo "Web sunucusu başlatılıyor..."
    (cd "$PUBLIC_DIR" && python -m http.server $PORT & echo $! > "$PID_FILE") &>/dev/null &
    PID=$(cat "$PID_FILE")
    echo "Web sunucusu başlatıldı. PID: $PID. Port: $PORT. (http://localhost:$PORT)"
}

stop_server() {
    echo "Tüm Python HTTP sunucuları aranıyor ve durduruluyor..."
    PIDS=$(ps aux | grep 'python -m http.server' | grep -v grep | awk '{print $2}')

    if [ -z "$PIDS" ]; then
        echo "Çalışan bir Python HTTP sunucusu bulunamadı."
    else
        for PID in $PIDS;
        do
            echo "PID $PID durduruluyor..."
            kill $PID
        done
        echo "Tüm Python HTTP sunucuları durduruldu."
    fi

    if [ -f "$PID_FILE" ]; then
        echo "PID dosyası temizleniyor..."
        rm "$PID_FILE"
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    *)
        echo "Kullanım: $0 {start|stop}"
        exit 1
        ;;
esac