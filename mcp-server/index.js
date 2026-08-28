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

// ─── AI Analysis ────────────────────────────────────────────────────
server.tool('get_ai_analysis', 'Análisis de tendencias con IA: finanzas, pacientes, terapeutas.', {
  period: z.string().optional().describe('Período: week, month, quarter, year'),
}, async ({ period }) => {
  const data = await api('/admin/api/financial-summary', { period: period || 'month' });
  const overview = await api('/admin/api/overview');
  const efficiency = await api('/api/therapist/efficiency');

  const prompt = `Eres el analista del Centro Juan Pablo II. Datos:\n\nFINANZAS: ${JSON.stringify(data)}\n\nVISTA GENERAL: ${JSON.stringify(overview)}\n\nEFICIENCIA TERAPEUTAS: ${JSON.stringify(efficiency)}\n\nGenera un análisis en español con:\n1. Tendencias financieras\n2. Rendimiento de pacientes\n3. Eficiencia de terapeutas\n4. Alertas y recomendaciones\n5. Predicciones para el próximo período\nMáximo 15 líneas, tono ejecutivo.`;

  try {
    const llmRes = await fetch(`${API_BASE}/api/ai/gemini`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(AUTH_TOKEN ? { 'Authorization': `Bearer ${AUTH_TOKEN}` } : {}) },
      body: JSON.stringify({ prompt }),
    });
    if (llmRes.ok) {
      const llmData = await llmRes.json();
      return { content: [{ type: 'text', text: `📊 *Análisis AI*\n\n${llmData.response || llmData.answer || JSON.stringify(llmData)}` }] };
    }
  } catch (e) {}

  return { content: [{ type: 'text', text: `Datos sin procesar:\n\nFinanzas: ${JSON.stringify(data, null, 2)}\n\nEficiencia: ${JSON.stringify(efficiency, null, 2)}` }] };
});

server.tool('get_predictions', 'Predicciones de ingresos y pacientes basadas en datos históricos.', {}, async () => {
  const financial = await api('/admin/api/financial-summary', { period: 'month' });
  const overview = await api('/admin/api/overview');
  const deudores = await api('/api/admin/deudores');

  let deudoresCount = 0;
  let deudoresAmount = 0;
  if (deudores && deudores.deudores) {
    deudoresCount = deudores.deudores.length;
    deudoresAmount = deudores.deudores.reduce((sum, d) => sum + (d.total_owed || 0), 0);
  }

  const incomeReal = financial?.data?.income_real || 0;
  const incomeExpected = financial?.data?.income_expected || 0;
  const patients = overview?.data?.patients || 0;

  const now = new Date();
  const dayOfMonth = now.getDate();
  const daysInMonth = 30;
  const projected = dayOfMonth > 0 ? (incomeReal / dayOfMonth) * daysInMonth : 0;

  const text = `🔮 *Predicciones Centro Juan Pablo II*

💰 *Ingresos:*
• Real este mes: S/ ${incomeReal.toFixed(0)}
• Meta: S/ ${incomeExpected.toFixed(0)}
• Cobranza: ${incomeExpected > 0 ? ((incomeReal / incomeExpected) * 100).toFixed(0) : 0}%
• Proyección fin de mes: S/ ${projected.toFixed(0)}

👥 *Pacientes:*
• Activos: ${patients}
• En mora: ${deudoresCount} usuarios
• Monto en mora: S/ ${deudoresAmount.toFixed(0)}

📈 *Tendencias:*
• ${incomeReal > incomeExpected * 0.5 ? '✅ Ingresos van bien' : '⚠️ Ingresos por debajo del esperado'}
• ${deudoresCount < 5 ? '✅ Pocos deudores' : '⚠️ Muchos deudores, revisar cobranza'}

💡 *Recomendación:*
• ${deudoresCount > 0 ? `Contactar a ${deudoresCount} pacientes morosos` : 'No hay mora pendiente'}
• ${projected < incomeExpected ? 'Considerar estrategias de upselling' : 'Mantener ritmo actual'}`;

  return { content: [{ type: 'text', text }] };
});

server.tool('generate_report', 'Generar reporte personalizado con IA.', {
  type: z.string().describe('Tipo: daily, weekly, monthly, annual'),
}, async ({ type }) => {
  const financial = await api('/admin/api/financial-summary', { period: type === 'daily' ? 'week' : type === 'weekly' ? 'week' : type === 'annual' ? 'year' : 'month' });
  const overview = await api('/admin/api/overview');
  const efficiency = await api('/api/therapist/efficiency');

  const prompt = `Genera un reporte ${type} para el Centro Juan Pablo II.\n\nDATOS:\nFinanzas: ${JSON.stringify(financial)}\nOverview: ${JSON.stringify(overview)}\nEficiencia: ${JSON.stringify(efficiency)}\n\nIncluye: BSC scores, análisis financiero, rendimiento, predicciones, recomendaciones. Español, formato ejecutivo, máximo 20 líneas.`;

  try {
    const llmRes = await fetch(`${API_BASE}/api/ai/gemini`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(AUTH_TOKEN ? { 'Authorization': `Bearer ${AUTH_TOKEN}` } : {}) },
      body: JSON.stringify({ prompt }),
    });
    if (llmRes.ok) {
      const llmData = await llmRes.json();
      return { content: [{ type: 'text', text: `📋 *Reporte ${type.toUpperCase()}*\n\n${llmData.response || llmData.answer || JSON.stringify(llmData)}` }] };
    }
  } catch (e) {}

  return { content: [{ type: 'text', text: `Reporte ${type}:\n\nFinanzas: ${JSON.stringify(financial, null, 2)}` }] };
});

server.tool('get_data_export', 'Exportar datos para análisis externo (CSV/JSON).', {
  type: z.string().describe('Tipo de dato: payments, sessions, patients, all'),
  format: z.string().optional().describe('Formato: json (default) o csv'),
}, async ({ type, format }) => {
  let data = {};
  if (type === 'payments' || type === 'all') {
    data.payments = await api('/admin/api/payments/all');
  }
  if (type === 'sessions' || type === 'all') {
    data.sessions = await api('/api/sessions');
  }
  if (type === 'patients' || type === 'all') {
    data.patients = await api('/api/patients');
  }
  if (type === 'all') {
    data.financial = await api('/admin/api/financial-summary');
    data.overview = await api('/admin/api/overview');
  }

  if (format === 'csv') {
    if (data.payments && data.payments.payments) {
      const headers = 'ID,Paciente,Monto,Fecha,Estado,Metodo\n';
      const rows = data.payments.payments.map(p =>
        `${p.id},${p.patient_name || ''},${p.amount},${p.date},${p.status},${p.method || ''}`
      ).join('\n');
      return { content: [{ type: 'text', text: headers + rows }] };
    }
  }

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
