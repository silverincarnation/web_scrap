import { existsSync, mkdirSync, readdirSync } from 'fs'
import { join } from 'path'
import { execSync } from 'child_process'
import { processDirectory } from './batch'

const EXTRACT_DIR = '/tmp/extracted-events'
const API_ENDPOINT = process.env.API_ENDPOINT || ''

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
  const rootDir = process.argv[2] || '.'

  if (!existsSync(rootDir)) {
    console.error(`Directory not found: ${rootDir}`)
    process.exit(1)
  }

  console.log(`Scanning ${rootDir} for zip files...`)
  const extractDirs = await extractZips(rootDir)

  if (extractDirs.length === 0) {
    console.log('No zip files found.')
    return
  }

  for (const dir of extractDirs) {
    console.log(`\nProcessing ${dir}...`)
    await processDirectory({
      inputDir: dir,
      outputDir: join(dir, 'output'),
      apiConfig: API_ENDPOINT
        ? {
            endpoint: API_ENDPOINT,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        : undefined,
    })
  }
}

main().catch((err) => {
  console.error('Fatal:', err)
  process.exit(1)
})
