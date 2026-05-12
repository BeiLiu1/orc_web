const API_BASE = import.meta.env.VITE_API_BASE || '/api'

function headers() {
  const token = localStorage.getItem('accessToken') || ''
  return token ? { 'x-access-token': token } : {}
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...headers(),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail || detail
    } catch {
      // Keep status text.
    }
    throw new Error(detail)
  }
  return response.json()
}

export function listJobs() {
  return request('/jobs')
}

export function getJob(jobId) {
  return request(`/jobs/${jobId}`)
}

export function uploadImages(files) {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return request('/jobs/upload', { method: 'POST', body: form })
}

export function saveItems(jobId, groups) {
  return request(`/jobs/${jobId}/items`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ groups }),
  })
}

export function createExport(jobId) {
  return request(`/jobs/${jobId}/export`, { method: 'POST' })
}

export function exportDownloadUrl(exportId) {
  const token = localStorage.getItem('accessToken') || ''
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${API_BASE}/exports/${exportId}/download${query}`
}

export function imagePreviewUrl(imageId) {
  const token = localStorage.getItem('accessToken') || ''
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${API_BASE}/images/${imageId}${query}`
}

export function deleteJob(jobId) {
  return request(`/jobs/${jobId}`, { method: 'DELETE' })
}
