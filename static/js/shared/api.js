/**
 * Centralized API client enforcing cookie sessions and CSRF protection.
 */
import './session.js';
import { showToast } from './ui.js';

export async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  let body = options.body;
  if (method !== 'GET') {
    headers['X-SiteIQ-CSRF'] = '1';
    if (body && !(body instanceof FormData) && typeof body === 'object') {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }
  }

  const fetchOptions = {
    ...options,
    method,
    headers,
    body,
    credentials: 'same-origin'
  };

  let res;
  try {
    res = await fetch(path, fetchOptions);
  } catch (netErr) {
    showToast(netErr.message || 'Network connection failed', 'error');
    throw netErr;
  }

  if (res.status === 401) {
    const currentPath = window.location.pathname + window.location.search;
    if (!window.location.pathname.startsWith('/login') && window.location.pathname !== '/') {
      window.location.href = `/login?next=${encodeURIComponent(currentPath)}`;
    }
    const err = new Error('Unauthorized');
    err.status = 401;
    throw err;
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || data.message || detail;
    } catch (_) {}

    showToast(detail, 'error');
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) {
    return null;
  }

  return await res.json();
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  put: (path, body, opts) => request(path, { ...opts, method: 'PUT', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  delete: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
};
