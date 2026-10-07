#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE"
command -v python3 >/dev/null || { echo 'Python 3 é necessário.' >&2; exit 1; }
for arquivo in .env .env.ingestion; do
  [[ -f "$arquivo" ]] || { echo "Arquivo necessário ausente: $BASE/$arquivo" >&2; exit 1; }
done
COMPOSE=(docker compose --project-directory "$BASE" --env-file "$BASE/.env" --env-file "$BASE/.env.ingestion")
"${COMPOSE[@]}" config --format json | python3 -c '
import json,pathlib,sys
config=json.load(sys.stdin)
mount=next((v for v in config["services"]["api"].get("volumes",[]) if v.get("target")=="/app/question-bank-assets"),None)
if not mount or mount.get("type")!="bind":sys.exit("Erro: volume de imagens da API não configurado.")
p=pathlib.Path(mount["source"])
if not p.is_dir() or not any(p.iterdir()):sys.exit(f"Erro: diretório de imagens ausente ou vazio: {p}")
print(f"Diretório de imagens: {p}")
'
"${COMPOSE[@]}" build api frontend
"${COMPOSE[@]}" up -d db
"${COMPOSE[@]}" run --rm --no-deps api python -m app.migrate
"${COMPOSE[@]}" up -d --force-recreate api frontend
echo 'Atualização concluída com o volume de imagens configurado.'
