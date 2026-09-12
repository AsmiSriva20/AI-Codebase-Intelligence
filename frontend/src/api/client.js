export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

export function apiFetch(path, options) {
  return fetch(apiUrl(path), options);
}

export function wsUrl(path) {
  const url = new URL(apiUrl(path), window.location.origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}
