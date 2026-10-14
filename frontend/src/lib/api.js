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

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const requestBody = options.body != null
    && typeof options.body !== 'string'
    && !isFormData
    ? JSON.stringify(options.body)
    : options.body

  const response = await fetch(API_BASE_URL + (path.startsWith('/') ? path : '/' + path), {
    ...options,
    body: requestBody,
    headers: {
      Accept: 'application/json',
      Authorization: 'Bearer ' + token,
      ...(options.body != null && !isFormData ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  if (response.status === 204) return null
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (Array.isArray(detail)) {
      const messages = detail.map(item => {
        const location = Array.isArray(item.loc) ? item.loc.filter(part => part !== 'body').join('.') : ''
        return location ? location + ': ' + item.msg : item.msg
      }).filter(Boolean)
      throw new Error(messages.join('; ') || 'Request failed with status ' + response.status + '.')
    }
    throw new Error('Request failed with status ' + response.status + '.')
  }
  return payload
}
