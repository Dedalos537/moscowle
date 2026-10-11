# Landing pública: centrojuanpabloii.com

React + three.js (Vite). El contenido se edita desde la plataforma, en **Configuración › Equipo › Sitio web**, y se
lee de la API `/api/landing` (módulo aparte del backend, `app/routes/landing_routes.py`). Si la API no responde, la
página usa `app/data/landing_default.json`, que también es el texto inicial del backend.

## Qué hace

- **Agendar la evaluación**: WhatsApp con el mensaje ya armado (nombre, edad, área y horario), llamada directa, o
  dejar el número para que el centro llame. Cada contacto queda registrado en la bandeja del admin con aviso.
- **Escenas 3D** (bloques lógicos): hero, recorrido de la evaluación con el scroll y torre de cifras. three.js se
  descarga después del primer pintado, se pausa fuera de pantalla y respeta `prefers-reduced-motion`. Sin WebGL se
  muestra una versión plana.

## Desarrollo

```bash
cd landing
npm install
npm run dev                         # http://localhost:5180 (usa la API de producción, ver .env.example)
LANDING_BASE=/ npm run build        # build para la raíz del dominio
```

## Publicar (cPanel, por FTP)

La CI (`ci.yml`, job «Landing Build») compila la versión para la raíz y para `/nuevo/` y deja el artefacto
`landing-cpanel` en cada push a `main`.

```bash
venv/bin/python scripts/deploy_landing.py --preview --from-ci   # https://centrojuanpabloii.com/nuevo/
venv/bin/python scripts/deploy_landing.py --root --from-ci      # reemplaza la landing de la raíz
venv/bin/python scripts/deploy_landing.py --rollback            # vuelve a la landing anterior
```

La landing anterior está respaldada en `backups/landing_legacy_2026-10-10/` (fuera de git). En la raíz el script no
borra archivos, así que el rollback solo restaura su `index.html`.
