# --- web app ---
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- backend ---
FROM golang:1.27-alpine AS backend
WORKDIR /src
COPY backend/go.mod backend/go.sum ./
RUN go mod download
COPY backend/ ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /should-we .

# --- runtime ---
FROM alpine:3.22
RUN apk add --no-cache ca-certificates tzdata
WORKDIR /app
COPY --from=backend /should-we /app/should-we
COPY --from=web /web/dist /app/pb_public
VOLUME /app/pb_data
EXPOSE 8090
HEALTHCHECK --interval=60s --timeout=5s CMD wget -qO- http://127.0.0.1:8090/api/health || exit 1
CMD ["/app/should-we", "serve", "--http=0.0.0.0:8090", "--dir=/app/pb_data", "--publicDir=/app/pb_public"]
