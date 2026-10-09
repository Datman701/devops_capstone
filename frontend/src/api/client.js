const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) return null;

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const error = new Error(
      (payload && payload.detail) || `Request failed with ${response.status}`,
    );
    error.status = response.status;
    error.detail = payload && payload.detail;
    throw error;
  }
  return payload;
}

function toQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value);
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

export const api = {
  health: () => request('/api/health'),

  getStats: (filters) => request(`/api/appointments/stats${toQuery(filters)}`),
  listAppointments: (filters) => request(`/api/appointments${toQuery(filters)}`),
  getAppointment: (id) => request(`/api/appointments/${id}`),
  createAppointment: (body) => request('/api/appointments', { method: 'POST', body }),
  updateAppointment: (id, body) =>
    request(`/api/appointments/${id}`, { method: 'PUT', body }),
  changeStatus: (id, status) =>
    request(`/api/appointments/${id}/status`, { method: 'PATCH', body: { status } }),
  cancelAppointment: (id) =>
    request(`/api/appointments/${id}`, { method: 'DELETE' }),
  availability: (doctorId, day) =>
    request(`/api/appointments/${doctorId}/availability${toQuery({ day })}`),

  listDoctors: () => request('/api/doctors'),
  createDoctor: (body) => request('/api/doctors', { method: 'POST', body }),
  listPatients: () => request('/api/patients'),
  createPatient: (body) => request('/api/patients', { method: 'POST', body }),
};

export default api;