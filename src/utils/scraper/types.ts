/**
 * types.ts - Type Definitions for Event Scraper
 * 
 * Defines all TypeScript interfaces used throughout the scraper system:
 * - ScrapedEvent: Normalized event data structure
 * - ExtractionRule: CSS selector rules for site-specific extraction
 * - SiteConfig: Configuration for known event platforms
 * - ScraperResult: Result of a scrape operation
 * - ApiConfig: API endpoint configuration
 */

export interface ScrapedEvent {
  title: string
  date: string
  time: string
  location: string
  description: string
  image: string
  url?: string
}

export interface ExtractionRule {
  selector: string
  attribute?: string
  transform?: (value: string) => string
}

export interface SiteConfig {
  name: string
  domains: string[]
  rules: Partial<Record<keyof ScrapedEvent, ExtractionRule>>
}

export interface ScraperResult {
  success: boolean
  data?: ScrapedEvent
  error?: string
  source: 'jsonld' | 'microdata' | 'site-config' | 'generic'
}

export interface ApiConfig {
  endpoint: string
  method?: 'POST' | 'PUT'
  headers?: Record<string, string>
}
