import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Pagination from '../components/Pagination.jsx'

describe('Pagination', () => {
  it('renders null when pages is 1', () => {
    const { container } = render(<Pagination page={1} pages={1} onPage={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders null when pages is 0', () => {
    const { container } = render(<Pagination page={1} pages={0} onPage={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders a nav with aria-label when pages > 1', () => {
    render(<Pagination page={1} pages={3} onPage={vi.fn()} />)
    expect(screen.getByRole('navigation', { name: 'Page navigation' })).toBeInTheDocument()
  })

  it('renders the correct number of page buttons', () => {
    render(<Pagination page={1} pages={4} onPage={vi.fn()} />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('disables prev button on first page', () => {
    render(<Pagination page={1} pages={3} onPage={vi.fn()} />)
    expect(screen.getByLabelText('Previous page')).toBeDisabled()
  })

  it('enables prev button when not on first page', () => {
    render(<Pagination page={2} pages={3} onPage={vi.fn()} />)
    expect(screen.getByLabelText('Previous page')).not.toBeDisabled()
  })

  it('disables next button on last page', () => {
    render(<Pagination page={3} pages={3} onPage={vi.fn()} />)
    expect(screen.getByLabelText('Next page')).toBeDisabled()
  })

  it('enables next button when not on last page', () => {
    render(<Pagination page={2} pages={3} onPage={vi.fn()} />)
    expect(screen.getByLabelText('Next page')).not.toBeDisabled()
  })

  it('calls onPage(page - 1) when prev is clicked', async () => {
    const user = userEvent.setup()
    const onPage = vi.fn()
    render(<Pagination page={2} pages={3} onPage={onPage} />)
    await user.click(screen.getByLabelText('Previous page'))
    expect(onPage).toHaveBeenCalledWith(1)
  })

  it('calls onPage(page + 1) when next is clicked', async () => {
    const user = userEvent.setup()
    const onPage = vi.fn()
    render(<Pagination page={1} pages={3} onPage={onPage} />)
    await user.click(screen.getByLabelText('Next page'))
    expect(onPage).toHaveBeenCalledWith(2)
  })

  it('calls onPage with the correct page when a numbered button is clicked', async () => {
    const user = userEvent.setup()
    const onPage = vi.fn()
    render(<Pagination page={1} pages={3} onPage={onPage} />)
    await user.click(screen.getByText('3'))
    expect(onPage).toHaveBeenCalledWith(3)
  })

  it('marks the active page with aria-current="page"', () => {
    render(<Pagination page={2} pages={3} onPage={vi.fn()} />)
    expect(screen.getByText('2')).toHaveAttribute('aria-current', 'page')
  })

  it('does not mark inactive pages with aria-current', () => {
    render(<Pagination page={2} pages={3} onPage={vi.fn()} />)
    expect(screen.getByText('1')).not.toHaveAttribute('aria-current')
    expect(screen.getByText('3')).not.toHaveAttribute('aria-current')
  })

  it('applies "active" class to the current page button', () => {
    render(<Pagination page={2} pages={3} onPage={vi.fn()} />)
    expect(screen.getByText('2')).toHaveClass('active')
    expect(screen.getByText('1')).not.toHaveClass('active')
  })
})
