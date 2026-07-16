import { useState } from 'react'
import { type EventData } from '../utils/eventData'
import { scrapeUrl, sendEvent, configureApi, getApiConfig } from '../utils/scraper'
import type { ScrapedEvent, ScraperResult } from '../utils/scraper'
import './ScraperPanel.css'

interface ScraperPanelProps {
  onFillData: (data: EventData) => void
}

export function ScraperPanel({ onFillData }: ScraperPanelProps) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScraperResult | null>(null)
  const [showApiConfig, setShowApiConfig] = useState(false)
  const [apiEndpoint, setApiEndpoint] = useState(getApiConfig().endpoint)
  const [sending, setSending] = useState(false)
  const [sendStatus, setSendStatus] = useState<string | null>(null)

  const handleScrape = async () => {
    if (!url.trim()) return
    setLoading(true)
    setResult(null)
    setSendStatus(null)

    const res = await scrapeUrl(url)
    setResult(res)
    setLoading(false)
  }

  const handleFillData = () => {
    if (!result?.data) return
    const e = result.data
    onFillData({
      title: e.title || '',
      date: e.date || '',
      time: e.time || '',
      location: e.location || '',
      description: e.description || '',
      image: e.image || '',
    })
  }

  const handleSendToApi = async () => {
    if (!result?.data) return
    setSending(true)
    setSendStatus(null)

    configureApi({ endpoint: apiEndpoint })
    const res = await sendEvent(result.data as ScrapedEvent)
    setSendStatus(res.success ? 'Event sent successfully!' : `Failed: ${res.error}`)
    setSending(false)
  }

  return (
    <div className="scraper-panel">
      <h3 className="scraper-title">Event Scraper</h3>
      <p className="scraper-subtitle">Paste any event page URL to extract its details</p>

      <div className="scraper-input-row">
        <input
          type="url"
          className="scraper-input"
          placeholder="https://eventbrite.com/e/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleScrape()}
        />
        <button
          className="scraper-btn"
          onClick={handleScrape}
          disabled={loading || !url.trim()}
        >
          {loading ? 'Scraping...' : 'Scrape'}
        </button>
      </div>

      {loading && (
        <div className="scraper-loading">
          <div className="scraper-spinner" />
          <span>Fetching and parsing event data...</span>
        </div>
      )}

      {result && !result.success && (
        <div className="scraper-error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="scraper-error-icon">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
          <span>{result.error}</span>
        </div>
      )}

      {result && result.success && result.data && (
        <>
          <div className="scraper-results">
            <div className="scraper-result-header">
              <span className="scraper-source-badge">{result.source}</span>
              <span className="scraper-result-label">Extracted Data</span>
            </div>
            <div className="scraper-fields">
              {[
                { label: 'Title', value: result.data.title },
                { label: 'Date', value: result.data.date },
                { label: 'Time', value: result.data.time },
                { label: 'Location', value: result.data.location },
                { label: 'Description', value: result.data.description },
                { label: 'Image', value: result.data.image, truncate: true },
              ].map((f) => (
                <div className="scraper-field" key={f.label}>
                  <span className="scraper-field-label">{f.label}</span>
                  <span className={`scraper-field-value ${f.value ? '' : 'empty'}`}>
                    {f.value || '(not found)'}
                  </span>
                </div>
              ))}
            </div>
            <div className="scraper-actions">
              <button className="scraper-btn primary" onClick={handleFillData}>
                Fill Card with This Data
              </button>
            </div>
          </div>

          <div className="scraper-api-section">
            <button
              className="scraper-api-toggle"
              onClick={() => setShowApiConfig(!showApiConfig)}
            >
              <span>Send to API</span>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className={`scraper-chevron ${showApiConfig ? 'open' : ''}`}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {showApiConfig && (
              <div className="scraper-api-config">
                <label className="scraper-api-label">API Endpoint</label>
                <input
                  type="url"
                  className="scraper-input"
                  value={apiEndpoint}
                  onChange={(e) => setApiEndpoint(e.target.value)}
                  placeholder="/api/events"
                />
                <button
                  className="scraper-btn"
                  onClick={handleSendToApi}
                  disabled={sending}
                >
                  {sending ? 'Sending...' : 'Send Event to API'}
                </button>
                {sendStatus && (
                  <div className={`scraper-send-status ${sendStatus.startsWith('Failed') ? 'error' : 'success'}`}>
                    {sendStatus}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
