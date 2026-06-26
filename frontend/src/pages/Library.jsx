import { useCallback, useEffect, useState } from 'react'
import { listVideos, scanVideos } from '../api.js'
import Pagination from '../components/Pagination.jsx'
import VideoCard from '../components/VideoCard.jsx'
import './Library.css'

const FILTERS = [
  { label: 'All',       value: '' },
  { label: 'New',       value: 'new' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Posted',    value: 'published' },
]

const REPO_PATH = 'C:\\Users\\yborodulina\\Downloads\\Purr'

export default function Library() {
  const [episodes,     setEpisodes]     = useState([])
  const [total,        setTotal]        = useState(0)
  const [pages,        setPages]        = useState(1)
  const [page,         setPage]         = useState(1)
  const [activeFilter, setActiveFilter] = useState('')
  const [loading,      setLoading]      = useState(false)
  const [scanning,     setScanning]     = useState(false)
  const [error,        setError]        = useState(null)
  const [lastScanned,  setLastScanned]  = useState(null)

  const loadList = useCallback(async (status, p) => {
    setLoading(true)
    setError(null)
    try {
      const data = await listVideos({ status: status || undefined, page: p })
      setEpisodes(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleScan = useCallback(async () => {
    setScanning(true)
    setError(null)
    try {
      await scanVideos()
      setLastScanned(new Date())
      setPage(1)
      await loadList(activeFilter, 1)
    } catch (err) {
      setError(err.message)
    } finally {
      setScanning(false)
    }
  }, [activeFilter, loadList])

  // Scan once on mount
  useEffect(() => { handleScan() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilter = (value) => {
    setActiveFilter(value)
    setPage(1)
    loadList(value, 1)
  }

  const handlePage = (p) => {
    setPage(p)
    loadList(activeFilter, p)
  }

  const isBusy = loading || scanning

  return (
    <div>
      <div className="library-top">
        <div>
          <div className="eyebrow">Your worktable</div>
          <h1 className="library-title">Library <em>·</em> rendered clips</h1>
        </div>
        <button className="scan-btn" onClick={handleScan} disabled={isBusy}>
          {scanning ? 'Scanning…' : '↻ Scan folder'}
        </button>
      </div>

      <div className="meta-row">
        <span className="path-badge">{REPO_PATH}</span>
        {!error && !isBusy && total > 0 && (
          <span>
            <span className="dot-ok" />
            Connected · {total} clip{total !== 1 ? 's' : ''}
            {lastScanned && ' · scanned just now'}
          </span>
        )}
        <div className="filters">
          {FILTERS.map(({ label, value }) => (
            <button
              key={value}
              className={`chip${activeFilter === value ? ' on' : ''}`}
              onClick={() => handleFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid">
        {isBusy ? (
          Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-thumb" />
              <div className="skeleton-body">
                <div className="skeleton-line" style={{ width: '60%' }} />
                <div className="skeleton-line" style={{ width: '80%' }} />
                <div className="skeleton-line" style={{ width: '40%' }} />
              </div>
            </div>
          ))
        ) : error ? (
          <div className="state-box">
            <h2>Can&apos;t reach the backend</h2>
            <p>
              <code>cd backend &amp;&amp; uvicorn main:app --reload</code>
            </p>
          </div>
        ) : episodes.length === 0 ? (
          <div className="state-box">
            <h2>No episodes found</h2>
            <p>No episodes found. Make sure your video folder is set in <code>backend/.env</code> and click <strong>Scan folder</strong> to try again.</p>
          </div>
        ) : (
          episodes.map((ep) => <VideoCard key={ep.id} episode={ep} />)
        )}
      </div>

      {!isBusy && !error && pages > 1 && (
        <Pagination page={page} pages={pages} onPage={handlePage} />
      )}
    </div>
  )
}
