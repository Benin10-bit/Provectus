# Estágio 1: Build e Instalação de dependências
FROM python:3.11-slim as builder

# Define variáveis de ambiente para o Python não gerar .pyc e não usar buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala ferramentas de compilação necessárias (se houver dependências C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências no diretório de pacotes do usuário
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Estágio 2: Imagem final de execução
FROM python:3.11-slim

WORKDIR /app

# Copia apenas as dependências instaladas do estágio anterior
COPY --from=builder /install /usr/local

# Instala apenas a lib necessária para o PostgreSQL (runtime)
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copia o código da aplicação
COPY . .

# Expõe a porta que o FastAPI usa
EXPOSE 8000

# Comando para rodar a aplicação com Uvicorn
# Usamos 4 workers para aguentar o volume de acessos no Dashboard
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]