#!/bin/bash
set -e

PROJECT_DIR="/home/beni/EsPCEx/provectus"
PORT=80
APP_NAME="Provectus"
ICON_PATH="/home/beni/.local/share/icons/hicolor/256x256/apps/provectus.png"

notify() {
    notify-send -i "$ICON_PATH" "$APP_NAME" "$1"
}

# Verifica se o Docker está rodando
if ! systemctl is-active --quiet docker; then
    notify "🐳 Docker inativo. Iniciando serviço..."
    sudo systemctl start docker
    sleep 3

    if ! systemctl is-active --quiet docker; then
        notify "❌ Falha ao iniciar o Docker. Abortando."
        exit 1
    fi

    notify "✅ Docker iniciado com sucesso."
fi

# Vai para o diretório do projeto
cd "$PROJECT_DIR" || {
    notify "❌ Erro ao acessar o diretório do projeto."
    exit 1
}

# Verifica se algum container do docker compose está rodando
RUNNING_CONTAINERS=$(docker compose ps -q 2>/dev/null)

if [ -n "$RUNNING_CONTAINERS" ]; then
    notify "🚀 Abrindo aplicativo..."
else
    notify "📦 Subindo containers..."
    docker compose up -d

    notify "⏳ Aguardando inicialização do servidor..."
    sleep 5

    # Aguarda a porta estar disponível (até 30s)
    TIMEOUT=30
    ELAPSED=0
    while ! curl -s --max-time 2 "http://localhost:$PORT" > /dev/null 2>&1; do
        sleep 2
        ELAPSED=$((ELAPSED + 2))
        if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
            notify "⚠️ Servidor demorou para responder. Tentando abrir mesmo assim..."
            break
        fi
    done

    notify "🚀 Sistema pronto! Abrindo no navegador..."
fi

# Abre no navegador
chromium --app="http://localhost:$PORT" &