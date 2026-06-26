import './StatusTag.css'

const LABELS = {
  new:       'New',
  scheduled: 'Scheduled',
  posted:    'Posted',
  published: 'Posted',
}

export default function StatusTag({ status }) {
  const key = status || 'default'
  const cls = ['new', 'scheduled', 'posted', 'published'].includes(key) ? key : 'default'
  const label = LABELS[key] ?? (status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown')

  return (
    <span className={`status-tag status-tag--${cls}`}>
      {label}
    </span>
  )
}
