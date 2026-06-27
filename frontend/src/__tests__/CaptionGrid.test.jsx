import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api.js')

import * as api from '../api.js'
import CaptionGrid from '../components/CaptionGrid.jsx'

const LANGS = ['en', 'uk', 'zh', 'fr']
const PLATFORMS = ['youtube', 'tiktok', 'instagram']

function makeCaption(language, platform, overrides = {}) {
  return {
    id: `${language}-${platform}`,
    language,
    platform,
    title: `Title ${language} ${platform}`,
    caption: `Caption for ${language} on ${platform}`,
    hashtags: ['#purr', '#facts'],
    source: 'skill',
    ...overrides,
  }
}

function makeFullGrid() {
  return LANGS.flatMap((lang) => PLATFORMS.map((platform) => makeCaption(lang, platform)))
}

describe('CaptionGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.saveCaption.mockResolvedValue({ ok: true })
  })

  // ─── empty state ────────────────────────────────────────────────────────────

  it('renders the empty-state message when captions array is empty', () => {
    render(<CaptionGrid videoId={1} captions={[]} />)
    expect(screen.getByText(/No descriptions imported/)).toBeInTheDocument()
  })

  // ─── grid structure ─────────────────────────────────────────────────────────

  it('renders platform column headers', () => {
    render(<CaptionGrid videoId={1} captions={makeFullGrid()} />)
    expect(screen.getByText('YouTube')).toBeInTheDocument()
    expect(screen.getByText('TikTok')).toBeInTheDocument()
    expect(screen.getByText('Instagram')).toBeInTheDocument()
  })

  it('renders a row label for each of the 4 languages', () => {
    render(<CaptionGrid videoId={1} captions={makeFullGrid()} />)
    expect(screen.getByText('EN')).toBeInTheDocument()
    expect(screen.getByText('UK')).toBeInTheDocument()
    expect(screen.getByText('ZH')).toBeInTheDocument()
    expect(screen.getByText('FR')).toBeInTheDocument()
  })

  it('renders "—" placeholder for null cells', () => {
    // Only provide en/youtube; the other 11 cells should show "—"
    const captions = [makeCaption('en', 'youtube')]
    render(<CaptionGrid videoId={1} captions={captions} />)
    const dashes = screen.getAllByText('—')
    expect(dashes).toHaveLength(11)
  })

  // ─── YouTube cell specifics ─────────────────────────────────────────────────

  it('renders a title input only for youtube cells', () => {
    // Only en/youtube cell is populated; no other cells have an input
    const captions = [makeCaption('en', 'youtube')]
    render(<CaptionGrid videoId={1} captions={captions} />)
    // The Title label only appears in youtube cells
    expect(screen.getAllByText('Title')).toHaveLength(1)
  })

  it('shows char count for youtube title', () => {
    const captions = [makeCaption('en', 'youtube', { title: 'Hello' })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    // "5/100" for the 5-char title with limit 100
    expect(screen.getByText('5/100')).toBeInTheDocument()
  })

  // ─── blur-triggered auto-save ────────────────────────────────────────────────

  it('calls saveCaption when a tiktok textarea is edited then blurred', async () => {
    const captions = [makeCaption('en', 'tiktok')]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)

    const textarea = container.querySelector('textarea')
    fireEvent.change(textarea, { target: { value: 'new caption text' } })
    fireEvent.blur(textarea)

    await waitFor(() => expect(api.saveCaption).toHaveBeenCalledTimes(1))
    expect(api.saveCaption).toHaveBeenCalledWith(
      expect.objectContaining({
        videoId: 1,
        language: 'en',
        platform: 'tiktok',
        caption: 'new caption text',
      })
    )
  })

  it('does NOT call saveCaption if the textarea is blurred without editing', () => {
    const captions = [makeCaption('en', 'tiktok')]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)
    const textarea = container.querySelector('textarea')
    fireEvent.blur(textarea)
    expect(api.saveCaption).not.toHaveBeenCalled()
  })

  it('passes title=null for non-youtube platforms', async () => {
    const captions = [makeCaption('en', 'instagram')]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)
    const textarea = container.querySelector('textarea')
    fireEvent.change(textarea, { target: { value: 'insta text' } })
    fireEvent.blur(textarea)

    await waitFor(() => expect(api.saveCaption).toHaveBeenCalled())
    expect(api.saveCaption).toHaveBeenCalledWith(expect.objectContaining({ title: null }))
  })

  it('calls saveCaption with the youtube title value', async () => {
    const captions = [makeCaption('en', 'youtube', { title: 'Old title' })]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)

    // Change the textarea (description field)
    const textarea = container.querySelector('textarea')
    fireEvent.change(textarea, { target: { value: 'changed description' } })
    fireEvent.blur(textarea)

    await waitFor(() => expect(api.saveCaption).toHaveBeenCalled())
    expect(api.saveCaption).toHaveBeenCalledWith(
      expect.objectContaining({ platform: 'youtube', title: 'Old title' })
    )
  })

  // ─── edited badge ────────────────────────────────────────────────────────────

  it('shows "edited" badge after a successful save', async () => {
    const captions = [makeCaption('en', 'tiktok')]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)
    const textarea = container.querySelector('textarea')
    fireEvent.change(textarea, { target: { value: 'updated' } })
    fireEvent.blur(textarea)

    await waitFor(() => expect(screen.getByText('edited')).toBeInTheDocument())
  })

  it('shows "edited" badge immediately for cells with source=manual', () => {
    const captions = [makeCaption('en', 'tiktok', { source: 'manual' })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    expect(screen.getByText('edited')).toBeInTheDocument()
  })

  // ─── save error ──────────────────────────────────────────────────────────────

  it('shows "save failed" error message when saveCaption rejects', async () => {
    api.saveCaption.mockRejectedValue(new Error('network'))
    const captions = [makeCaption('en', 'tiktok')]
    const { container } = render(<CaptionGrid videoId={1} captions={captions} />)
    const textarea = container.querySelector('textarea')
    fireEvent.change(textarea, { target: { value: 'anything' } })
    fireEvent.blur(textarea)

    await waitFor(() => expect(screen.getByText('save failed')).toBeInTheDocument())
  })

  // ─── char counts ─────────────────────────────────────────────────────────────

  it('shows tiktok char limit as /150', () => {
    const captions = [makeCaption('en', 'tiktok', { caption: 'Hi' })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    expect(screen.getByText('2/150')).toBeInTheDocument()
  })

  it('shows instagram char limit as /2200', () => {
    const captions = [makeCaption('en', 'instagram', { caption: 'Hi' })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    expect(screen.getByText('2/2200')).toBeInTheDocument()
  })

  it('shows youtube description char limit as /5000', () => {
    const captions = [makeCaption('en', 'youtube', { caption: 'Hi' })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    expect(screen.getByText('2/5000')).toBeInTheDocument()
  })

  // ─── hashtags ────────────────────────────────────────────────────────────────

  it('renders hashtag chips for each caption', () => {
    const captions = [makeCaption('en', 'tiktok', { hashtags: ['#cat', '#facts'] })]
    render(<CaptionGrid videoId={1} captions={captions} />)
    expect(screen.getByText('#cat')).toBeInTheDocument()
    expect(screen.getByText('#facts')).toBeInTheDocument()
  })
})
