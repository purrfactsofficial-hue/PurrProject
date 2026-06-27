import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StatusTag from '../components/StatusTag.jsx'

describe('StatusTag', () => {
  const knownStatuses = [
    ['new', 'New render'],
    ['draft', 'Draft'],
    ['ready', 'Captions ready'],
    ['scheduled', 'Scheduled'],
    ['published', 'Posted'],
    ['failed', 'Failed'],
  ]

  it.each(knownStatuses)('renders label "%s" for status "%s"', (status, expectedLabel) => {
    render(<StatusTag status={status} />)
    expect(screen.getByText(`● ${expectedLabel}`)).toBeInTheDocument()
  })

  it('falls back to Draft label for an unknown status', () => {
    render(<StatusTag status="totally_unknown" />)
    expect(screen.getByText('● Draft')).toBeInTheDocument()
  })

  it('falls back to Draft label when status is undefined', () => {
    render(<StatusTag />)
    expect(screen.getByText('● Draft')).toBeInTheDocument()
  })

  it('applies the correct CSS class for ready status', () => {
    const { container } = render(<StatusTag status="ready" />)
    expect(container.firstChild).toHaveClass('tag-ready')
  })

  it('applies the correct CSS class for new status', () => {
    const { container } = render(<StatusTag status="new" />)
    expect(container.firstChild).toHaveClass('tag-new')
  })

  it('applies tag-sched class for scheduled and published', () => {
    const { container: c1 } = render(<StatusTag status="scheduled" />)
    expect(c1.firstChild).toHaveClass('tag-sched')

    const { container: c2 } = render(<StatusTag status="published" />)
    expect(c2.firstChild).toHaveClass('tag-sched')
  })
})
