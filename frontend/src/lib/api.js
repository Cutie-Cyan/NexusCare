import { supabase } from './supabase.js'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

export async function apiRequest(path, options = {}) {
  if (!supabase) {
    throw new Error('Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in frontend/.env.local.')
  }

  const { data, error } = await supabase.auth.getSession()
  if (error) throw new Error(error.message)
  const token = data.session?.access_token
  if (!token) throw new Error('Your session has expired. Please sign in again.')

  const response = await fetch(API_BASE_URL + (path.startsWith('/') ? path : '/' + path), {
    ...options,
    headers: {
      Accept: 'application/json',
      Authorization: 'Bearer ' + token,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  if (response.status === 204) return null
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
    throw new Error(typeof detail === 'string' ? detail : 'Request failed with status ' + response.status + '.')
  }
  return payload
}
