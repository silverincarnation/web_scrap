import { type ScraperResult, type ScrapedEvent } from './types'
import { extractEventData } from './extractors'

const PROXY_URLS = [
  'https://api.allorigins.win/raw?url=',
  'https://corsproxy.io/?',
]

function encodeUrl(url: string): string {
  return `${PROXY_URLS[0]}${encodeURIComponent(url)}`
}

export async function scrapeUrl(url: string): Promise<ScraperResult> {
  let cleanUrl = url.trim()
  if (!/^https?:\/\//i.test(cleanUrl)) {
    cleanUrl = 'https://' + cleanUrl
  }

  try {
    new URL(cleanUrl)
  } catch {
    return { success: false, error: 'Invalid URL provided', source: 'generic' }
  }

  const proxyUrl = encodeUrl(cleanUrl)

  let html: string
  try {
    const res = await fetch(proxyUrl, {
      signal: AbortSignal.timeout(15000),
    })
    if (!res.ok) {
      return {
        success: false,
        error: `Failed to fetch page (HTTP ${res.status})`,
        source: 'generic',
      }
    }
    html = await res.text()
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Failed to fetch page',
      source: 'generic',
    }
  }

  return extractEventData(html, cleanUrl)
}

export function fillEventData(
  scraped: ScrapedEvent,
  current: ScrapedEvent
): ScrapedEvent {
  return {
    title: scraped.title || current.title,
    date: scraped.date || current.date,
    time: scraped.time || current.time,
    location: scraped.location || current.location,
    description: scraped.description || current.description,
    image: scraped.image || current.image,
  }
}
