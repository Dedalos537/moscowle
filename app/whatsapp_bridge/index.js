const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');
const fs = require('fs');

const SESSION_DIR = path.join(__dirname, '..', '..', 'whatsapp_sessions');

function sendJSON(data) {
  process.stdout.write(JSON.stringify(data) + '\n');
}

async function startBot() {
  if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  }

  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
    browser: ['Moscowle Bot', 'Chrome', '1.0'],
  });

  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      sendJSON({ type: 'qr', qr });
    }
    if (connection === 'open') {
      sendJSON({ type: 'ready' });
    }
    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      sendJSON({ type: 'disconnected', reason });
      if (reason === DisconnectReason.loggedOut) {
        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
      }
      startBot();
    }
  });

  sock.ev.on('creds.update', saveCreds);

  process.stdin.on('data', async (data) => {
    try {
      const msg = JSON.parse(data.toString().trim());
      if (msg.type === 'send') {
        const phone = msg.phone.replace(/\D/g, '');
        const jid = `${phone}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: msg.message });
        sendJSON({ type: 'sent', phone: msg.phone });
      }
    } catch (e) {
      sendJSON({ type: 'error', message: e.message });
    }
  });
}

startBot().catch((err) => {
  sendJSON({ type: 'error', message: err.message });
  process.exit(1);
});
