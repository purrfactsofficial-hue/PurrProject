import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api.js')
import * as api from '../api.js'
import EpisodeScheduler from '../components/EpisodeScheduler.jsx'

const CAPTIONS_ALL = ['en', 'uk', 'zh', 'fr'].flatMap((lang) =>
  ['youtube', 'tiktok', 'instagram'].map((platform) => ({
    language: lang,
    platform,
    source: 'skill',
  }))
)

const SLOTS = {
  slots: [
    {
      language: 'en',
      audience_time: '8:00 PM',
      audience_tz: 'New York',
      your_time: '5:00 PM',
      your_tz: 'Pacific',
    },
    {
      language: 'uk',
      audience_time: '8:00 PM',
      audience_tz: 'Kyiv',
      your_time: '10:00 AM',
      your_tz: 'Pacific',
    },
    {
      language: 'zh',
      audience_time: '8:00 PM',
      audience_tz: 'Hong Kong',
      your_time: '5:00 AM',
      your_tz: 'Pacific',
    },
    {
      language: 'fr',
      audience_time: '8:00 PM',
      audience_tz: 'Paris',
      your_time: '11:00 AM',
      your_tz: 'Pacific',
    },
  ],
}

function renderScheduler(overrides = {}) {
  const props = {
    episodeId: 1,
    captions: CAPTIONS_ALL,
    onScheduled: vi.fn(),
    ...overrides,
  }
  return render(<EpisodeScheduler {...props} />)
}

describe('EpisodeScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSlots.mockResolvedValue(SLOTS)
    api.createSchedule.mockResolvedValue({ created: 12, warnings: [], errors: [] })
  })

  it('renders language toggles for all four languages', () => {
    renderScheduler()
    expect(screen.getByRole('button', { name: /EN/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /UK/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ZH/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /FR/i })).toBeInTheDocument()
  })

  it('renders platform toggles', () => {
    renderScheduler()
    expect(screen.getByRole('button', { name: /YouTube/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /TikTok/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Instagram/i })).toBeInTheDocument()
  })

  it('defaults all languages with captions to selected', () => {
    renderScheduler()
    // All 4 lang buttons should have selected/active styling — check aria or class
    const enBtn = screen.getByRole('button', { name: /^EN$/i })
    expect(enBtn.className).toMatch(/on|active|selected/)
  })

  it('clicking a language toggle deselects it', async () => {
    const user = userEvent.setup()
    renderScheduler()
    const enBtn = screen.getByRole('button', { name: /^EN$/i })
    await user.click(enBtn)
    expect(enBtn.className).not.toMatch(/\bon\b/)
  })

  it('date change triggers getSlots call', async () => {
    const user = userEvent.setup()
    renderScheduler()
    const dateInput = screen.getByLabelText(/date/i)
    await user.type(dateInput, '2025-07-04')
    await waitFor(() => expect(api.getSlots).toHaveBeenCalledWith('2025-07-04'))
  })

  it('slot preview renders audience and pacific times', async () => {
    const user = userEvent.setup()
    renderScheduler()
    const dateInput = screen.getByLabelText(/date/i)
    await user.type(dateInput, '2025-07-04')
    await waitFor(() => expect(screen.getByText(/New York/i)).toBeInTheDocument())
    expect(screen.getByText(/5:00 PM/i)).toBeInTheDocument()
  })

  it('schedule button calls createSchedule with selected langs/platforms', async () => {
    const user = userEvent.setup()
    renderScheduler()
    const dateInput = screen.getByLabelText(/date/i)
    await user.type(dateInput, '2025-07-04')

    await user.click(screen.getByRole('button', { name: /schedule selected/i }))
    await waitFor(() =>
      expect(api.createSchedule).toHaveBeenCalledWith(
        expect.objectContaining({
          episodeId: 1,
          date: '2025-07-04',
          languages: expect.arrayContaining(['en', 'uk', 'zh', 'fr']),
          platforms: expect.arrayContaining(['youtube', 'tiktok', 'instagram']),
        })
      )
    )
  })

  it('calls onScheduled after successful schedule', async () => {
    const user = userEvent.setup()
    const onScheduled = vi.fn()
    renderScheduler({ onScheduled })
    await user.type(screen.getByLabelText(/date/i), '2025-07-04')
    await user.click(screen.getByRole('button', { name: /schedule selected/i }))
    await waitFor(() => expect(onScheduled).toHaveBeenCalled())
  })

  it('shows validation error inline when createSchedule returns 409', async () => {
    const user = userEvent.setup()
    api.createSchedule.mockRejectedValue(
      Object.assign(new Error('409'), {
        data: { detail: "Can't schedule — no caption for en/youtube" },
      })
    )
    renderScheduler()
    await user.type(screen.getByLabelText(/date/i), '2025-07-04')
    await user.click(screen.getByRole('button', { name: /schedule selected/i }))
    await waitFor(() => expect(screen.getByText(/Can't schedule/i)).toBeInTheDocument())
  })

  it('shows warnings from the API response', async () => {
    api.createSchedule.mockResolvedValue({
      created: 3,
      warnings: ['EN/youtube already has a post that day.'],
      errors: [],
    })
    const user = userEvent.setup()
    renderScheduler()
    await user.type(screen.getByLabelText(/date/i), '2025-07-04')
    await user.click(screen.getByRole('button', { name: /schedule selected/i }))
    await waitFor(() => expect(screen.getByText(/already has a post/i)).toBeInTheDocument())
  })
})
