#!/bin/bash

PATH=/usr/bin:/bin:/usr/local/bin
TOPIC="provectus"
CONTAINER="fastapi_app"
STATUS_FILE="/home/beni/.provectus_status"

send_notification() {
    CURRENT="$1"
    PREVIOUS=$(cat $STATUS_FILE 2>/dev/null)
    if [ "$CURRENT" != "$PREVIOUS" ]; then
        /usr/bin/curl -H "Priority: high" \
                      -H "Title: Provectus" \
                      -d "Status: $CURRENT" \
                      ntfy.sh/$TOPIC
        echo "$CURRENT" > $STATUS_FILE
    fi
}

# 🔥 Limpa status anterior para garantir notificação após reboot
rm -f $STATUS_FILE

# 🔥 Espera Docker subir
until /usr/bin/docker info > /dev/null 2>&1; do
    sleep 2
done

# 🔥 Espera container existir
until /usr/bin/docker inspect $CONTAINER > /dev/null 2>&1; do
    sleep 2
done

# 🔥 Espera health estabilizar
while true; do
    STATUS=$(/usr/bin/docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{end}}' $CONTAINER 2>/dev/null)

    if [ "$STATUS" = "healthy" ]; then
        send_notification "ONLINE ✅"
        break
    elif [ "$STATUS" = "unhealthy" ]; then
        send_notification "PROBLEMA ⚠️"
        break
    fi

    sleep 2
done

# 🔥 Loop infinito resiliente
while true; do
    /usr/bin/docker events \
      --filter "container=$CONTAINER" \
      --format '{{.Action}}' | while read status; do

        case "$status" in
            "health_status: healthy")
                send_notification "ONLINE ✅"
                ;;
            "health_status: unhealthy")
                send_notification "PROBLEMA ⚠️"
                ;;
            "die")
                send_notification "OFFLINE ❌"
                ;;
        esac

    done

    # Se o docker events morrer, reinicia automaticamente
    sleep 2
done