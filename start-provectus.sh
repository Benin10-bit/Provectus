#!/bin/bash
set -x
PROJECT_DIR="/home/beni/EsPCEx/provectus"
PORT=80

# Verifica se o Docker está rodando
if ! systemctl is-active --quiet docker; then
    echo "Docker não está rodando. Iniciando..."
    sudo systemctl start docker
    sleep 3
fi

# Vai para o diretório do projeto
cd "$PROJECT_DIR" || {
    echo "Erro ao acessar $PROJECT_DIR"
    exit 1
}

# Verifica se algum container do docker compose está rodando
RUNNING_CONTAINERS=$(docker compose ps -q)

if [ -n "$RUNNING_CONTAINERS" ]; then
    echo "Containers já estão rodando."
else
    echo "Subindo containers..."
    docker compose up -d
    echo "Aguardando inicialização..."
    sleep 5
fi

# Abre no navegador
echo "Abrindo no navegador..."
chromium --app=http://localhost:$PORT &