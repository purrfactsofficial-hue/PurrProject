import './StatusTag.css'

const STATUS_CONFIG = {
  new:       { label: 'New render',     cls: 'tag-new' },
  draft:     { label: 'Draft',          cls: 'tag-draft' },
  ready:     { label: 'Captions ready', cls: 'tag-ready' },
  scheduled: { label: 'Scheduled',      cls: 'tag-sched' },
  published: { label: 'Posted',         cls: 'tag-sched' },
  failed:    { label: 'Failed',         cls: 'tag-draft' },
}

export default function StatusTag({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft
  return (
    <span className={`status-tag ${cfg.cls}`}>● {cfg.label}</span>
  )
}
