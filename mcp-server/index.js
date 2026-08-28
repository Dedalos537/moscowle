#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const API_BASE = process.env.MOSCOWLE_API_URL || 'https://api-centrojuanpabloii.online';
let AUTH_TOKEN = process.env.MOSCOWLE_API_TOKEN || '';

async function api(path, params = {}) {
  const url = new URL(path, API_BASE);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  });
  const headers = { 'Content-Type': 'application/json' };
  if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  const res = await fetch(url.toString(), { headers });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

async function apiPost(path, body = {}) {
  const url = new URL(path, API_BASE);
  const headers = { 'Content-Type': 'application/json' };
  if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  const res = await fetch(url.toString(), { method: 'POST', headers, body: JSON.stringify(body) });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

const server = new McpServer({ name: 'moscowle', version: '1.0.0' });

// ─── Auth ───────────────────────────────────────────────────────────
server.tool('login', 'Iniciar sesión en Moscowle. Ejecutar primero.', {
  email: z.string().describe('Email'),
  password: z.string().describe('Contraseña'),
}, async ({ email, password }) => {
  const data = await apiPost('/api/login', { email, password });
  if (data.access_token) {
    AUTH_TOKEN = data.access_token;
    return { content: [{ type: 'text', text: `✅ Sesión iniciada como ${data.user?.username || email}` }] };
  }
  return { content: [{ type: 'text', text: `❌ ${data.error || 'Error'}` }] };
});

// ─── Dashboard ──────────────────────────────────────────────────────
server.tool('get_dashboard', 'Obtener dashboard principal con estadísticas del centro.', {}, async () => {
  const data = await api('/admin/dashboard');
  return { content: [{ type: 'text', text: typeof data === 'string' ? data : JSON.stringify(data, null, 2) }] };
});

server.tool('get_overview', 'Obtener resumen general del centro (pacientes activos, sesiones, etc).', {}, async () => {
  const data = await api('/admin/api/overview');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Pacientes ──────────────────────────────────────────────────────
server.tool('get_patients', 'Obtener lista de pacientes.', {
  search: z.string().optional().describe('Buscar por nombre'),
}, async ({ search }) => {
  const data = await api('/api/patients', { search });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_patient_detail', 'Obtener detalle de un paciente.', {
  patient_id: z.number().describe('ID del paciente'),
}, async ({ patient_id }) => {
  const data = await api(`/api/admin/patient/${patient_id}/detail`);
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Usuarios / Terapeutas ──────────────────────────────────────────
server.tool('get_users', 'Obtener lista de todos los usuarios (terapeutas, pacientes, admins).', {
  role: z.string().optional().describe('Filtrar por rol: admin, supervisor, terapista, jugador'),
}, async ({ role }) => {
  const data = await api('/api/admin/list-users', { role });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_therapist_efficiency', 'Obtener eficiencia de terapeutas (sesiones completadas, etc).', {}, async () => {
  const data = await api('/api/therapist/efficiency');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_therapist_financials', 'Obtener datos financieros por terapeuta.', {}, async () => {
  const data = await api('/admin/api/therapist-financials');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Sesiones ───────────────────────────────────────────────────────
server.tool('get_sessions', 'Obtener sesiones/terapias.', {
  patient_id: z.number().optional().describe('Filtrar por paciente'),
  status: z.string().optional().describe('Estado: pending, in_progress, completed, cancelled'),
}, async ({ patient_id, status }) => {
  const data = await api('/api/sessions', { patient_id, status });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_session', 'Obtener detalle de una sesión.', {
  session_id: z.number().describe('ID de la sesión'),
}, async ({ session_id }) => {
  const data = await api(`/api/sessions/${session_id}`);
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_upcoming_sessions', 'Obtener sesiones próximas.', {}, async () => {
  const data = await api('/api/sessions/upcoming');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Pagos / Finanzas ───────────────────────────────────────────────
server.tool('get_financial_summary', 'Obtener resumen financiero del centro (ingresos, egresos, balance).', {
  period: z.string().optional().describe('Período: month, quarter, year'),
}, async ({ period }) => {
  const data = await api('/admin/api/financial-summary', { period });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_payments', 'Obtener lista de pagos registrados.', {}, async () => {
  const data = await api('/admin/api/payments/all');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_expenses', 'Obtener egresos/gastos del centro.', {}, async () => {
  const data = await api('/admin/api/expenses');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_deudores', 'Obtener lista de deudores (pacientes con pagos pendientes).', {}, async () => {
  const data = await api('/api/admin/deudores');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Contratos ──────────────────────────────────────────────────────
server.tool('get_contracts', 'Obtener contratos del centro.', {
  status: z.string().optional().describe('Estado: active, completed, cancelled'),
}, async ({ status }) => {
  const data = await api('/admin/api/contracts', { status });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Notificaciones ─────────────────────────────────────────────────
server.tool('get_notifications', 'Obtener notificaciones agrupadas.', {
  category: z.string().optional().describe('Categoría: message, session, payment, alert, system'),
}, async ({ category }) => {
  const data = await api('/api/notifications/groups', { category });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_notification_count', 'Obtener cantidad de notificaciones no leídas.', {}, async () => {
  const data = await api('/api/notifications/count');
  return { content: [{ type: 'text', text: `No leídas: ${data.count}` }] };
});

// ─── Reportes ───────────────────────────────────────────────────────
server.tool('get_reports_weekly', 'Obtener reportes semanales.', {}, async () => {
  const data = await api('/api/daily-reports');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_reports_monthly', 'Obtener reportes mensuales.', {}, async () => {
  const data = await api('/api/reports/monthly');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_audit_stats', 'Obtener estadísticas de auditoría.', {}, async () => {
  const data = await api('/admin/api/audit-stats');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Incidentes ─────────────────────────────────────────────────────
server.tool('get_incidents', 'Obtener incidentes/accidentes reportados.', {
  status: z.string().optional().describe('Estado: open, in_progress, resolved, closed'),
}, async ({ status }) => {
  const data = await api('/api/incidents', { status });
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_incidents_dashboard', 'Obtener dashboard de incidentes con métricas.', {}, async () => {
  const data = await api('/api/incidents/dashboard');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Juegos ─────────────────────────────────────────────────────────
server.tool('get_games', 'Obtener juegos/actividades del centro.', {}, async () => {
  const data = await api('/api/games');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Sedes ──────────────────────────────────────────────────────────
server.tool('get_sedes', 'Obtener sedes del centro.', {}, async () => {
  const data = await api('/api/admin/sedes');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

server.tool('get_sede_stats', 'Obtener estadísticas por sede.', {}, async () => {
  const data = await api('/api/admin/sedes/stats');
  return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
});

// ─── Start ──────────────────────────────────────────────────────────
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Moscowle MCP Server running on stdio');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
