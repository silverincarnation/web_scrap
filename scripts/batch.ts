/**
 * batch.ts - Batch Event Processing Script
 * 
 * Reads CSV files from a directory, normalizes event data, and optionally sends to API.
 * Handles special character removal from titles and descriptions.
 * 
 * Usage:
 *   npx tsx scripts/process-events.ts <input-dir> [--output <output-dir>] [--api <endpoint>]
 * 
 * Example:
 *   npx tsx scripts/process-events.ts eventbrite/sample
 *   npx tsx scripts/process-events.ts Mexico_City_MX --output ./output --api https://api.example.com/events
 */

import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'fs'
import { join, extname } from 'path'
import { type ScrapedEvent, type ApiConfig } from '../src/utils/scraper/types'
import { sendEvent } from '../src/utils/scraper/apiClient'

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === ',' && !inQuotes) {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

function parseCsv(content: string): Record<string, string>[] {
  const lines = content.split('\n').filter((l) => l.trim())
  if (lines.length < 2) return []

  const headers = parseCsvLine(lines[0])

  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line)
    const row: Record<string, string> = {}
    headers.forEach((h, i) => {
      row[h.trim()] = (values[i] || '').replace(/^"|"$/g, '')
    })
    return row
  })
}

const FIELD_MAP: Record<string, string[]> = {
  title: ['name', 'title', 'event_name', 'event'],
  date: ['date', 'start_date', 'event_date'],
  time: ['time', 'start_time', 'event_time'],
  location: ['location_name', 'venue', 'location', 'venue_name', 'place'],
  description: ['description', 'details', 'event_description', 'notes'],
  image: ['image', 'thumbnail_image', 'image_url', 'photo', 'img_url'],
}

function findValue(row: Record<string, string>, keys: string[]): string {
  for (const k of keys) {
    const v = row[k]
    if (v && v.trim()) return v.trim()
  }
  return ''
}

function hasTimeComponent(raw: string): boolean {
  return raw.includes('T') || raw.includes(' ') || /:\d{2}/.test(raw)
}

function needsTimezoneFix(raw: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(raw)
}

function normalizeDate(raw: string): string {
  if (!raw) return ''
  try {
    if (needsTimezoneFix(raw)) {
      const [y, m, d] = raw.split('-').map(Number)
      const date = new Date(y, m - 1, d)
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-US', {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          year: 'numeric',
          timeZone: 'UTC',
        })
      }
    }
    const dt = new Date(raw)
    if (!isNaN(dt.getTime())) {
      return dt.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    }
  } catch {}
  return raw
}

function normalizeTime(raw: string): string {
  if (!raw || !hasTimeComponent(raw)) return ''
  try {
    const d = new Date(raw)
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      })
    }
  } catch {}
  if (/^\d{1,2}:\d{2}\s*(?:AM|PM)/i.test(raw)) return raw
  if (/^\d{1,2}:\d{2}$/.test(raw)) return raw
  return ''
}

function cleanSpecialChars(text: string): string {
  if (!text) return ''
  return text
    .replace(/['']/g, "'")
    .replace(/[""]/g, '"')
    .replace(/[""]/g, '"')
    .replace(/[""]/g, '"')
    .replace(/['']/g, "'")
    .replace(/['']/g, "'")
    .replace(/[&]/g, 'and')
    .replace(/[@#%]/g, '')
    .replace(/[^\w\s\-.,!?:;()\/]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function csvRowToEvent(row: Record<string, string>): ScrapedEvent {
  const rawDate = findValue(row, ['start_time', 'start_date', 'date'])
  const rawTime = findValue(row, ['start_time', 'time'])
  const rawEndTime = findValue(row, ['end_time', 'end_date'])
  const rawEndDate = findValue(row, ['end_date'])

  let date = normalizeDate(rawDate)

  let time = ''
  if (hasTimeComponent(rawTime) || hasTimeComponent(rawDate)) {
    time = normalizeTime(rawTime || rawDate)
  }

  if (rawEndTime && hasTimeComponent(rawEndTime)) {
    const endTime = normalizeTime(rawEndTime)
    if (time && endTime && !time.includes(':')) {
      time = `${time} - ${endTime}`
    } else if (time && endTime) {
      time = `${time} - ${endTime}`
    }
  }

  if (rawEndDate && needsTimezoneFix(rawEndDate) && needsTimezoneFix(rawDate) && rawEndDate !== rawDate) {
    const endFormatted = normalizeDate(rawEndDate)
    if (endFormatted && date && endFormatted !== date) {
      date = `${date} – ${endFormatted}`
    }
  }

  const address = findValue(row, ['address', 'address_line', 'street'])
  const city = findValue(row, ['city', 'town', 'locality'])

  let location = findValue(row, FIELD_MAP.location)
  if (address && !location.includes(address)) {
    location = [location, address, city].filter(Boolean).join(', ')
  } else if (city && !location.includes(city)) {
    location = [location, city].filter(Boolean).join(', ')
  }

  const image = findValue(row, FIELD_MAP.image)
  const externalLink = findValue(row, ['external_link', 'url', 'link', 'event_url'])

  return {
    title: cleanSpecialChars(findValue(row, FIELD_MAP.title)) || 'Untitled Event',
    date,
    time,
    location,
    description: cleanSpecialChars(findValue(row, FIELD_MAP.description)),
    image: image || '',
    url: externalLink,
  }
}

export interface BatchOptions {
  inputDir: string
  outputDir?: string
  apiConfig?: ApiConfig
}

export async function processDirectory(options: BatchOptions): Promise<ScrapedEvent[]> {
  const { inputDir, outputDir, apiConfig } = options

  if (!existsSync(inputDir)) {
    throw new Error(`Input directory not found: ${inputDir}`)
  }

  const files = readdirSync(inputDir).filter(
    (f: string) => extname(f).toLowerCase() === '.csv'
  )

  if (files.length === 0) {
    console.warn(`No CSV files found in ${inputDir}`)
    return []
  }

  const allEvents: ScrapedEvent[] = []

  for (const file of files) {
    const filePath = join(inputDir, file)
    console.log(`Reading ${filePath}...`)
    const content = readFileSync(filePath, 'utf-8')
    const rows = parseCsv(content)
    console.log(`  Found ${rows.length} rows`)

    for (const row of rows) {
      allEvents.push(csvRowToEvent(row))
    }
  }

  if (apiConfig && allEvents.length > 0) {
    console.log(`Sending ${allEvents.length} events to API...`)
    for (const event of allEvents) {
      try {
        const res = await sendEvent(event)
        console.log(`  "${event.title}" → ${res.success ? 'OK' : `FAIL: ${res.error}`}`)
      } catch (err) {
        console.error(`  "${event.title}" → ERROR: ${err}`)
      }
    }
  }

  if (outputDir) {
    if (!existsSync(outputDir)) {
      mkdirSync(outputDir, { recursive: true })
    }
    const outPath = join(outputDir, 'events.json')
    writeFileSync(outPath, JSON.stringify(allEvents, null, 2), 'utf-8')
    console.log(`Written to ${outPath}`)
  }

  console.log(`Processed ${allEvents.length} events total`)
  return allEvents
}

export async function processZipContents(
  extractDir: string,
  apiEndpoint?: string
): Promise<ScrapedEvent[]> {
  const apiConfig = apiEndpoint
    ? {
        endpoint: apiEndpoint,
        method: 'POST' as const,
        headers: { 'Content-Type': 'application/json' },
      }
    : undefined

  return processDirectory({
    inputDir: extractDir,
    apiConfig,
  })
}
