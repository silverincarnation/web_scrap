export interface EventData {
  title: string
  date: string
  time: string
  location: string
  description: string
  image: string
}

export function parseUrlParams(): EventData | null {
  const params = new URLSearchParams(window.location.search)
  const title = params.get('title')
  const date = params.get('date')
  const time = params.get('time')
  const location = params.get('location')
  const description = params.get('description')
  const image = params.get('image')

  if (!title) return null

  return {
    title: decodeURIComponent(title),
    date: decodeURIComponent(date || ''),
    time: decodeURIComponent(time || ''),
    location: decodeURIComponent(location || ''),
    description: decodeURIComponent(description || ''),
    image: decodeURIComponent(image || ''),
  }
}

export function formatUrlParams(data: EventData): string {
  const params = new URLSearchParams()
  if (data.title) params.set('title', encodeURIComponent(data.title))
  if (data.date) params.set('date', encodeURIComponent(data.date))
  if (data.time) params.set('time', encodeURIComponent(data.time))
  if (data.location) params.set('location', encodeURIComponent(data.location))
  if (data.description) params.set('description', encodeURIComponent(data.description))
  if (data.image) params.set('image', encodeURIComponent(data.image))
  return params.toString()
}
