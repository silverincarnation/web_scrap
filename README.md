# Event Scraper Pipeline

An adaptive event scraper that works with multiple platforms and data sources, with both interactive web UI and automated batch processing capabilities.

## Overview

This project provides two ways to work with event data:

1. **Web UI** - Interactive scraping via browser with preview cards
2. **Batch Processing** - CLI and GitHub Actions for automated processing

## Features

- **Adaptive Scraping**: Automatically extracts data from Eventbrite, Meetup, Luma, Partiful, and more
- **Multiple Extraction Strategies**:
  - JSON-LD structured data (most reliable)
  - Microdata markup
  - Site-specific CSS selectors
  - Generic fallback (meta tags, regex patterns)
- **Batch Processing**: Process hundreds of events from CSV files
- **Special Character Cleaning**: Automatically removes problematic characters from titles and descriptions
- **API Integration**: Send processed events to any REST API
- **GitHub Actions**: Automated pipeline for continuous processing

## Quick Start

### Web UI (Interactive)

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser at http://localhost:5173
# Click "Scraper" tab, paste an event URL, and click "Scrape"
```

### Batch Processing (CLI)

```bash
# Process zip files containing event data
npx tsx scripts/process-events.ts .

# Process CSV files from a specific folder
npx tsx scripts/process-events.ts eventbrite/sample

# Process with output directory
npx tsx scripts/process-events.ts eventbrite/sample --output ./output

# Process and send to API
npx tsx scripts/process-events.ts eventbrite/sample --api https://api.example.com/events
```

### Using npm scripts

```bash
# Process zip files in current directory
npm run process-events -- .

# Process CSV files from a folder
npm run process-events -- eventbrite/sample
```

## Data Format

### Input CSV Structure

The scraper expects CSV files with these columns (flexible naming):

| Column | Alternative Names | Description |
|--------|-------------------|-------------|
| `name` | `title`, `event_name`, `event` | Event title |
| `start_time` | `start_date`, `date` | Event start date/time (ISO format) |
| `end_time` | `end_date` | Event end date/time (ISO format) |
| `location_name` | `venue`, `location`, `place` | Venue name |
| `address` | `address_line`, `street` | Street address |
| `city` | `town`, `locality` | City name |
| `description` | `details`, `event_description` | Event description |
| `thumbnail_image` | `image`, `image_url`, `photo` | Image URL |
| `external_link` | `url`, `link`, `event_url` | Event page URL |

### Output JSON Structure

```json
{
  "title": "Event Name",
  "date": "Tuesday, July 21, 2026",
  "time": "6:00 PM",
  "location": "Venue Name, 123 Street, City",
  "description": "Event description...",
  "image": "https://...",
  "url": "https://..."
}
```

## Automated Processing (GitHub Actions)

The pipeline automatically processes event data when:

1. **Zip files are pushed** to the repository
2. **Manually triggered** via workflow_dispatch

### Setting up GitHub Actions

1. **API Endpoint** (optional): Add repository secret `API_ENDPOINT`

2. **Push a zip file**:
   ```bash
   # Create zip with your event data
   zip -r events.zip eventbrite/sample/
   
   # Push to GitHub
   git add events.zip
   git commit -m "Add new event data"
   git push
   ```

3. **Manual trigger**:
   - Go to Actions → Process Events
   - Click "Run workflow"
   - Select city to process

### Workflow Steps

1. **Checkout** repository
2. **Setup Node.js** and install dependencies
3. **Extract zip files** (if present)
4. **Process CSV files**:
   - Parse and normalize data
   - Clean special characters
   - Format dates/times
   - Combine location fields
5. **Send to API** (if configured)
6. **Upload artifact** with processed JSON

## Project Structure

```
share_card_maker/
├── scripts/
│   ├── process-events.ts    # CLI entry point
│   └── batch.ts             # Batch processing logic
├── src/
│   └── utils/
│       └── scraper/
│           ├── index.ts     # Module exports
│           ├── types.ts     # TypeScript interfaces
│           ├── scraperEngine.ts  # Core scraper logic
│           ├── extractors.ts     # Data extraction strategies
│           ├── siteConfigs.ts    # Platform-specific configs
│           └── apiClient.ts      # API integration
├── .github/
│   └── workflows/
│       └── process-events.yml  # GitHub Actions workflow
└── package.json
```

## Adding Support for New Platforms

1. Edit `src/utils/scraper/siteConfigs.ts`
2. Add a new configuration object:

```typescript
{
  name: 'NewPlatform',
  domains: ['newplatform.com', 'www.newplatform.com'],
  rules: {
    title: { selector: '.event-title' },
    date: { selector: '.event-date' },
    time: { selector: '.event-time' },
    location: { selector: '.event-location' },
    description: { selector: '.event-description' },
    image: { selector: 'meta[property="og:image"]', attribute: 'content' },
  },
}
```

3. The scraper will automatically use these rules when processing URLs from that domain.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ENDPOINT` | URL to send processed events | `/api/events` |

## License

MIT
