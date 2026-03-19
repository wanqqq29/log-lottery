FROM docker.gh-proxy.org/node:22-alpine AS frontend-builder

ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

WORKDIR /app

COPY package.json pnpm-lock.yaml .npmrc ./
RUN npm config set registry "${NPM_CONFIG_REGISTRY}" \
    && corepack enable \
    && corepack prepare pnpm@10.26.1 --activate \
    && pnpm config set registry "${NPM_CONFIG_REGISTRY}"
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM docker.gh-proxy.org/nginx:1.26-alpine

COPY --from=frontend-builder /app/dist /usr/share/nginx/html/log-lottery
COPY deploy/docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
