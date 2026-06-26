import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getCaptions, getVideo, importCaptions } from '../api.js'
import CaptionGrid from '../components/CaptionGrid.jsx'
import './Episode.css'

export default function Episode() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [episode, setEpisode] = useState(null)
  const [captions, setCaptions] = useState([])
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getVideo(id)
      .then(setEpisode)
      .catch((err) => setError(err.message))
    getCaptions(id)
      .then(setCaptions)
      .catch(() => setCaptions([]))
  }, [id])

  const handleImport = async () => {
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importCaptions(id)
      setImportResult(result)
      if (!result.errors?.length) {
        const updated = await getCaptions(id)
        setCaptions(updated)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setImporting(false)
    }
  }

  if (error) return <div className="ep-error">{error}</div>
  if (!episode) return <div className="ep-loading">Loading…</div>

  return (
    <div className="episode-page">
      <div className="ep-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Library</button>
        <div>
          <div className="ep-eyebrow">Episode {episode.episode_num}</div>
          <h1 className="ep-title">{episode.name}</h1>
        </div>
        <button className="import-btn" onClick={handleImport} disabled={importing}>
          {importing ? 'Importing…' : 'Import descriptions'}
        </button>
      </div>

      {episode.primary_file && (
        <video
          className="ep-video"
          src={`/api/videos/${id}/stream`}
          controls
          preload="metadata"
        />
      )}

      {importResult && (
        <div className={`import-result ${importResult.errors?.length ? 'error' : 'ok'}`}>
          {importResult.errors?.length ? (
            importResult.errors.map((e, i) => <p key={i}>{e}</p>)
          ) : (
            <p>
              Imported {importResult.imported} descriptions.
              {importResult.warnings?.map((w, i) => (
                <span key={i}> · {w}</span>
              ))}
            </p>
          )}
        </div>
      )}

      <h2 className="ep-section-title">Publishing descriptions</h2>
      <CaptionGrid videoId={parseInt(id, 10)} captions={captions} />

      <div className="ep-footer">
        <button className="save-btn" onClick={() => navigate('/queue')}>
          Save &amp; continue to scheduling →
        </button>
      </div>
    </div>
  )
}
