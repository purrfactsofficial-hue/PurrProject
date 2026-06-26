import StatusTag from './StatusTag.jsx'
import './VideoCard.css'

const GRADIENTS = [
  'linear-gradient(135deg,#f3dbe2,#e9c9d3)',
  'linear-gradient(135deg,#d9e7ec,#c5dbe4)',
  'linear-gradient(135deg,#ece0c9,#e0d0b0)',
  'linear-gradient(135deg,#f0d8c4,#e7c2a6)',
  'linear-gradient(135deg,#eee2c0,#e3d09a)',
  'linear-gradient(135deg,#e8e4dc,#d8d2c6)',
  'linear-gradient(135deg,#dce6ec,#c9dbe6)',
  'linear-gradient(135deg,#e6dcea,#d6c6e0)',
  'linear-gradient(135deg,#f2ddc6,#ecca9f)',
]

function fmtDuration(secs) {
  if (!secs) return null
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function fmtSize(bytes) {
  if (!bytes) return null
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

export default function VideoCard({ episode }) {
  const { episode_num, name, thumbnail_path, duration_secs, size_bytes, languages, status } = episode
  const gradient = GRADIENTS[(episode_num - 1) % GRADIENTS.length]
  const duration = fmtDuration(duration_secs)
  const size = fmtSize(size_bytes)

  return (
    <article className="card">
      <div className="thumb">
        {thumbnail_path ? (
          <img
            src={`/api${thumbnail_path}`}
            alt={name}
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
        ) : null}
        <div
          className="thumb-fallback"
          style={{ background: gradient }}
          aria-hidden="true"
        />
        <span className="ep-badge">Ep {episode_num}</span>
        {duration && <span className="dur">{duration}</span>}
      </div>

      <div className="card-body">
        <div className="card-name">{name}</div>
        <div className="card-sub">
          Episode {episode_num}{size ? ` · ${size}` : ''} · mp4
        </div>
        <div className="langs">
          {languages.map((lang) => (
            <span key={lang} className="lang-chip">{lang.toUpperCase()}</span>
          ))}
        </div>
        <div className="card-status">
          <StatusTag status={status} />
          <button className="open-btn" tabIndex={-1} aria-hidden="true">Open →</button>
        </div>
      </div>
    </article>
  )
}
