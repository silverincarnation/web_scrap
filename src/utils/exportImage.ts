export async function downloadAsPng(elementId: string, filename: string, scale = 2) {
  const { toPng } = await import('html-to-image')
  const element = document.getElementById(elementId)
  if (!element) throw new Error(`Element with id "${elementId}" not found`)

  const dataUrl = await toPng(element, {
    quality: 1,
    pixelRatio: scale,
    cacheBust: true,
    style: {
      transform: 'none',
    },
  })

  const link = document.createElement('a')
  link.download = `${filename}.png`
  link.href = dataUrl
  link.click()
}
