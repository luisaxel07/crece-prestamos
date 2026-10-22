export class AuthError extends Error {
  constructor(message, status = 0) { super(message); this.name = 'AuthError'; this.status = status; }
}
async function request(path, { method = 'GET', body } = {}) {
  const config = window.CRECE_AUTH;
  if (!config?.baseUrl) throw new AuthError('Esta vista aún no está conectada al servidor. Abre el portal web o configura la API para continuar.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(`${config.baseUrl.replace(/\/$/, '')}/${path}`, {
      method, credentials: 'include', signal: controller.signal,
      headers: { 'Accept': 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), 'X-CSRF-Token': config.csrfToken || '' },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    if (!response.headers.get('content-type')?.includes('application/json')) throw new AuthError('El servidor devolvió una respuesta no válida. Intenta más tarde.', response.status);
    let data;
    try { data = await response.json(); } catch { throw new AuthError('La respuesta del servidor está incompleta.', response.status); }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new AuthError('La respuesta del servidor no es válida.', response.status);
    if (!response.ok) throw new AuthError(data.message || 'No se pudo completar la solicitud.', response.status);
    return data;
  } catch (error) {
    if (error instanceof AuthError) throw error;
    throw new AuthError(error.name === 'AbortError' ? 'El servidor tardó demasiado. Intenta nuevamente.' : 'No se pudo conectar al servidor. Revisa tu conexión.');
  } finally { clearTimeout(timeout); }
}
export const auth = {
  login: data => request('login', { method: 'POST', body: data }),
  register: data => request('register', { method: 'POST', body: data }),
  recover: data => request('recover', { method: 'POST', body: data }),
  session: async () => {
    const result = await request('session');
    if (typeof result.csrfToken === 'string') window.CRECE_AUTH.csrfToken = result.csrfToken;
    return result;
  },
  logout: () => request('logout', { method: 'POST', body: {} })
};
