import { type EventData } from '../utils/eventData'
import './FormInputs.css'

interface FormInputsProps {
  eventData: EventData
  onChange: (data: EventData) => void
}

export function FormInputs({ eventData, onChange }: FormInputsProps) {
  const handleChange = (field: keyof EventData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    onChange({ ...eventData, [field]: e.target.value })
  }

  return (
    <div className="form-container">
      <h3 className="form-title">Event Details</h3>

      <div className="form-group">
        <label htmlFor="event-title">Event Title</label>
        <input
          id="event-title"
          type="text"
          placeholder="e.g. Food Truck Friday"
          value={eventData.title}
          onChange={handleChange('title')}
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="event-date">Date</label>
          <input
            id="event-date"
            type="text"
            placeholder="e.g. Saturday, Dec 15"
            value={eventData.date}
            onChange={handleChange('date')}
          />
        </div>

        <div className="form-group">
          <label htmlFor="event-time">Time</label>
          <input
            id="event-time"
            type="text"
            placeholder="e.g. 6:00 PM - 10:00 PM"
            value={eventData.time}
            onChange={handleChange('time')}
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="event-location">Location</label>
        <input
          id="event-location"
          type="text"
          placeholder="e.g. Mercado Roma, CDMX"
          value={eventData.location}
          onChange={handleChange('location')}
        />
      </div>

      <div className="form-group">
        <label htmlFor="event-description">Description</label>
        <textarea
          id="event-description"
          placeholder="Brief description of the event..."
          value={eventData.description}
          onChange={handleChange('description')}
          rows={3}
        />
      </div>

      <div className="form-group">
        <label htmlFor="event-image">Image URL</label>
        <input
          id="event-image"
          type="text"
          placeholder="https://example.com/event-image.jpg"
          value={eventData.image}
          onChange={handleChange('image')}
        />
      </div>
    </div>
  )
}
