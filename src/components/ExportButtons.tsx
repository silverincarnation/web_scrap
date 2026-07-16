import { useState } from 'react'
import { type EventData } from '../utils/eventData'
import { downloadAsPng } from '../utils/exportImage'
import './ExportButtons.css'

interface ExportButtonsProps {
  eventData: EventData
  onExport: () => void
}

export function ExportButtons({ eventData, onExport }: ExportButtonsProps) {
  const [exporting, setExporting] = useState<string | null>(null)

  const handleExport = async (variant: 'post' | 'story') => {
    const formatName = variant === 'post' ? 'Post' : 'Story'
    setExporting(formatName)

    try {
      const filename = `busco-${eventData.title || 'event'}-${formatName.toLowerCase()}`
      await downloadAsPng('share-card', filename, 2)
      onExport()
    } catch (error) {
      console.error('Failed to export:', error)
    } finally {
      setExporting(null)
    }
  }

  const handleCopyLink = () => {
    const url = `${window.location.origin}${window.location.pathname}`
    navigator.clipboard.writeText(url).then(() => {
      alert('Link copied to clipboard!')
    })
  }

  return (
    <div className="export-buttons">
      <button
        className="export-btn primary"
        onClick={() => handleExport('post')}
        disabled={exporting !== null}
      >
        {exporting === 'Post' ? 'Generating...' : 'Download Post (4:5)'}
      </button>

      <button
        className="export-btn primary"
        onClick={() => handleExport('story')}
        disabled={exporting !== null}
      >
        {exporting === 'Story' ? 'Generating...' : 'Download Story (9:16)'}
      </button>

      <button className="export-btn secondary" onClick={handleCopyLink}>
        Copy Share Link
      </button>
    </div>
  )
}
