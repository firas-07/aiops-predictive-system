const API_BASE = '/api';

export async function fetchJson(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errData = await response.json();
      errorDetail = errData.detail || JSON.stringify(errData);
    } catch (_) {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: () => fetchJson('/v1/health'),

  // Application Management
  listApplications: () => fetchJson('/applications'),
  getApplication: (appId) => fetchJson(`/applications/${appId}`),
  createApplication: (payload) =>
    fetchJson('/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateApplication: (appId, payload) =>
    fetchJson(`/applications/${appId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteApplication: (appId) =>
    fetchJson(`/applications/${appId}`, {
      method: 'DELETE',
    }),

  // Real-time Application Telemetry
  getApplicationTelemetry: (appId, limit = 75) =>
    fetchJson(`/applications/${appId}/telemetry?limit=${limit}`),
  getLatestTelemetry: (appId) =>
    fetchJson(`/applications/${appId}/telemetry/latest`),

  // Real-time Prediction (Automated telemetry retrieval + 30m forecast + time-to-threshold)
  predictRealtime: (appId, horizonMinutes = 30) =>
    fetchJson(`/applications/${appId}/predict`, {
      method: 'POST',
      body: JSON.stringify({ horizon_minutes: horizonMinutes }),
    }),

  // Threshold Configuration
  getApplicationThresholds: (appId) =>
    fetchJson(`/applications/${appId}/thresholds`),
  updateApplicationThresholds: (appId, thresholds) =>
    fetchJson(`/applications/${appId}/thresholds`, {
      method: 'PUT',
      body: JSON.stringify(thresholds),
    }),

  // Data & Training
  getDataSummary: () => fetchJson('/v1/data/summary'),
  getModels: () => fetchJson('/v1/models'),
  getTrainingStatus: () => fetchJson('/v1/training/status'),
  triggerTraining: (fastMode = false) =>
    fetchJson('/v1/training/train', {
      method: 'POST',
      body: JSON.stringify({ fast_mode: fastMode, forecast_horizon_minutes: 60 }),
    }),
};
