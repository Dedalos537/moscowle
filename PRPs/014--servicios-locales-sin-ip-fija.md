# PRP: Cockpit, Grafana, impresora y escáner sin depender de la IP

> **Version:** 1.0
> **Created:** 2026-10-22
> **Status:** Implementado (2026-10-22), fases A–D. En el host falta correr `setup_scanner.sh` una vez.
> **Decisiones:** (1) el aviso «la impresora cambió de IP» llega a **todos los admins**; (2) también Prometheus y el frontend LAN (`/app/`). Prometheus no se publica en la LAN porque no tiene login: su botón abre el explorador de Grafana.
> **Restricción:** **no se puede reservar IP en el router** (por seguridad). La IP del servidor y la de la Epson van a seguir cambiando por DHCP. El sistema tiene que encontrarlas solo.

---

## Goal

- Cada botón lleva **siempre** a donde está el servicio **ahora**, aunque la IP haya cambiado.
  - En Monitor del servidor: «Abrir Cockpit» y «Abrir Grafana».
  - En el Drive: «Reconectar impresora» y el escáner.
- La impresora y el escáner son **el mismo dispositivo** (Epson L4150): una sola identidad, un solo descubrimiento, y los dos usan el resultado.
- Sin IP escrita a mano en ningún lado (`.env`, código, CUPS ni SANE).

## Why

Esta semana el router cambió la IP del servidor dos veces (.41 → .249 → .6) y la Epson se perdió. Lo que se rompió:

| Qué | Dónde estaba la IP fija | Síntoma |
|---|---|---|
| Cockpit | `COCKPIT_URL = https://192.168.1.249:9090` (config.py / `.env`) | `ERR_ADDRESS_UNREACHABLE` |
| Grafana | `GRAFANA_URL` en `.env` | lo mismo |
| Impresora | CUPS con `socket://192.168.1.233:9100` | trabajos «Enviado» que nunca salen, cola «Lista» |
| Escáner | SANE con la IP que encontró la última vez (caché 10 min) | «no encuentra el escáner» |

Lo que **sí** sirve y no cambia:

- **El nombre del servidor en la red: `moscowle.local`.** Avahi ya lo anuncia por mDNS. Lo probamos el 22-oct: `https://moscowle.local:9090` (Cockpit) y `http://moscowle.local:3000` (Grafana) responden 200 desde la Mac.
- **El puente interno `virbr0` (192.168.122.1).** No depende del router. Desde VM-APP siempre se llega al host por ahí, y ahí vive `moscowle-scand`.
- **La MAC de cada equipo.** El servidor es `d8:cb:8a:22:46:ef`; la Epson se registra la primera vez que se encuentre. La MAC no cambia aunque cambie la IP.
- **El nombre mDNS de la Epson.** Se anuncia como `EPSONxxxxxx.local` / «EPSON L4150 Series» (`_ipp._tcp`, `_pdl-datastream._tcp`, `_uscan._tcp`).

## What

### 1. «Dónde estás»: el host responde su ubicación actual

Nuevo endpoint en `moscowle-scand` (host, `192.168.122.1:8631`, con su token):

```
GET /where → {
  "host": { "lan_ip": "192.168.1.6", "mdns": "moscowle.local", "mac": "d8:cb:8a:22:46:ef" },
  "services": {
    "cockpit": { "port": 9090, "scheme": "https", "up": true },
    "grafana": { "port": 3000, "scheme": "http",  "up": true }
  },
  "epson": { "ip": "192.168.1.40", "mac": "64:eb:8c:…", "mdns": "EPSON1A2B3C.local", "print": true, "scan": true }
}
```

- La IP del host sale de la interfaz con la ruta por defecto, sin preguntarle al router.
- `up` se comprueba conectando al puerto en el momento.
- La Epson sale del descubrimiento del punto 3.
- Es solo lectura, sin comandos libres, como el resto del daemon.

### 2. Botones que redirigen a la ubicación actual

Backend: `GET /admin/api/infra/open/<servicio>` (`cockpit` | `grafana`), solo admin:

1. Pide `/where` al host. Lo guarda en caché 30 s.
2. Responde **302** a la URL actual: `https://<lan_ip>:9090/`.
3. Si el host no responde, cae a `https://moscowle.local:9090/`.

El botón del frontend apunta a ese endpoint con `target="_blank"`, en vez de a una URL fija. Se borran `COCKPIT_URL` y `GRAFANA_URL` del código y del `.env`; quedan solo como anulación opcional.

Por qué los dos caminos, IP y `.local`:

- `moscowle.local` funciona en Mac, iPhone, Windows 10+ y Linux.
- En **Android**, Chrome no siempre resuelve `.local`. Por eso el botón usa la IP que da el host, y el nombre queda como respaldo y para escribirlo a mano.

En el Monitor también se muestra la dirección: «Cockpit: https://192.168.1.6:9090 · también moscowle.local». Así se puede copiar.

### 3. Impresora y escáner: un solo dispositivo, encontrado por quién es

`moscowle-scand` mantiene **una identidad de la Epson** en `/var/lib/moscowle-scand/epson.json` (MAC + nombre mDNS + última IP). Para encontrarla usa, en orden:

1. **mDNS** (`avahi-browse -rpt _ipp._tcp` / `_uscan._tcp`): toma el anuncio cuyo nombre contenga «EPSON L4150». Es inmediato y da la IP actual.
2. **MAC**: barrido rápido de la LAN, ya hecho en PR #84 (~3 s). Después, `ip neigh` para quedarse con la IP cuya MAC coincide con la guardada.
3. **Huella**: puerto 9100 abierto y página web con «EPSON». Es el método actual, para la primera vez, cuando aún no hay MAC guardada.

Con la IP encontrada, la **misma** actualiza:

- **Impresión:** CUPS pasa a usar la URI por **nombre**, `ipp://EPSONxxxxxx.local:631/ipp/print`, en vez de una IP. CUPS la resuelve en cada trabajo, así que un cambio de IP ya no rompe la cola. Si `.local` falla en el host, se repunta a `socket://<ip>:9100` (como hoy).
- **Escaneo:** el daemon le pasa a SANE el dispositivo `airscan:e0:EPSON L4150` / `epsonds:net:<ip>` de la misma identidad. La caché de dispositivos se invalida cuando cambia la IP, así que no vuelve a buscar por su lado.

El **vigilante** (cada 10 min, más cada trabajo que falle) repite el descubrimiento si la Epson no responde. Si la encuentra en otra IP, actualiza CUPS y el escáner solo y avisa en la campana: «La impresora cambió de IP (.233 → .40): ya está reconectada».

El botón **Reconectar impresora** del Drive pasa a ser «Reconectar impresora y escáner» y hace lo mismo a demanda.

### 4. Cuando de verdad no está en la red

Si ninguno de los tres métodos la encuentra, el mensaje lo dice tal cual: «La Epson no está en el WiFi del centro». El aviso tiene los pasos para reconectarla (botón Wi-Fi o hoja de estado de red) y no se queda esperando. En la campana sale **un solo aviso**, no uno por revisión.

### 5. La app Android

La app bloquea dominios fuera de Moscowle, así que las direcciones de la LAN (`192.168.x.x`, `*.local`) se abren en el **navegador del teléfono** con un Intent, no dentro de la app. Cockpit y Grafana tienen su propio inicio de sesión.

## Fuera de alcance / descartado

- **Reservar IP en el router**: no se puede, por política.
- **Publicar Cockpit o Grafana por el túnel de Cloudflare**: Cockpit da control total del servidor. Sigue siendo solo LAN; ya se había decidido no exponer una terminal web.
- **DNS propio en la LAN (dnsmasq)**: haría falta que el router lo entregue por DHCP. Es el mismo problema.

## Success Criteria

- [ ] Cambiar la IP del host (renovar DHCP) no rompe los botones: «Abrir Cockpit» y «Abrir Grafana» llevan a la IP nueva sin tocar `.env`.
- [ ] Cambiar la IP de la Epson: el siguiente trabajo de impresión sale (URI por nombre) y el siguiente escaneo funciona sin pulsar nada; si hizo falta repuntar, hay un aviso en la campana.
- [ ] «Reconectar impresora y escáner» responde en menos de 15 s, con éxito o con el motivo real.
- [ ] No queda ninguna IP de la LAN escrita en `config.py`, `.env.example` ni en CUPS.
- [ ] Tests:
  - redirección con el host caído (fallback `.local`);
  - identidad de la Epson: misma MAC con otra IP → actualiza;
  - otra Epson en la red no se confunde si la MAC no coincide;
  - el vigilante no avisa dos veces por el mismo cambio.

## Implementation Blueprint

1. **Fase A: `/where` + redirección.**
   - Endpoint `/where` en el daemon.
   - `GET /admin/api/infra/open/<servicio>`.
   - Botones del Monitor apuntando al endpoint.
   - Se retiran `COCKPIT_URL` y `GRAFANA_URL`.
   - **Cockpit y Grafana quedan resueltos aquí.**
2. **Fase B: identidad de la Epson.** `epson.json`, descubrimiento mDNS → MAC → huella, y `/where` incluye la Epson.
3. **Fase C: CUPS y SANE desde la identidad.**
   - URI de CUPS por nombre mDNS, con respaldo por IP.
   - Escáner con el mismo dispositivo.
   - Vigilante que avisa una vez.
   - Botón «Reconectar impresora y escáner».
4. **Fase D: instalación.**
   - `setup_scanner.sh` instala `avahi-utils` si falta y migra la cola de CUPS a la URI por nombre.
   - En el host solo hay que correrlo una vez más.

## Notas de implementación

- **Sin redirección 302.** Un enlace que se abre en una pestaña nueva no lleva el token de la sesión. Por eso el Monitor recibe en `links` las direcciones resueltas (se refrescan cada 10 s) y muestra la dirección en texto.
- **CUPS apunta por nombre con `socket://EPSONxxxx.local:9100`.** No usa `ipp://`, para mantener el mismo driver y formato que hoy.
- **El aviso de «no está en la red» sale una vez**, y se rearma cuando la Epson vuelve.
