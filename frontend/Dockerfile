# ESTÁGIO 1: Build (Transforma o código React em arquivos estáticos)
FROM node:18-alpine AS build

WORKDIR /app

# Copia arquivos de dependências primeiro (otimiza o cache do Docker)
COPY package.json package-lock.json ./
RUN npm ci

# Copia o restante do código
COPY . .

# Recebe a URL da API como argumento no momento do build
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Gera a pasta /dist
RUN npm run build

# ESTÁGIO 2: Serve (Usa o Nginx para entregar os arquivos)
FROM nginx:alpine

# Copia os arquivos gerados no estágio anterior para a pasta do Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# CONFIGURAÇÃO AUTOMÁTICA DO NGINX:
# Resolve o problema comum de dar "404" ao atualizar a página em SPAs (React Router)
# Substitua a configuração automática por esta:
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
