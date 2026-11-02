export type Verdict = 'REAL' | 'FAKE'

export interface Probabilities {
  REAL: number
  FAKE: number
}

export interface ImageInfo {
  filename: string
  width: number
  height: number
  size_kb: number
  format: string
}

export interface ModelInfo {
  name: string
  input_size: number
}

export interface AnalyzeResponse {
  id: string
  verdict: Verdict
  confidence: number
  probabilities: Probabilities
  heatmap: string
  original: string
  image_info: ImageInfo
  model: ModelInfo
  processing_ms: number
  created_at: string
}

export interface HealthResponse {
  status: string
  model_loaded: boolean
  model_name: string
  version: string
}

export interface HistoryItem {
  id: string
  verdict: Verdict
  confidence: number
  filename: string
  created_at: string
  thumbnail: string
}

export interface ApiError {
  code: string
  message: string
}
