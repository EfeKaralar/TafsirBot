const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

function buildUrl(path) {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
  return `${baseUrl}${path}`;
}

async function request(path, options = {}) {
  const response = await fetch(buildUrl(path), {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the fallback message if the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json();
}

export function getHealth() {
  return request('/health', { headers: {} });
}

export function sendWebhook(payload) {
  return request('/api/webhook', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listSessions() {
  return request('/api/sessions');
}

export function getSession(sessionId) {
  return request(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export function listTestRuns() {
  return request('/api/test-runs');
}

export function getTestRun(runId) {
  return request(`/api/test-runs/${encodeURIComponent(runId)}`);
}
