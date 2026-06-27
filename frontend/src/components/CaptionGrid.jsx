import { useEffect, useRef, useState } from 'react'
import { saveCaption } from '../api.js'
import './CaptionGrid.css'

const LANGS = ['en', 'uk', 'zh', 'fr']
const PLATFORMS = ['youtube', 'tiktok', 'instagram']
const PLATFORM_LABELS = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram' }

function buildGrid(captions) {
  const g = {}
  for (const lang of LANGS) {
    g[lang] = {}
    for (const platform of PLATFORMS) {
      g[lang][platform] = null
    }
  }
  for (const c of captions) {
    if (g[c.language]) g[c.language][c.platform] = c
  }
  return g
}

function CaptionCell({ cell, videoId, language, platform }) {
  const [title, setTitle] = useState(cell?.title ?? '')
  const [text, setText] = useState(cell?.caption ?? '')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [isManual, setIsManual] = useState(cell?.source === 'manual')
  const dirty = useRef(false)

  useEffect(() => {
    setTitle(cell?.title ?? '')
    setText(cell?.caption ?? '')
    setIsManual(cell?.source === 'manual')
    dirty.current = false
  }, [cell])

  const handleSave = async () => {
    if (!dirty.current || !cell || saving) return
    setSaving(true)
    setSaveError(null)
    try {
      await saveCaption({
        videoId,
        language,
        platform,
        title: platform === 'youtube' ? title : null,
        caption: text,
        hashtags: cell.hashtags,
      })
      setIsManual(true)
      dirty.current = false
    } catch {
      setSaveError('save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!cell) {
    return (
      <div className="caption-cell stitched" style={{ opacity: 0.4 }}>
        —
      </div>
    )
  }

  const titleLimit = platform === 'youtube' ? 100 : null
  const textLimit = platform === 'tiktok' ? 150 : platform === 'instagram' ? 2200 : 5000

  return (
    <div className={`caption-cell stitched${isManual ? ' edited' : ''}`}>
      {platform === 'youtube' && (
        <>
          <span className="cell-label">Title</span>
          <input
            className="cell-title"
            value={title}
            maxLength={100}
            onChange={(e) => {
              setTitle(e.target.value)
              dirty.current = true
            }}
            onBlur={handleSave}
          />
          {titleLimit && (
            <span className="char-count">
              {title.length}/{titleLimit}
            </span>
          )}
          <span className="cell-label">Description</span>
        </>
      )}
      {platform !== 'youtube' && <span className="cell-label">Caption</span>}
      <textarea
        className="cell-text"
        value={text}
        rows={platform === 'youtube' ? 4 : 3}
        onChange={(e) => {
          setText(e.target.value)
          dirty.current = true
        }}
        onBlur={handleSave}
      />
      <span className="char-count">
        {text.length}/{textLimit}
      </span>
      <div className="hashtag-chips">
        {cell.hashtags.map((h, i) => (
          <span key={`${h}-${i}`} className="hashtag-chip">
            {h}
          </span>
        ))}
      </div>
      <div className="cell-footer">
        {isManual && <span className="edited-mark">edited</span>}
        {saving && <span className="saving-mark">saving…</span>}
        {saveError && (
          <span className="saving-mark" style={{ color: '#b04040' }}>
            {saveError}
          </span>
        )}
      </div>
    </div>
  )
}

export default function CaptionGrid({ videoId, captions }) {
  if (!captions.length) {
    return (
      <p className="caption-empty">
        No descriptions imported. Click Import to pull them from this episode&apos;s captions.json.
      </p>
    )
  }

  const grid = buildGrid(captions)

  return (
    <div className="caption-grid-wrap">
      <div className="caption-grid">
        <div className="grid-corner" />
        {PLATFORMS.map((p) => (
          <div key={p} className="platform-label">
            {PLATFORM_LABELS[p]}
          </div>
        ))}
        {LANGS.map((lang) => (
          <div key={lang} className="caption-row">
            <span className="lang-label">{lang.toUpperCase()}</span>
            {PLATFORMS.map((platform) => (
              <CaptionCell
                key={platform}
                cell={grid[lang][platform]}
                videoId={videoId}
                language={lang}
                platform={platform}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
