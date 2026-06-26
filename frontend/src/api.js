const BASE = '/api'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export function scanVideos() {
  return request('/videos/scan')
}

export function listVideos({ status, page = 1, perPage = 12 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  return request(`/videos/list?${params}`)
}
