const BASE = '/api'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body, { allow422 = false } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body != null ? { 'Content-Type': 'application/json' } : {},
    body: body != null ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok && !(allow422 && res.status === 422))
    throw Object.assign(new Error(`${res.status} ${res.statusText}`), { data })
  return data
}

async function patch(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(`${res.status} ${res.statusText}`), { data })
  return data
}

async function del(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(`${res.status} ${res.statusText}`), { data })
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
  return post(`/captions/import/${videoId}?force=${force}`, undefined, { allow422: true })
}

export function getCaptions(videoId) {
  return request(`/captions/${videoId}`)
}

export function saveCaption({ videoId, language, platform, title = null, caption, hashtags }) {
  return post('/captions/save', { video_id: videoId, language, platform, title, caption, hashtags })
}

export function getSlots(episodeId, date) {
  return request(`/schedule/slots?episode_id=${episodeId}&date=${date}`)
}

export function createSchedule(episodeId, postDate, languages, platforms) {
  return post('/schedule/create', {
    episode_id: episodeId,
    date: postDate,
    languages,
    platforms,
  })
}

export function getQueue() {
  return request('/schedule/queue')
}

export function cancelPost(postId) {
  return del(`/schedule/${postId}`)
}

export function reschedulePost(postId, date) {
  return patch(`/schedule/${postId}`, { date })
}

export function rescheduleEpisode(episodeId, date) {
  return patch(`/schedule/episode/${episodeId}`, { date })
}

export function retryPost(postId) {
  return post(`/schedule/${postId}/retry`)
}

export function publishNow(postId) {
  return post(`/schedule/${postId}/publish`)
}
