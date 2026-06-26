import './Pagination.css'

/**
 * Renders numbered page controls.
 * Hidden (returns null) when pages <= 1.
 */
export default function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null

  // Build page number list with ellipsis for large sets
  function buildPages() {
    if (pages <= 7) {
      return Array.from({ length: pages }, (_, i) => i + 1)
    }
    const items = []
    items.push(1)
    if (page > 3) items.push('…')
    const start = Math.max(2, page - 1)
    const end = Math.min(pages - 1, page + 1)
    for (let i = start; i <= end; i++) items.push(i)
    if (page < pages - 2) items.push('…')
    items.push(pages)
    return items
  }

  const items = buildPages()

  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        className="page-btn"
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        ‹
      </button>

      {items.map((item, idx) =>
        item === '…' ? (
          <span key={`ellipsis-${idx}`} className="page-ellipsis">…</span>
        ) : (
          <button
            key={item}
            className={`page-btn${item === page ? ' active' : ''}`}
            onClick={() => item !== page && onPage(item)}
            aria-current={item === page ? 'page' : undefined}
          >
            {item}
          </button>
        )
      )}

      <button
        className="page-btn"
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
        aria-label="Next page"
      >
        ›
      </button>
    </nav>
  )
}
