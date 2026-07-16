import { useState } from 'react'
import { type EventData } from '../utils/eventData'
import './ShareCard.css'

interface ShareCardProps {
  eventData: EventData
  id?: string
  variant?: 'post' | 'story'
}

export function ShareCard({ eventData, id, variant = 'post' }: ShareCardProps) {
  const { title, date, time, location, description, image } = eventData
  const isStory = variant === 'story'
  const [imgError, setImgError] = useState(false)
  const showImage = image && !imgError

  return (
    <div
      id={id}
      className={`share-card ${isStory ? 'story' : 'post'}`}
    >
      <div className="card-background" />
      <div className="card-gradient" />

      {showImage && (
        <div className="card-image-container">
          <img
            src={image}
            alt={title}
            className="card-image"
            onError={() => setImgError(true)}
            crossOrigin="anonymous"
          />
          <div className="card-image-overlay" />
        </div>
      )}

      <div className="card-content">
        <div className="card-header">
          <div className="card-logo">
            <img src="/favicon.png" alt="Busco" className="card-logo-img" />
            <span className="card-brand">Busco</span>
          </div>
        </div>

        <div className="card-body">
          <h2 className="card-title">{title || 'Event Title'}</h2>

          {(date || time || location) && (
            <div className="card-details">
              {date && (
                <div className="card-detail">
                  <svg className="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  <span>{date}</span>
                </div>
              )}
              {time && (
                <div className="card-detail">
                  <svg className="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span>{time}</span>
                </div>
              )}
              {location && (
                <div className="card-detail">
                  <svg className="detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                  <span>{location}</span>
                </div>
              )}
            </div>
          )}

          {description && <p className="card-description">{description}</p>}
        </div>

        <div className="card-footer">
          <div className="qr-code">
            <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="5" y="5" width="25" height="25" rx="2" fill="white" />
              <rect x="8" y="8" width="19" height="19" rx="1" fill="black" />
              <rect x="11" y="11" width="13" height="13" rx="1" fill="white" />

              <rect x="70" y="5" width="25" height="25" rx="2" fill="white" />
              <rect x="73" y="8" width="19" height="19" rx="1" fill="black" />
              <rect x="76" y="11" width="13" height="13" rx="1" fill="white" />

              <rect x="5" y="70" width="25" height="25" rx="2" fill="white" />
              <rect x="8" y="73" width="19" height="19" rx="1" fill="black" />
              <rect x="11" y="76" width="13" height="13" rx="1" fill="white" />

              <rect x="35" y="5" width="8" height="8" fill="white" />
              <rect x="50" y="5" width="8" height="8" fill="white" />
              <rect x="35" y="20" width="8" height="8" fill="white" />
              <rect x="35" y="35" width="8" height="8" fill="white" />
              <rect x="50" y="35" width="8" height="8" fill="white" />
              <rect x="65" y="35" width="8" height="8" fill="white" />

              <rect x="5" y="35" width="8" height="8" fill="white" />
              <rect x="5" y="50" width="8" height="8" fill="white" />
              <rect x="20" y="35" width="8" height="8" fill="white" />

              <rect x="35" y="50" width="8" height="8" fill="white" />
              <rect x="50" y="50" width="8" height="8" fill="white" />
              <rect x="65" y="50" width="8" height="8" fill="white" />
              <rect x="80" y="50" width="8" height="8" fill="white" />

              <rect x="35" y="65" width="8" height="8" fill="white" />
              <rect x="50" y="65" width="8" height="8" fill="white" />
              <rect x="65" y="65" width="8" height="8" fill="white" />
              <rect x="80" y="65" width="8" height="8" fill="white" />

              <rect x="35" y="80" width="8" height="8" fill="white" />
              <rect x="50" y="80" width="8" height="8" fill="white" />
              <rect x="65" y="80" width="8" height="8" fill="white" />
              <rect x="80" y="80" width="8" height="8" fill="white" />

              <rect x="70" y="70" width="8" height="8" fill="white" />
              <rect x="85" y="70" width="8" height="8" fill="white" />
              <rect x="70" y="85" width="8" height="8" fill="white" />
              <rect x="85" y="85" width="8" height="8" fill="white" />
            </svg>
          </div>
          <span className="card-footer-text">Scan to view on Busco</span>
        </div>
      </div>
    </div>
  )
}
