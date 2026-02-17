import api from '../api/client'

export type ExportFormat = 'pdf' | 'xlsx'

const MIME_TYPES: Record<ExportFormat, string> = {
  pdf: 'application/pdf',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

export async function downloadFile(url: string, filename: string, format: ExportFormat = 'pdf') {
  const separator = url.includes('?') ? '&' : '?'
  const fullUrl = format === 'xlsx' ? `${url}${separator}export=xlsx` : url

  const response = await api.get(fullUrl, { responseType: 'blob' })
  const blob = new Blob([response.data], { type: MIME_TYPES[format] })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename.replace(/\.(pdf|xlsx)$/, '') + (format === 'xlsx' ? '.xlsx' : '.pdf')
  link.click()
  URL.revokeObjectURL(link.href)
}

export async function downloadPdf(url: string, filename: string) {
  return downloadFile(url, filename, 'pdf')
}
