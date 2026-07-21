/**
 * siteConfigs.ts - Site-Specific Extraction Configurations
 * 
 * Contains CSS selector rules for extracting event data from known platforms:
 * - Eventbrite
 * - Meetup
 * - Luma
 * - Partiful
 * 
 * Extend this file to add support for new event platforms.
 */

import { type SiteConfig } from './types'

export const siteConfigs: SiteConfig[] = [
  {
    name: 'Eventbrite',
    domains: ['eventbrite.com', 'www.eventbrite.com'],
    rules: {
      title: { selector: 'h1[data-event-title]', attribute: 'data-event-title' },
      date: { selector: '[data-event-date]', attribute: 'data-event-date' },
      time: { selector: '.event-details__time' },
      location: { selector: '.event-details__location' },
      description: { selector: '.event-description' },
      image: { selector: 'meta[property="og:image"]', attribute: 'content' },
    },
  },
  {
    name: 'Meetup',
    domains: ['meetup.com', 'www.meetup.com'],
    rules: {
      title: { selector: 'h1' },
      date: { selector: 'time[datetime]', attribute: 'datetime', transform: (v) => new Date(v).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) },
      time: { selector: 'time[datetime]', attribute: 'datetime', transform: (v) => {
        const d = new Date(v)
        return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
      }},
      location: { selector: '.venueDisplay-venue-address' },
      description: { selector: '.event-description' },
      image: { selector: 'meta[property="og:image"]', attribute: 'content' },
    },
  },
  {
    name: 'Luma',
    domains: ['lu.ma', 'luma.com'],
    rules: {
      title: { selector: 'h1' },
      date: { selector: '[data-testid="event-date"]' },
      time: { selector: '[data-testid="event-time"]' },
      location: { selector: '[data-testid="event-location"]' },
      description: { selector: '[data-testid="event-description"]' },
      image: { selector: 'meta[property="og:image"]', attribute: 'content' },
    },
  },
  {
    name: 'Partiful',
    domains: ['partiful.com', 'www.partiful.com'],
    rules: {
      title: { selector: 'h1' },
      date: { selector: '.event-date' },
      time: { selector: '.event-time' },
      location: { selector: '.event-location' },
      description: { selector: '.event-description' },
      image: { selector: 'meta[property="og:image"]', attribute: 'content' },
    },
  },
]

export function findSiteConfig(url: string): SiteConfig | undefined {
  const hostname = new URL(url).hostname
  return siteConfigs.find((c) => c.domains.some((d) => hostname === d || hostname.endsWith('.' + d)))
}
