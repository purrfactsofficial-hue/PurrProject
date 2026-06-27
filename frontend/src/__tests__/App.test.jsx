import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api.js')

import * as api from '../api.js'
import App from '../App.jsx'

const episode = {
  id: 1,
  episode_num: 1,
  name: 'Venus',
  slug: 'episode-1-venus',
  status: 'draft',
  duration_secs: 30,
  size_bytes: null,
  languages: ['en'],
  thumbnail_path: null,
  primary_file: null,
}

function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  )
}

describe('App routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Library (rendered at '/') calls scanVideos + listVideos on mount.
    api.scanVideos.mockResolvedValue({ scanned: 0 })
    api.listVideos.mockResolvedValue({ items: [], total: 0, pages: 1 })
    // Episode page calls getVideo + getCaptions.
    api.getVideo.mockResolvedValue(episode)
    api.getCaptions.mockResolvedValue([])
  })

  // ─── nav ──────────────────────────────────────────────────────────────────────

  it('renders the PurrFacts brand name in the side nav', async () => {
    renderApp('/')
    expect(screen.getByText('PurrFacts')).toBeInTheDocument()
  })

  it('renders nav links for all five sections', () => {
    renderApp('/queue')
    expect(screen.getByRole('link', { name: /library/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /queue/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument()
  })

  // ─── / → Library ──────────────────────────────────────────────────────────────

  it('renders Library at root path', async () => {
    renderApp('/')
    // Library's title is visible during / after scan
    expect(screen.getByText(/Library/)).toBeInTheDocument()
  })

  it('shows the scan button at root', () => {
    renderApp('/')
    expect(screen.getByRole('button', { name: /scan/i })).toBeInTheDocument()
  })

  // ─── /queue ───────────────────────────────────────────────────────────────────

  it('renders Queue placeholder at /queue', () => {
    renderApp('/queue')
    expect(screen.getByText(/Queue/)).toBeInTheDocument()
  })

  // ─── /dashboard ───────────────────────────────────────────────────────────────

  it('renders Dashboard placeholder at /dashboard', () => {
    renderApp('/dashboard')
    expect(screen.getByText(/Analytics/)).toBeInTheDocument()
  })

  // ─── /settings ────────────────────────────────────────────────────────────────

  it('renders Settings placeholder at /settings', () => {
    renderApp('/settings')
    expect(screen.getByText(/Settings/)).toBeInTheDocument()
  })

  // ─── /episode/:id ─────────────────────────────────────────────────────────────

  it('renders Episode loading state at /episode/1 before data resolves', () => {
    api.getVideo.mockReturnValue(new Promise(() => {})) // never resolves
    renderApp('/episode/1')
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('renders Episode content after data resolves', async () => {
    renderApp('/episode/1')
    await waitFor(() => expect(screen.getByText('Venus')).toBeInTheDocument())
  })

  // ─── Nav active-link class ────────────────────────────────────────────────────

  it('applies active class to Library nav link at /', async () => {
    renderApp('/')
    const libraryLink = screen.getByRole('link', { name: /library/i })
    // NavLink sets class='active' for the matching route
    expect(libraryLink).toHaveClass('active')
  })

  it('does not apply active class to Queue link at /', async () => {
    renderApp('/')
    const queueLink = screen.getByRole('link', { name: /queue/i })
    expect(queueLink).not.toHaveClass('active')
  })

  it('applies active class to Queue nav link at /queue', () => {
    renderApp('/queue')
    const queueLink = screen.getByRole('link', { name: /queue/i })
    expect(queueLink).toHaveClass('active')
  })
})
