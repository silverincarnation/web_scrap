import { useState, useEffect, useCallback } from 'react'
import { ShareCard } from './components/ShareCard'
import { FormInputs } from './components/FormInputs'
import { ExportButtons } from './components/ExportButtons'
import { ScraperPanel } from './components/ScraperPanel'
import { type EventData, parseUrlParams, formatUrlParams } from './utils/eventData'
import './App.css'

type Tab = 'create' | 'scraper'

function App() {
  const [eventData, setEventData] = useState<EventData>({
    title: 'Food Truck Friday',
    date: 'Saturday, Dec 15',
    time: '6:00 PM - 10:00 PM',
    location: 'Mercado Roma, CDMX',
    description: 'The best street food in town, live music, and good vibes.',
    image: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80',
  })

  const [showForm, setShowForm] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('create')

  useEffect(() => {
    const params = parseUrlParams()
    if (params) {
      setEventData(params)
    }
  }, [])

  const handleUpdateUrl = useCallback(() => {
    const newUrl = `${window.location.pathname}?${formatUrlParams(eventData)}`
    window.history.replaceState({}, '', newUrl)
  }, [eventData])

  const handleExportSuccess = useCallback(() => {
    handleUpdateUrl()
  }, [handleUpdateUrl])

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo-container">
          <img src="/favicon.png" alt="Busco" className="logo-icon" />
          <h1 className="app-title">Busco</h1>
        </div>
        <nav className="app-nav">
          <button
            className={`nav-tab ${activeTab === 'create' ? 'active' : ''}`}
            onClick={() => setActiveTab('create')}
          >
            Create Card
          </button>
          <button
            className={`nav-tab ${activeTab === 'scraper' ? 'active' : ''}`}
            onClick={() => setActiveTab('scraper')}
          >
            Scraper
          </button>
        </nav>
        {activeTab === 'create' && (
          <button className="share-btn" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Preview Card' : 'Edit Card'}
          </button>
        )}
      </header>

      <main className="app-main">
        <div className="app-content">
          {activeTab === 'create' && (
            <>
              <div className="card-preview">
                <ShareCard eventData={eventData} id="share-card" />
              </div>

              {showForm && (
                <div className="form-section">
                  <FormInputs eventData={eventData} onChange={setEventData} />
                </div>
              )}

              <ExportButtons eventData={eventData} onExport={handleExportSuccess} />
            </>
          )}

          {activeTab === 'scraper' && (
            <ScraperPanel
              onFillData={(data) => {
                setEventData(data)
                setActiveTab('create')
                setShowForm(true)
              }}
            />
          )}
        </div>
      </main>
    </div>
  )
}

export default App
