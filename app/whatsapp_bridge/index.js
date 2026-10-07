/**
 * Puente de WhatsApp via Baileys.
 *
 * Habla con Python por stdin/stdout: una linea JSON entra, una linea JSON sale.
 * stdout es solo para este protocolo, los logs van a stderr.
 *
 * Lo que cambia respecto a la version anterior:
 *  - Los envios se correlacionan por id, para que Python sepa si el mensaje
 *    salio de verdad. Antes Python asumia exito al escribir y se equivocaba.
 *  - La reconexion espera antes de reintentar y para si WhatsApp ya no
 *    permite la sesion, en vez de quedarse reconectando en bucle.
 *  - Reporta el numero conectado, que es el dato que hace falta para saber
 *    desde que numero sale la comunicacion.
 */
const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');
const fs = require('fs');

const SESSION_DIR = path.join(__dirname, '..', '..', 'whatsapp_sessions');
const RECONNECT_BASE_MS = 5000;
const RECONNECT_MAX_MS = 120000;

const logger = pino({ level: process.env.BRIDGE_LOG_LEVEL || 'warn' }, pino.destination(2));

function send(data) {
  process.stdout.write(JSON.stringify(data) + '\n');
}

let sock = null;
let stopping = false;
let starting = false;
let pending = new Map();
let nextMsgId = 1;
let queue = Promise.resolve();

function jidOf(phone) {
  let digits = String(phone).replace(/\D/g, '');
  if (digits.startsWith('0')) digits = '51' + digits.slice(1);
  if (!digits.startsWith('51')) digits = '51' + digits;
  return `${digits}@s.whatsapp.net`;
}

function settle(msgId, result) {
  const entry = pending.get(msgId);
  if (!entry) return;
  pending.delete(msgId);
  clearTimeout(entry.timer);
  entry.resolve(result);
}

function stopAll(error) {
  for (const [id, entry] of pending) {
    clearTimeout(entry.timer);
    entry.resolve({ ok: false, error: error || 'timeout' });
    pending.delete(id);
  }
}

// WhatsApp esconde el teléfono de algunos contactos tras un identificador @lid. Escribirle al @lid directo se queda colgado
// en esta versión de Baileys, así que primero se busca el teléfono real en la tabla de equivalencias que guarda la sesión.
async function resolvePn(lidUser) {
  const lidJid = `${lidUser}@lid`;
  try {
    const mapping = sock?.signalRepository?.lidMapping;
    if (mapping?.getPNForLID) {
      const pn = await mapping.getPNForLID(lidJid);
      if (pn) return String(pn).split('@')[0].split(':')[0];
    }
  } catch (_) {}
  try {
    const got = await sock?.authState?.keys?.get('lid-mapping', [`${lidUser}_reverse`]);
    const pn = got && got[`${lidUser}_reverse`];
    if (pn) return String(pn).split('@')[0].split(':')[0];
  } catch (_) {}
  return null;
}

async function sendMessage(phone, text, lid = false) {
  if (!sock) return { ok: false, error: 'no_conectado' };

  const msgId = String(nextMsgId++);
  // Los contactos con identificador @lid no tienen teléfono visible: se les escribe a su propio jid.
  let jid;
  if (lid) {
    const lidUser = String(phone).replace(/\D/g, '');
    const pn = await resolvePn(lidUser);
    jid = pn ? `${pn}@s.whatsapp.net` : `${lidUser}@lid`;
  } else jid = jidOf(phone);

  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      settle(msgId, { ok: false, error: 'timeout' });
    }, 30000);
    pending.set(msgId, { resolve, timer });

    queue = queue
      .then(() =>
        sock.sendMessage(jid, { text }, { messageId: msgId })
      )
      .then((info) => {
        settle(msgId, {
          ok: true,
          provider_message_id: info?.key?.id || null,
          jid: jid,
        });
      })
      .catch((err) => {
        const code = err?.output?.statusCode;
        settle(msgId, { ok: false, error: code ? `wa_${code}` : (err?.message || 'error') });
      });
  });
}

async function start() {
  if (starting) return;
  if (stopping) return;
  starting = true;

  // Se cierra y desengancha el socket anterior. Si no, sus listeners siguen
  // vivos y Python recibe 'disconnected' del socket viejo mientras el nuevo
  // esta conectado: por eso el estado quedaba en false.
  if (sock) {
    try { sock.ev.removeAllListeners(); } catch (_) {}
    try { if (sock.ws) sock.ws.close(); } catch (_) {}
    try { if (sock.end) sock.end(); } catch (_) {}
    sock = null;
  }

  try {
  fs.mkdirSync(SESSION_DIR, { recursive: true });
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger,
    browser: ['Moscowle', 'Chrome', '1.0'],
    connectTimeoutMs: 60000,
    keepAliveIntervalMs: 25000,
  });

  sock.ev.on('creds.update', saveCreds);

  // Mensajes entrantes (solo chats individuales): se reenvían al backend para el buzón del panel.
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    // Diagnóstico: cada evento de mensajes queda en el journal (stderr) con el tipo de identificador, sin el contenido.
    for (const m of messages || []) {
      console.error(`[wa-upsert] type=${type} fromMe=${Boolean(m.key?.fromMe)} jid=${String(m.key?.remoteJid || '').replace(/^\d+/, '#')} alt=${m.key?.remoteJidAlt ? 'si' : 'no'}`);
      break;
    }
    if (type !== 'notify') return;
    for (const m of messages || []) {
      try {
        const jid = m.key?.remoteJid || '';
        if (m.key?.fromMe) continue;
        // Chats individuales: con teléfono (@s.whatsapp.net) o con identificador @lid (WhatsApp lo usa para ocultar el número).
        // Si un @lid trae el teléfono real en remoteJidAlt/senderPn, se usa ese. Grupos y estados se ignoran.
        const alt = m.key?.remoteJidAlt || m.key?.senderPn || '';
        const phoneJid = jid.endsWith('@s.whatsapp.net') ? jid : alt.endsWith('@s.whatsapp.net') ? alt : null;
        let resolved = phoneJid;
        if (!resolved && jid.endsWith('@lid')) {
          const pn = await resolvePn(jid.split('@')[0].split(':')[0]);
          if (pn) resolved = `${pn}@s.whatsapp.net`;
        }
        const isLid = !resolved && jid.endsWith('@lid');
        if (!resolved && !isLid) continue;
        const body = m.message || {};
        let text = body.conversation || body.extendedTextMessage?.text || body.imageMessage?.caption || '';
        let kind = 'text';
        if (body.audioMessage) { kind = 'voice'; text = text || '🎤 Nota de voz'; }
        else if (body.imageMessage) { kind = 'image'; text = text ? `🖼️ ${text}` : '🖼️ Imagen'; }
        else if (!text) continue; // reacciones, stickers, etc.
        send({
          type: 'incoming',
          phone: (resolved || jid).split('@')[0].split(':')[0],
          lid: isLid,
          name: m.pushName || null,
          id: m.key?.id || null,
          kind,
          text,
          ts: Number(m.messageTimestamp) || null,
        });
      } catch (_) {}
    }
  });
  } finally {
    starting = false;
  }

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      send({ type: 'qr', qr });
    }

    if (connection === 'open') {
      let me = null;
      try {
        me = sock.user?.id || null;
      } catch (_) {
        me = null;
      }
      send({ type: 'ready', jid: me, phone: me ? me.split('@')[0] : null });
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      const banned = statusCode === DisconnectReason.forbidden;

      // Sin esto no se ve nunca el motivo: statusCode viene vacio en muchos
      // errores de Baileys y quedaba un reason=None inutil para diagnosticar.
      // err.data.stack apunta a quien llamo a promiseTimeout: es el unico
      // lugar que dice si colgo sendRawMessage, awaitNextMessage o el query.
      const err = lastDisconnect?.error;
      const errName = err?.name || err?.constructor?.name || 'desconocido';
      const errMsg = (err?.message || String(err || '')).slice(0, 400);
      const where = String(err?.data?.stack || '').split('\n').slice(0, 8).join(' | ');
      logger.warn(
        { statusCode, errName, loggedOut, banned, caller: where },
        'connection close: %s %s',
        errName,
        errMsg
      );

      stopAll('desconectado');
      // Se suelta el socket caido. Dejarlo referenciado hacia que sendMessage
      // intente usarlo y fallara tarde, y start() lo reemplazaria igual.
      try { sock.ev.removeAllListeners(); } catch (_) {}
      sock = null;
      send({ type: 'disconnected', reason: statusCode || null, logged_out: loggedOut, banned });

      if (stopping) return;

      if (loggedOut || banned) {
        // Ya no hay sesion que reconectar. Reconectar en bucle aqui produce
        // miles de intentos y no recupera nada: hay que volver a escanear QR
        // a proposito. Si es un baneo, avisamos y paramos.
        if (loggedOut) {
          try {
            fs.rmSync(SESSION_DIR, { recursive: true, force: true });
          } catch (_) {}
        }
        send({ type: 'needs_qr', banned });
        return;
      }

      const delay = Math.min(RECONNECT_BASE_MS * (pending.size + 1), RECONNECT_MAX_MS);
      send({ type: 'reconnecting', in_ms: RECONNECT_BASE_MS });
      setTimeout(() => {
        if (!stopping) start().catch((err) => send({ type: 'error', message: err.message }));
      }, RECONNECT_BASE_MS);
    }
  });
}

function handleLine(line) {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (err) {
    send({ type: 'error', message: 'json_invalido' });
    return;
  }

  if (msg.type === 'send') {
    sendMessage(msg.phone, msg.message, Boolean(msg.lid)).then((r) => {
      send({ type: 'send_result', ref: msg.ref || null, ...r });
    });
  } else if (msg.type === 'presence') {
    // «escribiendo…» mientras el bot prepara la respuesta (equivalente al «procesando» de Telegram).
    (async () => {
      try {
        const lidUser = String(msg.phone).replace(/\D/g, '');
        const pn = msg.lid ? await resolvePn(lidUser) : null;
        const jid = msg.lid ? (pn ? `${pn}@s.whatsapp.net` : `${lidUser}@lid`) : jidOf(msg.phone);
        await sock?.sendPresenceUpdate(msg.state === 'paused' ? 'paused' : 'composing', jid);
      } catch (_) {}
    })();
  } else if (msg.type === 'ping') {
    send({ type: 'pong', connected: Boolean(sock) });
  } else if (msg.type === 'status') {
    let jid = null;
    try {
      jid = sock?.user?.id || null;
    } catch (_) {}
    send({ type: 'status', connected: Boolean(sock), jid, phone: jid ? jid.split('@')[0] : null });
  } else if (msg.type === 'logout') {
    stopping = true;
    try {
      fs.rmSync(SESSION_DIR, { recursive: true, force: true });
    } catch (_) {}
    send({ type: 'logged_out' });
    process.exit(0);
  }
}

let buffer = '';
process.stdin.on('data', (chunk) => {
  buffer += chunk.toString();
  let idx;
  while ((idx = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, idx).trim();
    buffer = buffer.slice(idx + 1);
    if (line) handleLine(line);
  }
});

process.on('SIGTERM', () => {
  stopping = true;
  try {
    sock?.end?.(undefined);
  } catch (_) {}
  process.exit(0);
});

start().catch((err) => {
  send({ type: 'fatal', message: err.message });
  process.exit(1);
});
