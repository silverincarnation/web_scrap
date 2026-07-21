/**
 * process-events.ts - Event Data Processing CLI
 * 
 * Extracts zip files and processes event data from CSV files.
 * Can be run manually or triggered by GitHub Actions.
 * 
 * Usage:
 *   npx tsx scripts/process-events.ts <input> [options]
 * 
 * Arguments:
 *   <input>              Directory containing zip files or CSV files
 * 
 * Options:
 *   --output, -o <dir>   Output directory for processed JSON (default: /tmp/output)
 *   --api, -a <url>      API endpoint to send processed events
 * 
 * Examples:
 *   # Process zip files in current directory
 *   npx tsx scripts/process-events.ts .
 * 
 *   # Process CSV files from a specific folder
 *   npx tsx scripts/process-events.ts eventbrite/sample
 * 
 *   # Process with output directory and API
 *   npx tsx scripts/process-events.ts Mexico_City_MX --output ./output --api https://api.example.com/events
 */

import { existsSync, mkdirSync, readdirSync } from 'fs'
import { join } from 'path'
import { execSync } from 'child_process'
import { processDirectory } from './batch'

const EXTRACT_DIR = '/tmp/extracted-events'

interface CliOptions {
  inputDir: string
  outputDir: string
  apiEndpoint: string
}

function parseArgs(): CliOptions {
  const args = process.argv.slice(2)
  let inputDir = '.'
  let outputDir = '/tmp/output'
  let apiEndpoint = process.env.API_ENDPOINT || ''

  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (arg === '--output' || arg === '-o') {
      outputDir = args[++i] || outputDir
    } else if (arg === '--api' || arg === '-a') {
      apiEndpoint = args[++i] || apiEndpoint
    } else if (!arg.startsWith('-')) {
      inputDir = arg
    }
  }

  return { inputDir, outputDir, apiEndpoint }
}

async function extractZips(rootDir: string): Promise<string[]> {
  const extracted: string[] = []

  const entries = readdirSync(rootDir)
  for (const entry of entries) {
    if (!entry.endsWith('.zip')) continue
    const zipPath = join(rootDir, entry)
    const name = entry.replace('.zip', '')
    const outDir = join(EXTRACT_DIR, name)

    if (!existsSync(outDir)) {
      mkdirSync(outDir, { recursive: true })
    }

    try {
      execSync(`unzip -o "${zipPath}" -d "${outDir}"`, { stdio: 'pipe' })
      console.log(`Extracted ${entry} → ${outDir}`)
      extracted.push(outDir)
    } catch (err) {
      console.error(`Failed to extract ${entry}:`, err)
    }
  }

  return extracted
}

async function main() {
  const options = parseArgs()

  if (!existsSync(options.inputDir)) {
    console.error(`Directory not found: ${options.inputDir}`)
    process.exit(1)
  }

  // Check if input contains zip files
  const entries = readdirSync(options.inputDir)
  const hasZips = entries.some((e) => e.endsWith('.zip'))

  let dirsToProcess: string[] = []

  if (hasZips) {
    console.log(`Scanning ${options.inputDir} for zip files...`)
    dirsToProcess = await extractZips(options.inputDir)

    if (dirsToProcess.length === 0) {
      console.log('No zip files found.')
      return
    }
  } else {
    // Check if directory contains CSV files
    const csvFiles = entries.filter((e) => e.endsWith('.csv'))
    if (csvFiles.length === 0) {
      console.error(`No zip or CSV files found in ${options.inputDir}`)
      process.exit(1)
    }
    dirsToProcess = [options.inputDir]
  }

  for (const dir of dirsToProcess) {
    console.log(`\nProcessing ${dir}...`)
    await processDirectory({
      inputDir: dir,
      outputDir: options.outputDir,
      apiConfig: options.apiEndpoint
        ? {
            endpoint: options.apiEndpoint,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        : undefined,
    })
  }

  console.log('\nDone!')
}

main().catch((err) => {
  console.error('Fatal:', err)
  process.exit(1)
})
