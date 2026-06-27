import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getCaptions,
  getVideo,
  importCaptions,
  listVideos,
  saveCaption,
  scanVideos,
} from '../api.js'

// Build a minimal fetch mock that returns the given data and ok/status.
function makeFetch(ok, data, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? 'OK' : 'Server Error',
    json: () => Promise.resolve(data),
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

// ─── request() path (GET) ────────────────────────────────────────────────────

describe('scanVideos', () => {
  it('calls GET /api/videos/scan and returns parsed JSON', async () => {
    const data = { scanned: 3 }
    vi.stubGlobal('fetch', makeFetch(true, data))
    const result = await scanVideos()
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith('/api/videos/scan')
  })

  it('throws when response is not ok', async () => {
    vi.stubGlobal('fetch', makeFetch(false, {}, 500))
    await expect(scanVideos()).rejects.toThrow('500')
  })
})

describe('listVideos', () => {
  it('calls GET /api/videos/list with default page=1 per_page=12', async () => {
    const data = { items: [], total: 0, pages: 1 }
    vi.stubGlobal('fetch', makeFetch(true, data))
    const result = await listVideos()
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith('/api/videos/list?page=1&per_page=12')
  })

  it('includes status, page and per_page when provided', async () => {
    vi.stubGlobal('fetch', makeFetch(true, { items: [], total: 0, pages: 1 }))
    await listVideos({ status: 'draft', page: 2, perPage: 6 })
    const url = fetch.mock.calls[0][0]
    expect(url).toContain('status=draft')
    expect(url).toContain('page=2')
    expect(url).toContain('per_page=6')
  })

  it('omits status param when not provided', async () => {
    vi.stubGlobal('fetch', makeFetch(true, { items: [], total: 0, pages: 1 }))
    await listVideos({ page: 1 })
    expect(fetch.mock.calls[0][0]).not.toContain('status=')
  })
})

describe('getVideo', () => {
  it('calls GET /api/videos/:id', async () => {
    const data = { id: 1, name: 'Pizza' }
    vi.stubGlobal('fetch', makeFetch(true, data))
    const result = await getVideo(1)
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith('/api/videos/1')
  })

  it('throws on non-ok response', async () => {
    vi.stubGlobal('fetch', makeFetch(false, {}, 404))
    await expect(getVideo(99)).rejects.toThrow('404')
  })
})

// ─── post() path ─────────────────────────────────────────────────────────────

describe('importCaptions', () => {
  it('calls POST /api/captions/import/:id with force=false by default', async () => {
    const data = { imported: 12 }
    vi.stubGlobal('fetch', makeFetch(true, data))
    const result = await importCaptions(1)
    expect(result).toEqual(data)
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toBe('/api/captions/import/1?force=false')
    expect(opts.method).toBe('POST')
  })

  it('calls POST with force=true when requested', async () => {
    vi.stubGlobal('fetch', makeFetch(true, { imported: 12 }))
    await importCaptions(1, true)
    expect(fetch.mock.calls[0][0]).toBe('/api/captions/import/1?force=true')
  })

  it('returns data even on 422 (allow422=true)', async () => {
    const data = { detail: 'already imported' }
    vi.stubGlobal('fetch', makeFetch(false, data, 422))
    const result = await importCaptions(1)
    expect(result).toEqual(data)
  })

  it('throws on non-ok non-422 response', async () => {
    vi.stubGlobal('fetch', makeFetch(false, {}, 500))
    await expect(importCaptions(1)).rejects.toThrow('500')
  })
})

describe('getCaptions', () => {
  it('calls GET /api/captions/:id', async () => {
    const data = [{ id: 1, language: 'en' }]
    vi.stubGlobal('fetch', makeFetch(true, data))
    const result = await getCaptions(1)
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith('/api/captions/1')
  })
})

describe('saveCaption', () => {
  it('calls POST /api/captions/save with correct JSON body', async () => {
    const responseData = { ok: true }
    vi.stubGlobal('fetch', makeFetch(true, responseData))
    const args = {
      videoId: 1,
      language: 'en',
      platform: 'youtube',
      title: 'My Title',
      caption: 'Body text',
      hashtags: ['#purr'],
    }
    const result = await saveCaption(args)
    expect(result).toEqual(responseData)
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toBe('/api/captions/save')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body).toMatchObject({
      video_id: 1,
      language: 'en',
      platform: 'youtube',
      title: 'My Title',
      caption: 'Body text',
      hashtags: ['#purr'],
    })
  })

  it('uses Content-Type application/json header', async () => {
    vi.stubGlobal('fetch', makeFetch(true, {}))
    await saveCaption({
      videoId: 1,
      language: 'en',
      platform: 'youtube',
      caption: 'C',
      hashtags: [],
    })
    const opts = fetch.mock.calls[0][1]
    expect(opts.headers['Content-Type']).toBe('application/json')
  })

  it('throws on error response', async () => {
    vi.stubGlobal('fetch', makeFetch(false, {}, 500))
    await expect(
      saveCaption({ videoId: 1, language: 'en', platform: 'youtube', caption: 'C', hashtags: [] })
    ).rejects.toThrow('500')
  })
})
