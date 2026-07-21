/**
 * apiClient.ts - API Client for Event Data
 * 
 * Handles sending processed event data to external APIs.
 * Supports POST and PUT methods with configurable endpoints.
 * 
 * Usage:
 *   import { configureApi, sendEvent } from './apiClient'
 *   configureApi({ endpoint: 'https://api.example.com/events' })
 *   await sendEvent(eventData)
 */

import { type ScrapedEvent, type ApiConfig } from './types'

export interface ApiResponse {
  success: boolean
  error?: string
  status?: number
}

const DEFAULT_CONFIG: ApiConfig = {
  endpoint: '/api/events',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
}

let apiConfig: ApiConfig = { ...DEFAULT_CONFIG }

export function configureApi(config: Partial<ApiConfig>): void {
  apiConfig = { ...DEFAULT_CONFIG, ...config }
}

export function getApiConfig(): ApiConfig {
  return { ...apiConfig }
}

export async function sendEvent(
  event: ScrapedEvent
): Promise<ApiResponse> {
  const { endpoint, method, headers } = apiConfig

  try {
    const res = await fetch(endpoint, {
      method: method || 'POST',
      headers,
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(10000),
    })

    if (!res.ok) {
      return {
        success: false,
        status: res.status,
        error: `API returned HTTP ${res.status}: ${res.statusText}`,
      }
    }

    return { success: true, status: res.status }
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Unknown API error',
    }
  }
}

export async function sendEvents(
  events: ScrapedEvent[]
): Promise<ApiResponse[]> {
  return Promise.all(events.map(sendEvent))
}
