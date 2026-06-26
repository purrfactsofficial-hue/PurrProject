const BASE = '/api'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body != null ? { 'Content-Type': 'application/json' } : {},
    body: body != null ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok && res.status !== 422) throw Object.assign(new Error(`${res.status} ${res.statusText}`), { data })
  return data
}

export function scanVideos() {
  return request('/videos/scan')
}

export function listVideos({ status, page = 1, perPage = 12 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  return request(`/videos/list?${params}`)
}

export function getVideo(id) {
  return request(`/videos/${id}`)
}

export function importCaptions(videoId, force = false) {
  return post(`/captions/import/${videoId}?force=${force}`)
}

export function getCaptions(videoId) {
  return request(`/captions/${videoId}`)
}

export function saveCaption({ videoId, language, platform, title = null, caption, hashtags }) {
  return post('/captions/save', { video_id: videoId, language, platform, title, caption, hashtags })
}
