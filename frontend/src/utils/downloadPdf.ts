import api from '../api/client'

export async function downloadPdf(url: string, filename: string) {
  const response = await api.get(url, { responseType: 'blob' })
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}
