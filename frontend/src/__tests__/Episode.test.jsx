import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

// Mock the api module — must come before importing consumers.
vi.mock('../api.js')

// Mock react-router-dom but keep all real exports; only override useParams
// so we can control the episode id per test.
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: vi.fn(() => ({ id: '1' })),
  }
})

import * as api from '../api.js'
import { useParams } from 'react-router-dom'
import Episode from '../pages/Episode.jsx'

const episode = {
  id: 1,
  episode_num: 9,
  name: 'Pizza',
  slug: 'episode-9-pizza',
  status: 'ready',
  duration_secs: 44,
  languages: ['en', 'fr'],
  thumbnail_path: null,
  primary_file: null, // no video element rendered
}

const captions = [
  {
    id: 1,
    language: 'en',
    platform: 'youtube',
    title: 'T',
    caption: 'C',
    hashtags: ['#A'],
    source: 'skill',
  },
]

function renderEpisode() {
  return render(
    <MemoryRouter initialEntries={['/episode/1']}>
      <Episode />
    </MemoryRouter>
  )
}

describe('Episode', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    // Re-apply the default useParams return after resetAllMocks cleared it.
    useParams.mockReturnValue({ id: '1' })
    api.getVideo.mockResolvedValue(episode)
    api.getCaptions.mockResolvedValue(captions)
    api.importCaptions.mockResolvedValue({ imported: 12, warnings: [], errors: [] })
  })

  // ─── loading / mount ─────────────────────────────────────────────────────────

  it('shows loading state before getVideo resolves', () => {
    api.getVideo.mockReturnValue(new Promise(() => {})) // never resolves
    renderEpisode()
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('calls getVideo and getCaptions with the numeric id on mount', async () => {
    renderEpisode()
    await waitFor(() => expect(api.getVideo).toHaveBeenCalledWith(1))
    expect(api.getCaptions).toHaveBeenCalledWith(1)
  })

  it('renders the episode name after load', async () => {
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
  })

  it('renders the episode number eyebrow', async () => {
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Episode 9')).toBeInTheDocument())
  })

  // ─── invalid id ──────────────────────────────────────────────────────────────

  it('shows an error for a non-numeric episode id', () => {
    useParams.mockReturnValue({ id: 'abc' })
    renderEpisode()
    expect(screen.getByText('Invalid episode ID.')).toBeInTheDocument()
  })

  it('does not call getVideo for an invalid id', () => {
    useParams.mockReturnValue({ id: 'xyz' })
    renderEpisode()
    expect(api.getVideo).not.toHaveBeenCalled()
  })

  // ─── video error ─────────────────────────────────────────────────────────────

  it('shows the error message when getVideo rejects', async () => {
    api.getVideo.mockRejectedValue(new Error('404 Not Found'))
    renderEpisode()
    await waitFor(() => expect(screen.getByText('404 Not Found')).toBeInTheDocument())
  })

  it('shows empty CaptionGrid when getCaptions fails', async () => {
    api.getCaptions.mockRejectedValue(new Error('forbidden'))
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    // CaptionGrid with empty captions shows the empty message
    expect(screen.getByText(/No descriptions imported/)).toBeInTheDocument()
  })

  // ─── video element ───────────────────────────────────────────────────────────

  it('renders a <video> element when primary_file is set', async () => {
    api.getVideo.mockResolvedValue({ ...episode, primary_file: 'video.mp4' })
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    const video = document.querySelector('video')
    expect(video).not.toBeNull()
    expect(video.getAttribute('src')).toBe('/api/videos/1/stream')
  })

  it('does not render a <video> element when primary_file is falsy', async () => {
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    expect(document.querySelector('video')).toBeNull()
  })

  // ─── import button ───────────────────────────────────────────────────────────

  it('import button calls importCaptions with the episode id', async () => {
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() => expect(api.importCaptions).toHaveBeenCalledWith(1))
  })

  it('import button is disabled while importing', async () => {
    api.importCaptions.mockReturnValue(new Promise(() => {})) // never resolves
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    expect(screen.getByRole('button', { name: /importing/i })).toBeDisabled()
  })

  it('shows success result after import', async () => {
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() => expect(screen.getByText(/Imported 12 descriptions/)).toBeInTheDocument())
  })

  it('re-fetches captions after a successful import', async () => {
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    // getCaptions called once on mount, once after import
    await waitFor(() => expect(api.getCaptions).toHaveBeenCalledTimes(2))
  })

  it('shows import warnings in the result panel', async () => {
    api.importCaptions.mockResolvedValue({
      imported: 10,
      warnings: ['2 captions already existed'],
      errors: [],
    })
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() => expect(screen.getByText(/2 captions already existed/)).toBeInTheDocument())
  })

  it('shows import errors in the result panel when result.errors is non-empty', async () => {
    api.importCaptions.mockResolvedValue({
      imported: 0,
      errors: ['File not found', 'Bad format'],
      warnings: [],
    })
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() => expect(screen.getByText('File not found')).toBeInTheDocument())
    expect(screen.getByText('Bad format')).toBeInTheDocument()
  })

  it('shows detail string as error when result.detail is a string', async () => {
    api.importCaptions.mockResolvedValue({ detail: 'Import failed: already exists' })
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() =>
      expect(screen.getByText('Import failed: already exists')).toBeInTheDocument()
    )
  })

  it('shows generic error when result.detail is an object', async () => {
    api.importCaptions.mockResolvedValue({ detail: [{ msg: 'bad' }] })
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() =>
      expect(screen.getByText('Import failed: validation error')).toBeInTheDocument()
    )
  })

  it('shows error message when importCaptions throws', async () => {
    api.importCaptions.mockRejectedValue(new Error('network error'))
    const user = userEvent.setup()
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    await user.click(screen.getByRole('button', { name: /import descriptions/i }))
    await waitFor(() => expect(screen.getByText('network error')).toBeInTheDocument())
  })

  // ─── navigation ──────────────────────────────────────────────────────────────

  it('renders the back-to-library button', async () => {
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    expect(screen.getByRole('button', { name: /library/i })).toBeInTheDocument()
  })

  it('renders the View Queue button', async () => {
    renderEpisode()
    await waitFor(() => screen.getByText('Pizza'))
    expect(screen.getByRole('button', { name: /view queue/i })).toBeInTheDocument()
  })
})
