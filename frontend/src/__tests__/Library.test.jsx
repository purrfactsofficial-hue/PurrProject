import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api.js')

import * as api from '../api.js'
import Library from '../pages/Library.jsx'

const episode = {
  id: 1,
  episode_num: 9,
  name: 'Pizza',
  slug: 'episode-9-pizza',
  status: 'ready',
  duration_secs: 44,
  size_bytes: null,
  languages: ['en', 'fr'],
  thumbnail_path: null,
}

function renderLibrary() {
  return render(
    <MemoryRouter>
      <Library />
    </MemoryRouter>
  )
}

describe('Library', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.scanVideos.mockResolvedValue({ scanned: 1 })
    api.listVideos.mockResolvedValue({ items: [episode], total: 1, pages: 1 })
  })

  // ─── mount behaviour ─────────────────────────────────────────────────────────

  it('calls scanVideos on mount', async () => {
    renderLibrary()
    await waitFor(() => expect(api.scanVideos).toHaveBeenCalledTimes(1))
  })

  it('calls listVideos after scan completes', async () => {
    renderLibrary()
    await waitFor(() => expect(api.listVideos).toHaveBeenCalled())
  })

  it('renders episode cards after the list loads', async () => {
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
  })

  it('shows skeleton cards while scanning', () => {
    // Make scan resolve slowly so scanning=true persists during check
    api.scanVideos.mockReturnValue(new Promise(() => {}))
    renderLibrary()
    // 12 skeleton cards should be present while busy
    const skeletons = document.querySelectorAll('.skeleton-card')
    expect(skeletons.length).toBe(12)
  })

  // ─── scan button ─────────────────────────────────────────────────────────────

  it('scan button triggers another scan+reload', async () => {
    const user = userEvent.setup()
    renderLibrary()
    // Wait for the first automatic scan to finish
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /scan folder/i }))
    await waitFor(() => expect(api.scanVideos).toHaveBeenCalledTimes(2))
  })

  it('scan button is disabled while scanning', async () => {
    api.scanVideos.mockReturnValue(new Promise(() => {})) // never resolves
    renderLibrary()
    expect(screen.getByRole('button', { name: /scanning/i })).toBeDisabled()
  })

  // ─── status filters ──────────────────────────────────────────────────────────

  it('clicking the Draft filter calls listVideos with status=draft', async () => {
    const user = userEvent.setup()
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Draft' }))
    await waitFor(() =>
      expect(api.listVideos).toHaveBeenCalledWith(expect.objectContaining({ status: 'draft' }))
    )
  })

  it('clicking All filter calls listVideos with status undefined', async () => {
    const user = userEvent.setup()
    // Prime with draft
    api.listVideos.mockResolvedValue({ items: [], total: 0, pages: 1 })
    renderLibrary()
    await waitFor(() => expect(api.listVideos).toHaveBeenCalled())

    await user.click(screen.getByRole('button', { name: 'All' }))
    await waitFor(() =>
      expect(api.listVideos).toHaveBeenCalledWith(expect.objectContaining({ status: undefined }))
    )
  })

  it('clicking a filter resets the page to 1', async () => {
    const user = userEvent.setup()
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Scheduled' }))
    await waitFor(() =>
      expect(api.listVideos).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }))
    )
  })

  // ─── pagination ──────────────────────────────────────────────────────────────

  it('shows pagination when pages > 1', async () => {
    api.listVideos.mockResolvedValue({ items: [episode], total: 24, pages: 2 })
    renderLibrary()
    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: 'Page navigation' })).toBeInTheDocument()
    )
  })

  it('does not show pagination when pages === 1', async () => {
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    expect(screen.queryByRole('navigation', { name: 'Page navigation' })).toBeNull()
  })

  it('clicking next page calls listVideos with page 2', async () => {
    const user = userEvent.setup()
    api.listVideos.mockResolvedValue({ items: [episode], total: 24, pages: 2 })
    renderLibrary()
    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: 'Page navigation' })).toBeInTheDocument()
    )

    await user.click(screen.getByLabelText('Next page'))
    await waitFor(() =>
      expect(api.listVideos).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }))
    )
  })

  // ─── error state ─────────────────────────────────────────────────────────────

  it('shows the backend error box when scanVideos rejects', async () => {
    api.scanVideos.mockRejectedValue(new Error('ECONNREFUSED'))
    renderLibrary()
    await waitFor(() => expect(screen.getByText("Can't reach the backend")).toBeInTheDocument())
  })

  it('shows the backend error box when listVideos rejects', async () => {
    api.listVideos.mockRejectedValue(new Error('network error'))
    renderLibrary()
    await waitFor(() => expect(screen.getByText("Can't reach the backend")).toBeInTheDocument())
  })

  // ─── empty state ─────────────────────────────────────────────────────────────

  it('shows the empty-state box when no episodes are returned', async () => {
    api.listVideos.mockResolvedValue({ items: [], total: 0, pages: 1 })
    renderLibrary()
    await waitFor(() => expect(screen.getByText('No episodes found')).toBeInTheDocument())
  })

  // ─── connected badge ─────────────────────────────────────────────────────────

  it('shows connected status after successful scan with episodes', async () => {
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    // The "Connected · N clip(s)" text appears after a successful scan
    expect(document.body.textContent).toMatch(/Connected/)
    expect(document.body.textContent).toMatch(/1 clip/)
  })

  it('shows "scanned just now" text after scan completes', async () => {
    renderLibrary()
    await waitFor(() => expect(screen.getByText('Pizza')).toBeInTheDocument())
    expect(document.body.textContent).toMatch(/scanned just now/)
  })
})
