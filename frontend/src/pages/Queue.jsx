import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { cancelPost, getQueue, reschedulePost, retryPost } from '../api.js'
import './Queue.css'

const STATUS_FILTERS = ['all', 'scheduled', 'publishing', 'published', 'failed', 'cancelled']
const BADGE_CLASS = {
  scheduled: 'badge-scheduled',
  publishing: 'badge-publishing',
  published: 'badge-published',
  failed: 'badge-failed',
  cancelled: 'badge-cancelled',
}

function formatTime(isoStr) {
  const d = new Date(isoStr)
  return d.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'UTC',
  })
}

function formatDate(isoStr) {
  const d = new Date(isoStr)
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

function groupByDate(items) {
  const groups = new Map()
  for (const item of items) {
    const day = item.scheduled_for.slice(0, 10)
    if (!groups.has(day)) groups.set(day, [])
    groups.get(day).push(item)
  }
  return groups
}

function PostRow({ post, onAction }) {
  const [rescheduleDate, setRescheduleDate] = useState('')

  const handleRescheduleClick = async () => {
    if (!rescheduleDate) return
    try {
      await reschedulePost(post.id, rescheduleDate)
      onAction()
    } catch {
      // ignore — queue refresh will show current state
    }
  }

  const handleCancel = async () => {
    try {
      await cancelPost(post.id)
      onAction()
    } catch {
      // ignore
    }
  }

  const handleRetry = async () => {
    try {
      await retryPost(post.id)
      onAction()
    } catch {
      // ignore
    }
  }

  return (
    <tr>
      <td>
        <div>{formatTime(post.scheduled_for)} UTC</div>
      </td>
      <td>{post.episode_name}</td>
      <td>{post.language.toUpperCase()}</td>
      <td style={{ textTransform: 'capitalize' }}>{post.platform}</td>
      <td>
        <span className={`badge ${BADGE_CLASS[post.status] ?? ''}`}>● {post.status}</span>
        {post.error_message && <div className="error-msg">{post.error_message}</div>}
      </td>
      <td>
        <div className="row-actions">
          {post.status === 'failed' && (
            <button className="action-btn" onClick={handleRetry}>
              Retry
            </button>
          )}
          {post.status === 'scheduled' && (
            <>
              <input
                type="date"
                aria-label="Reschedule date"
                className="reschedule-input"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
              />
              <button
                className="action-btn"
                onClick={handleRescheduleClick}
                disabled={!rescheduleDate}
              >
                Reschedule
              </button>
              <button className="action-btn danger" onClick={handleCancel}>
                Cancel
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function Queue() {
  const [items, setItems] = useState([])
  const [activeFilter, setActiveFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const data = await getQueue()
      setItems(data.items)
    } catch {
      // keep stale data on refresh failure
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load()
    intervalRef.current = setInterval(load, 30000)
    return () => clearInterval(intervalRef.current)
  }, [load])

  const filtered = activeFilter === 'all' ? items : items.filter((i) => i.status === activeFilter)
  const groups = groupByDate(filtered)

  return (
    <div className="queue-page">
      <div className="queue-top">
        <div className="queue-eyebrow">Operations</div>
        <h1 className="queue-title">Queue</h1>
      </div>

      <div className="queue-filters">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            className={`chip${activeFilter === f ? ' on' : ''}`}
            onClick={() => setActiveFilter(f)}
          >
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {!loading && filtered.length === 0 ? (
        <div className="queue-empty">Queue is empty.</div>
      ) : (
        <table className="queue-table">
          <thead>
            <tr>
              <th>Time (UTC)</th>
              <th>Episode</th>
              <th>Lang</th>
              <th>Platform</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {[...groups.entries()].map(([day, posts]) => (
              <Fragment key={day}>
                <tr aria-hidden="true" className="date-seam">
                  <td colSpan={6}>{formatDate(day + 'T00:00:00Z')}</td>
                </tr>
                {posts.map((post) => (
                  <PostRow key={post.id} post={post} onAction={load} />
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
