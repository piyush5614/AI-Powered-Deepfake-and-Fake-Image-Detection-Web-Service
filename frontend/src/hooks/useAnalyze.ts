import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeImage, getRetryAfter, toApiError } from '../api'
import type { AnalyzeResponse, ApiError } from '../types'

export type AnalysisState =
  | { status: 'idle' }
  | { status: 'ready' }
  | { status: 'uploading'; progress: number }
  | { status: 'analyzing'; progress: number }
  | { status: 'success'; result: AnalyzeResponse }
  | { status: 'error'; error: ApiError }

export function useAnalyze() {
  const [state, setState] = useState<AnalysisState>({ status: 'idle' })
  const [retryCountdown, setRetryCountdown] = useState(0)
  const controller = useRef<AbortController | null>(null)

  useEffect(() => {
    if (retryCountdown <= 0) return
    const timer = window.setTimeout(() => setRetryCountdown((seconds) => Math.max(0, seconds - 1)), 1000)
    return () => window.clearTimeout(timer)
  }, [retryCountdown])

  const markReady = useCallback((ready: boolean) => {
    setRetryCountdown(0)
    setState({ status: ready ? 'ready' : 'idle' })
  }, [])

  const run = useCallback(async (file: File) => {
    controller.current?.abort()
    setRetryCountdown(0)
    const currentController = new AbortController()
    controller.current = currentController
    setState({ status: 'uploading', progress: 0 })
    try {
      const result = await analyzeImage(file, {
        signal: currentController.signal,
        onProgress: (progress) => {
          setState(progress >= 100 ? { status: 'analyzing', progress: 100 } : { status: 'uploading', progress })
        },
      })
      setState({ status: 'success', result })
      return result
    } catch (error: unknown) {
      if (currentController.signal.aborted) {
        setState({ status: 'ready' })
        return null
      }
      const apiError = toApiError(error)
      const retryAfter = apiError.code === 'rate_limited' ? await getRetryAfter(error) : undefined
      if (retryAfter) setRetryCountdown(retryAfter)
      setState({ status: 'error', error: apiError })
      return null
    } finally {
      if (controller.current === currentController) controller.current = null
    }
  }, [])

  const cancel = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    setRetryCountdown(0)
    setState({ status: 'ready' })
  }, [])

  const reset = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    setRetryCountdown(0)
    setState({ status: 'idle' })
  }, [])

  return { state, retryCountdown, markReady, run, cancel, reset }
}
