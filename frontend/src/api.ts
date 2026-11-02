import axios, { AxiosError } from 'axios'
import type {
  AnalyzeResponse,
  ApiError,
  HealthResponse,
  HistoryItem,
} from './types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 30_000,
})

export function toApiError(error: unknown): ApiError {
  if (axios.isCancel(error)) {
    return { code: 'cancelled', message: 'Analysis cancelled.' }
  }
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ error?: ApiError }>
    const serverError = axiosError.response?.data?.error
    if (serverError && typeof serverError.code === 'string' && typeof serverError.message === 'string') {
      return serverError
    }
    if (axiosError.code === 'ECONNABORTED' || axiosError.code === 'ETIMEDOUT') {
      return { code: 'timeout', message: 'The request timed out. Try again with a smaller image.' }
    }
    if (!axiosError.response) {
      return { code: 'network_error', message: 'Cannot reach the server. Is the backend running?' }
    }
  }
  return { code: 'unknown', message: 'Something went wrong. Please try again.' }
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

export async function analyzeImage(
  file: File,
  options: { onProgress?: (percent: number) => void; signal?: AbortSignal },
): Promise<AnalyzeResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<AnalyzeResponse>('/analyze', form, {
    signal: options.signal,
    onUploadProgress: (event) => {
      if (event.total) options.onProgress?.(Math.round((event.loaded / event.total) * 100))
    },
  })
  return data
}

export async function getHistory(limit = 20): Promise<HistoryItem[]> {
  const { data } = await api.get<{ items: HistoryItem[] }>('/history', { params: { limit } })
  return data.items
}

export async function deleteHistoryItem(id: string): Promise<void> {
  await api.delete(`/history/${encodeURIComponent(id)}`)
}

export async function clearHistory(): Promise<void> {
  await api.delete('/history')
}

export async function getRetryAfter(error: unknown): Promise<number> {
  if (axios.isAxiosError(error)) {
    const header = error.response?.headers['retry-after']
    const seconds = Number.parseInt(String(header ?? ''), 10)
    if (Number.isFinite(seconds)) return seconds
  }
  return 60
}
