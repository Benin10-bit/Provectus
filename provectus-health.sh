#!/bin/bash

TOPIC="provectus"
CONTAINER="fastapi_app"
STATUS_FILE="/tmp/provectus_status"

# Pega status do container
RAW_STATUS=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' $CONTAINER 2>/dev/null)

# Traduz status
if [ $? -ne 0 ]; then
    CURRENT="OFFLINE ❌"
elif [ "$RAW_STATUS" = "healthy" ]; then
    CURRENT="ONLINE ✅"
elif [ "$RAW_STATUS" = "unhealthy" ]; then
    CURRENT="PROBLEMA ⚠️"
else
    CURRENT="INICIANDO ⏳"
fi

# Pega status anterior
PREVIOUS=$(cat $STATUS_FILE 2>/dev/null)

# Só notifica se mudou
if [ "$CURRENT" != "$PREVIOUS" ]; then
    curl -H "Priority: high" \
         -H "Title: Provectus" \
         -d "Status: $CURRENT" \
         ntfy.sh/$TOPIC

    echo "$CURRENT" > $STATUS_FILE
fi
