import { useState } from 'react'
import StatusTag from './StatusTag.jsx'
import './VideoCard.css'

// 9 tint backgrounds for when thumbnail fails to load
const FALLBACK_TINTS = [
  '#F2E0E8', // rose
  '#E8EDF8', // blue
  '#E8F2EA', // sage
  '#F8F0E0', // warm sand
  '#F0E8F4', // lavender
  '#E0EFF0', // teal
  '#F4EDE0', // peach
  '#E8F0E8', // mint
  '#F2EBE0', // linen
]

function formatDuration(secs) {
  if (!secs && secs !== 0) return ''
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatSize(bytes) {
  if (!bytes) return ''
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

export default function VideoCard({ episode }) {
  const {
    id,
    episode_num,
    name,
    thumbnail_path,
    duration_secs,
    size_bytes,
    languages = [],
    status,
  } = episode

  const [imgError, setImgError] = useState(false)
  const tint = FALLBACK_TINTS[(id ?? 0) % FALLBACK_TINTS.length]

  return (
    <div className="video-card">
      <div className="card-thumb-wrap">
        {thumbnail_path && !imgError ? (
          <img
            className="card-thumb"
            src={thumbnail_path}
            alt={`Episode ${episode_num} – ${name}`}
            onError={() => setImgError(true)}
          />
        ) : (
          <div
            className="card-thumb-fallback"
            style={{ background: tint }}
          >
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="4" width="20" height="16" rx="3" stroke="var(--ink)" strokeWidth="1.5" />
              <path d="M9 9l6 3-6 3V9z" fill="var(--ink)" />
            </svg>
          </div>
        )}

        {episode_num != null && (
          <span className="card-badge card-badge--ep">
            Ep.&nbsp;{episode_num}
          </span>
        )}

        {duration_secs != null && (
          <span className="card-badge card-badge--dur">
            {formatDuration(duration_secs)}
          </span>
        )}
      </div>

      <div className="card-body">
        <div className="card-name">{name}</div>

        {size_bytes != null && (
          <div className="card-meta">{formatSize(size_bytes)} · MP4</div>
        )}

        {languages.length > 0 && (
          <div className="card-langs">
            {languages.map((lang) => (
              <span key={lang} className="lang-chip">
                {lang.toUpperCase()}
              </span>
            ))}
          </div>
        )}

        <div className="card-footer">
          <StatusTag status={status} />
          <button className="card-open-btn" type="button">
            Open →
          </button>
        </div>
      </div>
    </div>
  )
}
