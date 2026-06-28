import { useState } from 'react'
import { createSchedule, getSlots } from '../api.js'
import './EpisodeScheduler.css'

const LANGS = ['en', 'uk', 'zh', 'fr']
const LANG_LABELS = { en: 'EN', uk: 'UK', zh: 'ZH', fr: 'FR' }
const PLATFORMS = ['youtube', 'tiktok', 'instagram']
const PLATFORM_LABELS = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram' }

export default function EpisodeScheduler({ episodeId, captions, onScheduled }) {
  const availableLangs = LANGS.filter((lang) =>
    PLATFORMS.some((plat) => captions.some((c) => c.language === lang && c.platform === plat))
  )

  const [selectedLangs, setSelectedLangs] = useState(new Set(availableLangs))
  const [selectedPlatforms, setSelectedPlatforms] = useState(new Set(PLATFORMS))
  const [date, setDate] = useState('')
  const [slots, setSlots] = useState([])
  const [scheduling, setScheduling] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const toggleLang = (lang) => {
    setSelectedLangs((prev) => {
      const next = new Set(prev)
      next.has(lang) ? next.delete(lang) : next.add(lang)
      return next
    })
  }

  const togglePlatform = (plat) => {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev)
      next.has(plat) ? next.delete(plat) : next.add(plat)
      return next
    })
  }

  const handleDateChange = async (e) => {
    const val = e.target.value
    setDate(val)
    setSlots([])
    if (!val) return
    try {
      const data = await getSlots(val)
      setSlots(data.slots)
    } catch {
      // preview is best-effort
    }
  }

  const handleSchedule = async () => {
    if (!date || selectedLangs.size === 0 || selectedPlatforms.size === 0) return
    setScheduling(true)
    setError(null)
    setResult(null)
    try {
      const data = await createSchedule({
        episodeId,
        date,
        languages: [...selectedLangs],
        platforms: [...selectedPlatforms],
      })
      setResult(data)
      if (data.created > 0) onScheduled()
    } catch (err) {
      const msg = err.data?.detail ?? err.message
      setError(msg)
    } finally {
      setScheduling(false)
    }
  }

  const visibleSlots = slots.filter((s) => selectedLangs.has(s.language))

  return (
    <div className="scheduler">
      <h2 className="scheduler-title">Schedule posts</h2>

      <div className="scheduler-toggles">
        <div className="toggle-group">
          {LANGS.map((lang) => (
            <button
              key={lang}
              className={`chip${selectedLangs.has(lang) ? ' on' : ''}`}
              onClick={() => toggleLang(lang)}
              disabled={!availableLangs.includes(lang)}
            >
              {LANG_LABELS[lang]}
            </button>
          ))}
        </div>
        <div className="toggle-group">
          {PLATFORMS.map((plat) => (
            <button
              key={plat}
              className={`chip${selectedPlatforms.has(plat) ? ' on' : ''}`}
              onClick={() => togglePlatform(plat)}
            >
              {PLATFORM_LABELS[plat]}
            </button>
          ))}
        </div>
      </div>

      <div className="scheduler-date">
        <label htmlFor="schedule-date" className="date-label">
          Post date
        </label>
        <input
          id="schedule-date"
          type="date"
          className="date-input"
          value={date}
          onChange={handleDateChange}
        />
      </div>

      {visibleSlots.length > 0 && (
        <div className="slot-preview">
          {visibleSlots.map((s) => (
            <div key={s.language} className="slot-row">
              <span className="slot-lang">{s.language.toUpperCase()}</span>
              <span className="slot-time">
                {s.audience_time} {s.audience_tz} → {s.your_time} {s.your_tz}
              </span>
            </div>
          ))}
        </div>
      )}

      {error && <div className="scheduler-error">{error}</div>}

      {result && result.warnings?.length > 0 && (
        <div className="scheduler-warnings">
          {result.warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <button
        className="schedule-btn"
        onClick={handleSchedule}
        disabled={scheduling || !date || selectedLangs.size === 0}
      >
        {scheduling ? 'Scheduling…' : 'Schedule selected'}
      </button>
    </div>
  )
}
