import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api.js')
import * as api from '../api.js'
import Queue from '../pages/Queue.jsx'

const POST_SCHEDULED = {
  id: 1,
  episode_id: 1,
  episode_name: 'Pizza',
  language: 'en',
  platform: 'youtube',
  status: 'scheduled',
  scheduled_for: '2025-07-05T00:00:00Z',
  platform_post_id: null,
  error_message: null,
}
const POST_FAILED = {
  id: 2,
  episode_id: 1,
  episode_name: 'Pizza',
  language: 'uk',
  platform: 'tiktok',
  status: 'failed',
  scheduled_for: '2025-07-04T17:00:00Z',
  platform_post_id: null,
  error_message: 'API timeout',
}
const POST_PUBLISHED = {
  id: 3,
  episode_id: 1,
  episode_name: 'Pizza',
  language: 'zh',
  platform: 'instagram',
  status: 'published',
  scheduled_for: '2025-07-04T12:00:00Z',
  platform_post_id: 'dev-3-1234',
  error_message: null,
}

function renderQueue() {
  return render(
    <MemoryRouter>
      <Queue />
    </MemoryRouter>
  )
}

describe('Queue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getQueue.mockResolvedValue({ items: [POST_SCHEDULED, POST_FAILED, POST_PUBLISHED] })
    api.cancelPost.mockResolvedValue({ status: 'cancelled' })
    api.retryPost.mockResolvedValue({ status: 'scheduled' })
    api.reschedulePost.mockResolvedValue({
      ...POST_SCHEDULED,
      scheduled_for: '2025-08-02T00:00:00Z',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ── rendering ──────────────────────────────────────────────────────────────

  it('calls getQueue on mount', async () => {
    renderQueue()
    await waitFor(() => expect(api.getQueue).toHaveBeenCalledTimes(1))
  })

  it('renders all queue items', async () => {
    renderQueue()
    // 3 rows all named 'Pizza' — use getAllByText
    await waitFor(() => expect(screen.getAllByText('Pizza').length).toBeGreaterThanOrEqual(1))
    expect(screen.getAllByText('Pizza').length).toBeGreaterThanOrEqual(1)
  })

  it('shows status badges for each post', async () => {
    renderQueue()
    // '● scheduled' is unique to the badge (chip only says 'Scheduled')
    await waitFor(() => expect(screen.getByText(/● scheduled/i)).toBeInTheDocument())
    expect(screen.getByText(/● failed/i)).toBeInTheDocument()
    expect(screen.getByText(/● published/i)).toBeInTheDocument()
  })

  it('shows empty state when queue is empty', async () => {
    api.getQueue.mockResolvedValue({ items: [] })
    renderQueue()
    await waitFor(() => expect(screen.getByText(/queue is empty/i)).toBeInTheDocument())
  })

  // ── filters ────────────────────────────────────────────────────────────────

  it('filter chips render for status values', async () => {
    renderQueue()
    await waitFor(() => expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /scheduled/i })).toBeInTheDocument()
  })

  it('clicking Scheduled filter shows only scheduled posts', async () => {
    const user = userEvent.setup()
    renderQueue()
    // Use getAllByText since all 3 rows share episode_name 'Pizza'
    await waitFor(() => expect(screen.getAllByText('Pizza').length).toBeGreaterThanOrEqual(1))
    await user.click(screen.getByRole('button', { name: /^scheduled$/i }))
    // failed and published rows should be gone
    await waitFor(() => {
      const rows = screen.getAllByRole('row')
      // Header row + 1 data row (date-seam rows are aria-hidden)
      expect(rows.length).toBe(2)
    })
  })

  // ── cancel action ──────────────────────────────────────────────────────────

  it('cancel button calls cancelPost and re-fetches queue', async () => {
    const user = userEvent.setup()
    api.getQueue.mockResolvedValueOnce({ items: [POST_SCHEDULED] })
    api.getQueue.mockResolvedValue({ items: [] })
    renderQueue()
    // Use exact name 'Cancel' to avoid matching the 'Cancelled' filter chip
    await waitFor(() => expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(api.cancelPost).toHaveBeenCalledWith(POST_SCHEDULED.id))
    await waitFor(() => expect(api.getQueue).toHaveBeenCalledTimes(2))
  })

  // ── retry action ───────────────────────────────────────────────────────────

  it('retry button on failed post calls retryPost', async () => {
    const user = userEvent.setup()
    api.getQueue.mockResolvedValue({ items: [POST_FAILED] })
    renderQueue()
    await waitFor(() => expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /retry/i }))
    await waitFor(() => expect(api.retryPost).toHaveBeenCalledWith(POST_FAILED.id))
  })

  it('shows error message for failed posts', async () => {
    api.getQueue.mockResolvedValue({ items: [POST_FAILED] })
    renderQueue()
    await waitFor(() => expect(screen.getByText('API timeout')).toBeInTheDocument())
  })

  // ── action error display ───────────────────────────────────────────────────

  it('shows error when cancel fails', async () => {
    const user = userEvent.setup()
    api.getQueue.mockResolvedValue({ items: [POST_SCHEDULED] })
    api.cancelPost.mockRejectedValueOnce(new Error('Server error'))
    renderQueue()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument())
  })

  // ── reschedule action ──────────────────────────────────────────────────────

  it('reschedule date input and button calls reschedulePost', async () => {
    const user = userEvent.setup()
    api.getQueue.mockResolvedValue({ items: [POST_SCHEDULED] })
    renderQueue()
    await waitFor(() => expect(screen.getByLabelText(/reschedule/i)).toBeInTheDocument())
    await user.type(screen.getByLabelText(/reschedule/i), '2025-08-01')
    await user.click(screen.getByRole('button', { name: /reschedule/i }))
    await waitFor(() =>
      expect(api.reschedulePost).toHaveBeenCalledWith(POST_SCHEDULED.id, '2025-08-01')
    )
  })

  // ── auto-refresh ───────────────────────────────────────────────────────────

  it('polls getQueue every 30 seconds', async () => {
    vi.useFakeTimers()
    renderQueue()
    // Flush initial async work from useEffect/load()
    await act(async () => {})
    expect(api.getQueue).toHaveBeenCalledTimes(1)
    // Advance 30s — setInterval fires, getQueue called again
    act(() => vi.advanceTimersByTime(30000))
    expect(api.getQueue).toHaveBeenCalledTimes(2)
    act(() => vi.advanceTimersByTime(30000))
    expect(api.getQueue).toHaveBeenCalledTimes(3)
    vi.useRealTimers()
  })
})
