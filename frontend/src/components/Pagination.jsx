import './Pagination.css'

export default function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null

  return (
    <nav className="pagination" aria-label="Page navigation">
      <button
        className="page-btn"
        onClick={() => onPage(page - 1)}
        disabled={page === 1}
        aria-label="Previous page"
      >
        ‹
      </button>

      {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
        <button
          key={p}
          className={`page-btn${p === page ? ' active' : ''}`}
          onClick={() => onPage(p)}
          aria-current={p === page ? 'page' : undefined}
        >
          {p}
        </button>
      ))}

      <button
        className="page-btn"
        onClick={() => onPage(page + 1)}
        disabled={page === pages}
        aria-label="Next page"
      >
        ›
      </button>
    </nav>
  )
}
