---
title: Deploy Flow
tags: [deploy, infra, ubuntu, github-actions]
---

# 🚀 Flujo de Deploy (Auto, sin cPanel)

Objetivo: cada `git push origin main` despliega automáticamente **backend + frontend**
al servidor Ubuntu (host `192.168.1.249`, backend en la **VM-APP** `192.168.122.10`)
vía el **webhook de deploy**.

> El webhook y `server_deploy.sh` corren **dentro de VM-APP**; el host solo reenvía
> `127.0.0.1:5000` $\rightarrow$ `192.168.122.10:5000` con `moscowle-fwd.service` (socat).
> El frontend LAN (`/var/www/moscowle/app`, nginx en el host) y el de cPanel
> (`https://moscowle.centrojuanpabloii.com`) se sirven con el mismo `dist`.

## Diagrama

```mermaid
flowchart LR
    A[git push origin main] --> B[GitHub Actions<br/>ci.yml: tests + build]
    B --> C{deploy-ubuntu.yml}
    C -->|backend=true + frontend_dist.tar.gz| D[Webhook POST<br/>api-centrojuanpabloii.online/api/deploy/webhook]
    D --> E[server_deploy.sh]
    E --> F[Backend:<br/>git fetch + reset --hard origin/main<br/>systemctl restart moscowle]
    E --> G[Frontend:<br/>extraer dist tar en /var/www/moscowle/app<br/>systemctl reload nginx]
    E --> H[Obsidian note<br/>docs/obsidian_graph/Deployments/]
```

## Piezas

| Pieza | Archivo | Rol |
|---|---|---|
| Webhook backend | `app/routes/deploy_routes.py` | Recibe POST /api/deploy/webhook, valida token, lanza script |
| Script server | `scripts/server_deploy.sh` | pull backend + restart, extrae frontend + reload nginx, escribe nota Obsidian |
| Workflow CI | `.github/workflows/ci.yml` | tests backend + build frontend + `deploy-ubuntu` job |
| Workflow deploy | `.github/workflows/deploy-ubuntu.yml` | trigger backend + package/send dist frontend + smoke test |
| Config | `config.py` → `DEPLOY_WEBHOOK_TOKEN`, `DEPLOY_WEBHOOK_URL` | Secrets para el webhook |

## Secrets de GitHub requeridos

- `DEPLOY_WEBHOOK_URL` = `https://api-centrojuanpabloii.online/api/deploy/webhook`
- `DEPLOY_TOKEN` = mismo valor que `DEPLOY_WEBHOOK_TOKEN` en el `.env` del server

## Qué NO se usa

- ~~cPanel~~ — workflows antiguos eliminados (`deploy-backend.yml`, `deploy-frontend.yml`).
- ~~Railway / Docker~~ — fallback documentado, no es primario.

## Registro de deploys

Cada deploy crea una nota timestamped en [[Deployments]] (ver `docs/obsidian_graph/Deployments/`).
Log del server: `logs/auto_deploy.log`.
