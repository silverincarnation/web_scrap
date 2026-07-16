import { type ScrapedEvent, type ScraperResult, type SiteConfig } from './types'
import { findSiteConfig } from './siteConfigs'

function extractJsonLd(doc: Document): ScrapedEvent | null {
  const scripts = doc.querySelectorAll('script[type="application/ld+json"]')
  for (const script of scripts) {
    try {
      const data = JSON.parse(script.textContent || '')

      const items = data['@graph'] || [data]
      for (const item of items) {
        if (item['@type'] === 'Event' || item['@type']?.includes('Event')) {
          return {
            title: item.name || '',
            date: formatDate(item.startDate || item.date || ''),
            time: formatTimeFromISO(item.startDate || ''),
            location: extractLocation(item.location),
            description: item.description || '',
            image: extractImage(item.image),
          }
        }
      }
    } catch {}
  }
  return null
}

function extractMicrodata(doc: Document): ScrapedEvent | null {
  const item = doc.querySelector('[itemtype*="Event"]')
  if (!item) return null

  const getProp = (prop: string): string => {
    const el = item.querySelector(`[itemprop="${prop}"]`)
    if (!el) return ''
    return el.getAttribute('content') || el.textContent?.trim() || ''
  }

  return {
    title: getProp('name'),
    date: formatDate(getProp('startDate')),
    time: formatTimeFromISO(getProp('startDate')),
    location: extractMicrodataLocation(item),
    description: getProp('description'),
    image: getProp('image'),
  }
}

function extractMicrodataLocation(item: Element): string {
  const locationEl = item.querySelector('[itemprop="location"]')
  if (!locationEl) return ''
  const name = locationEl.querySelector('[itemprop="name"]')?.textContent?.trim() || ''
  const address = locationEl.querySelector('[itemprop="address"]')?.textContent?.trim() || ''
  return [name, address].filter(Boolean).join(', ')
}

function extractFromMeta(doc: Document): Partial<ScrapedEvent> {
  const getMeta = (prop: string): string => {
    const el =
      doc.querySelector(`meta[property="${prop}"]`) ||
      doc.querySelector(`meta[name="${prop}"]`)
    return el?.getAttribute('content')?.trim() || ''
  }

  return {
    title: getMeta('og:title') || doc.title || '',
    description: getMeta('og:description') || getMeta('description') || '',
    image: getMeta('og:image') || '',
  }
}

function extractGeneric(doc: Document): Partial<ScrapedEvent> {
  const text = doc.body?.textContent || ''

  const data: Partial<ScrapedEvent> = {}

  data.title =
    doc.querySelector('h1')?.textContent?.trim() ||
    doc.querySelector('h2')?.textContent?.trim() ||
    ''

  const datePatterns = [
    /\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b/gi,
    /\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/g,
  ]
  for (const pattern of datePatterns) {
    const match = text.match(pattern)
    if (match) {
      data.date = match[0]
      break
    }
  }

  const timePatterns = [
    /\b\d{1,2}:\d{2}\s*(?:AM|PM)\s*[-–to]+\s*\d{1,2}:\d{2}\s*(?:AM|PM)\b/gi,
    /\b\d{1,2}:\d{2}\s*(?:AM|PM)\b/gi,
  ]
  for (const pattern of timePatterns) {
    const match = text.match(pattern)
    if (match) {
      data.time = match[0]
      break
    }
  }

  return data
}

function extractWithConfig(doc: Document, config: SiteConfig): Partial<ScrapedEvent> {
  const data: Partial<ScrapedEvent> = {}

  for (const [field, rule] of Object.entries(config.rules)) {
    const el = doc.querySelector(rule.selector)
    if (!el) continue

    let value = rule.attribute
      ? el.getAttribute(rule.attribute) || ''
      : el.textContent?.trim() || ''

    if (rule.transform) {
      value = rule.transform(value)
    }

    if (value) {
      (data as any)[field] = value
    }
  }

  return data
}

function extractLocation(loc: any): string {
  if (!loc) return ''
  if (typeof loc === 'string') return loc
  const name = loc.name || ''
  const address =
    loc.address?.streetAddress ||
    loc.address?.addressLocality ||
    loc.address?.addressRegion ||
    ''
  return [name, address].filter(Boolean).join(', ')
}

function extractImage(img: any): string {
  if (!img) return ''
  if (typeof img === 'string') return img
  if (Array.isArray(img)) return img[0] || ''
  return img.url || ''
}

function formatDate(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}

function formatTimeFromISO(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export async function extractEventData(html: string, url: string): Promise<ScraperResult> {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')

  const jsonld = extractJsonLd(doc)
  if (jsonld && jsonld.title) {
    return { success: true, data: jsonld, source: 'jsonld' }
  }

  const microdata = extractMicrodata(doc)
  if (microdata && microdata.title) {
    return { success: true, data: microdata, source: 'microdata' }
  }

  const config = findSiteConfig(url)
  if (config) {
    const configData = extractWithConfig(doc, config)
    const meta = extractFromMeta(doc)
    const data: ScrapedEvent = {
      title: configData.title || meta.title || '',
      date: configData.date || '',
      time: configData.time || '',
      location: configData.location || '',
      description: configData.description || meta.description || '',
      image: configData.image || meta.image || '',
    }
    if (data.title) {
      return { success: true, data, source: 'site-config' }
    }
  }

  const meta = extractFromMeta(doc)
  const generic = extractGeneric(doc)
  const data: ScrapedEvent = {
    title: meta.title || generic.title || '',
    date: generic.date || '',
    time: generic.time || '',
    location: generic.location || '',
    description: meta.description || generic.description || '',
    image: meta.image || generic.image || '',
  }

  return {
    success: !!data.title,
    data: data.title ? data : undefined,
    error: data.title ? undefined : 'Could not extract event data from this page',
    source: 'generic',
  }
}
