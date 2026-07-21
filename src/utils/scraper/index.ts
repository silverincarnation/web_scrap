/**
 * index.ts - Scraper Module Entry Point
 * 
 * Re-exports all public types and functions from the scraper system.
 * Use this as the main import for the scraper library.
 * 
 * Usage:
 *   import { scrapeUrl, sendEvent, configureApi } from './utils/scraper'
 */

export type { ScrapedEvent, ScraperResult, SiteConfig, ExtractionRule, ApiConfig } from './types'
export { scrapeUrl, fillEventData } from './scraperEngine'
export { configureApi, getApiConfig, sendEvent, sendEvents } from './apiClient'
export type { ApiResponse } from './apiClient'
export { siteConfigs, findSiteConfig } from './siteConfigs'

