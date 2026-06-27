import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import VideoCard from '../components/VideoCard.jsx'

const base = {
  id: 9,
  episode_num: 9,
  name: 'Pizza',
  slug: 'episode-9-pizza',
  status: 'ready',
  duration_secs: 44,
  size_bytes: 5_200_000,
  languages: ['en', 'fr'],
  thumbnail_path: '/thumbs/episode-9-pizza.jpg',
}

describe('VideoCard', () => {
  it('renders the episode name', () => {
    render(<VideoCard episode={base} />)
    expect(screen.getByText('Pizza')).toBeInTheDocument()
  })

  it('renders the episode badge', () => {
    render(<VideoCard episode={base} />)
    expect(screen.getByText('Ep 9')).toBeInTheDocument()
  })

  it('renders a thumbnail image when thumbnail_path is set', () => {
    render(<VideoCard episode={base} />)
    const img = screen.getByAltText('Pizza')
    expect(img).toHaveAttribute('src', '/api/thumbs/episode-9-pizza.jpg')
  })

  it('does not render an img element when thumbnail_path is falsy', () => {
    render(<VideoCard episode={{ ...base, thumbnail_path: null }} />)
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('renders the duration badge when duration_secs is set', () => {
    render(<VideoCard episode={base} />)
    expect(screen.getByText('0:44')).toBeInTheDocument()
  })

  it('does not render a duration badge when duration_secs is falsy', () => {
    render(<VideoCard episode={{ ...base, duration_secs: null }} />)
    expect(screen.queryByText(/\d:\d\d/)).toBeNull()
  })

  it('formats duration correctly for values over 60 seconds', () => {
    render(<VideoCard episode={{ ...base, duration_secs: 125 }} />)
    expect(screen.getByText('2:05')).toBeInTheDocument()
  })

  it('shows file size in MB when size_bytes is set', () => {
    render(<VideoCard episode={base} />)
    expect(screen.getByText(/5\.2 MB/)).toBeInTheDocument()
  })

  it('omits size when size_bytes is falsy', () => {
    render(<VideoCard episode={{ ...base, size_bytes: null }} />)
    expect(screen.queryByText(/MB/)).toBeNull()
  })

  it('renders language chips for each language', () => {
    render(<VideoCard episode={base} />)
    expect(screen.getByText('EN')).toBeInTheDocument()
    expect(screen.getByText('FR')).toBeInTheDocument()
  })

  it('renders the StatusTag for the episode status', () => {
    render(<VideoCard episode={base} />)
    // 'ready' status → "Captions ready" label
    expect(screen.getByText('● Captions ready')).toBeInTheDocument()
  })

  it('renders with draft status correctly', () => {
    render(<VideoCard episode={{ ...base, status: 'draft' }} />)
    expect(screen.getByText('● Draft')).toBeInTheDocument()
  })

  it('uses a gradient based on episode_num', () => {
    const { container } = render(<VideoCard episode={{ ...base, episode_num: 1 }} />)
    const fallback = container.querySelector('.thumb-fallback')
    expect(fallback).toBeInTheDocument()
    expect(fallback.style.background).toBeTruthy()
  })
})
