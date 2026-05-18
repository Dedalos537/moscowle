// Minimal robust API wrapper for frontend
export async function apiFetch(url, opts = {}) {
  opts = Object.assign({}, opts);
  opts.credentials = opts.credentials || 'same-origin';
  opts.headers = Object.assign({'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}, opts.headers || {});

  // Inject CSRF token if present in a meta tag
  const csrfMeta = document.querySelector("meta[name='csrf-token']");
  if (csrfMeta && !opts.headers['X-CSRFToken']) {
    opts.headers['X-CSRFToken'] = csrfMeta.content;
  }

  const res = await fetch(url, opts);
  const ct = (res.headers.get('content-type') || '').toLowerCase();

  // Handle authentication redirects / unauthorized
  if (res.status === 401 || res.status === 403) {
    // For API calls, prefer redirecting to login preserving next param
    const next = encodeURIComponent(location.pathname + location.search);
    // If running inside an iframe or XHR caller, we just throw an object
    if (opts.headers['X-Requested-With'] === 'XMLHttpRequest' || ct.includes('application/json')) {
      throw { error: 'Unauthorized', status: res.status };
    }
    window.location.href = '/login?next=' + next;
    throw { error: 'Redirecting to login', status: res.status };
  }

  // Prefer JSON responses
  if (ct.includes('application/json')) {
    const payload = await res.json();
    
    // If the backend uses the API wrapper {success,data,error,status}
    if (payload && typeof payload.success !== 'undefined') {
      if (!payload.success) {
        throw { 
          error: payload.error || payload.message || 'Error al procesar solicitud', 
          status: payload.status || res.status, 
          raw: payload 
        };
      }
      // ✅ FIXED: Return payload.data if it exists, otherwise return entire payload
      // This handles both: {success: true, data: {...}} and {success: true, message: "..."}
      return payload.data !== undefined ? payload.data : payload;
    }
    // Backwards compatibility: return payload as-is
    return payload;
  }

  // Unexpected HTML response — likely a redirect to login or an error page
  const text = await res.text();
  console.error('apiFetch received non-JSON response for', url, 'status', res.status);
  // If it looks like a login page, redirect
  if (/\<form[^>]+login/i.test(text) || /name="password"/.test(text)) {
    const next = encodeURIComponent(location.pathname + location.search);
    window.location.href = '/login?next=' + next;
    throw { error: 'Redirecting to login (HTML returned)', status: res.status };
  }

  throw { error: 'Unexpected non-JSON response', status: res.status, raw: text };
}

// Helper to wrap calls and always return a predictable shape for callers that prefer it
export async function safeApiFetch(url, opts = {}) {
  try {
    const data = await apiFetch(url, opts);
    return { success: true, data };
  } catch (err) {
    return { success: false, error: err.error || err.message || 'Unknown error', status: err.status || 500, raw: err.raw };
  }
}
