import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, ArrowDownToLine, Check, Clipboard, ImagePlus, RotateCcw, UploadCloud, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { ConfidenceMeter } from '../components/ConfidenceMeter'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { Segmented } from '../components/Segmented'
import { Skeleton } from '../components/Skeleton'
import { Slider } from '../components/Slider'
import { Tooltip } from '../components/Tooltip'
import { EmptyState } from '../components/EmptyState'
import { Modal } from '../components/Modal'
import { Toast } from '../components/Toast'
import { useAnalyze } from '../hooks/useAnalyze'
import type { AnalyzeResponse } from '../types'

const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])
const MAX_FILE_BYTES = 5 * 1024 * 1024
type ViewMode = 'Original' | 'Heatmap' | 'Compare'

function formatBytes(bytes: number): string {
  return `${(bytes / 1024).toFixed(0)} KB`
}

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) return 'Only JPEG, PNG and WebP images are allowed.'
  if (file.size > MAX_FILE_BYTES) return 'Images must be 5 MB or smaller.'
  return null
}

function ResultPanel({ result, onReset }: { result: AnalyzeResponse; onReset: () => void }) {
  const [mode, setMode] = useState<ViewMode>('Original')
  const [opacity, setOpacity] = useState(100)
  const [compare, setCompare] = useState(50)
  const [copied, setCopied] = useState(false)
  const resultHeading = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    resultHeading.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
    resultHeading.current?.focus({ preventScroll: true })
  }, [])

  const copyResult = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  return (
    <motion.section
      className="result-grid"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      aria-labelledby="result-title"
    >
      <Card className="viewer-card">
        <div className="card-heading"><div><p className="eyebrow">VISUAL EXPLANATION</p><h2>Image viewer</h2></div><Tooltip text="The overlay is a model explanation, not proof of manipulation." /></div>
        <Segmented options={['Original', 'Heatmap', 'Compare'] as const} value={mode} onChange={setMode} />
        <div className="image-stage" style={{
          aspectRatio: `${result.image_info.width} / ${result.image_info.height}`,
          width: `min(100%, ${540 * result.image_info.width / result.image_info.height}px)`,
        }}>
          <img className="stage-base" src={result.original} alt={`Original image: ${result.image_info.filename}`} />
          {mode === 'Heatmap' && <img className="stage-overlay" style={{ opacity: opacity / 100 }} src={result.heatmap} alt="Grad-CAM heatmap overlay showing influential regions" />}
          {mode === 'Compare' && (
            <div className="compare-overlay" style={{ clipPath: `inset(0 0 0 ${compare}%)` }}>
              <img src={result.heatmap} alt="Heatmap side of comparison" />
            </div>
          )}
          {mode === 'Compare' && (
            <input className="compare-range" type="range" min={0} max={100} value={compare} onChange={(event) => setCompare(Number(event.target.value))} aria-label="Compare original and heatmap" />
          )}
          {mode === 'Compare' && <span className="compare-divider" style={{ left: `${compare}%` }} aria-hidden="true" />}
          <span className="image-caption mono">{mode === 'Heatmap' ? 'GRAD-CAM OVERLAY' : mode === 'Compare' ? 'ORIGINAL / HEATMAP' : 'ORIGINAL IMAGE'}</span>
        </div>
        {mode === 'Heatmap' && <Slider label="Overlay opacity" value={opacity} onChange={setOpacity} />}
        {mode !== 'Original' && (
          <div className="heatmap-legend"><span>Less influence</span><span className="legend-gradient" aria-hidden="true" /><span>More influence</span><Tooltip text="Warm areas are regions the model found most suspicious. It highlights where the model looked, not proof of editing." /></div>
        )}
        <Button variant="secondary" onClick={() => {
          const anchor = document.createElement('a')
          anchor.href = result.heatmap
          anchor.download = `truthlens-${result.id.slice(0, 8)}-heatmap.png`
          anchor.click()
        }}><ArrowDownToLine size={16} aria-hidden="true" /> Download heatmap</Button>
      </Card>
      <Card className="verdict-card">
        <p className="eyebrow">ANALYSIS RESULT</p>
        <h2 id="result-title" ref={resultHeading} tabIndex={-1}>Image assessment</h2>
        <Badge verdict={result.verdict}>{result.verdict === 'REAL' ? '✓  Likely real' : '⚠  Likely AI-generated'}</Badge>
        <ConfidenceMeter value={result.confidence} />
        <ProbabilityBar probabilities={result.probabilities} />
        {result.confidence < 0.7 && <div className="notice notice-warning"><AlertTriangle size={17} />Low confidence. Treat this result as inconclusive.</div>}
        <p className="disclaimer">Detection is probabilistic and can be wrong. Do not use this as sole evidence.</p>
        <details className="technical-details"><summary>Technical details</summary>
          <dl className="details-grid">
            <dt>Model</dt><dd>{result.model.name}</dd>
            <dt>Input size</dt><dd>{result.model.input_size}px</dd>
            <dt>Processing</dt><dd>{result.processing_ms} ms</dd>
            <dt>Dimensions</dt><dd>{result.image_info.width} × {result.image_info.height}</dd>
            <dt>Format / size</dt><dd>{result.image_info.format} / {result.image_info.size_kb} KB</dd>
            <dt>Analysis ID</dt><dd className="truncate">{result.id}</dd>
            <dt>Timestamp</dt><dd>{new Date(result.created_at).toLocaleString()}</dd>
          </dl>
        </details>
        <div className="result-actions"><Button variant="primary" onClick={onReset}><RotateCcw size={15} /> Analyze another</Button><Button onClick={() => void copyResult()}>{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? 'Copied' : 'Copy result as JSON'}</Button></div>
      </Card>
    </motion.section>
  )
}

export function AnalyzerPage() {
  const { state, retryCountdown, markReady, run, cancel, reset } = useAnalyze()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [analysisTick, setAnalysisTick] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const busy = state.status === 'uploading' || state.status === 'analyzing'
  const currentError = state.status === 'error' ? state.error : null
  const analyzingStage = analysisTick % 2

  useEffect(() => {
    if (state.status !== 'analyzing') return
    const timer = window.setInterval(() => setAnalysisTick((tick) => tick + 1), 2200)
    return () => window.clearInterval(timer)
  }, [state.status])

  const setSelectedFile = useCallback((next: File | null) => {
    setClientError(null)
    if (!next) {
      setFile(null)
      setPreviewUrl(null)
      if (inputRef.current) inputRef.current.value = ''
      markReady(false)
      return
    }
    const validationError = validateFile(next)
    if (validationError) {
      setClientError(validationError)
      setFile(null)
      setPreviewUrl(null)
      if (inputRef.current) inputRef.current.value = ''
      markReady(false)
      return
    }
    setFile(next)
    setPreviewUrl(URL.createObjectURL(next))
    markReady(true)
    if (inputRef.current) inputRef.current.value = ''
  }, [markReady])

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [previewUrl])

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const pasted = Array.from(event.clipboardData?.files ?? []).find((item) => item.type.startsWith('image/'))
      if (pasted) setSelectedFile(pasted)
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [setSelectedFile])

  const analyze = async () => {
    if (file) await run(file)
  }

  const retry = async () => {
    if (file) await run(file)
  }

  const chooseNewImage = () => {
    setFile(null)
    setSelectedFile(null)
    reset()
  }

  return (
    <main className="page-shell analyzer-page">
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <span className="eyebrow-pill"><span className="live-dot" /> AI-GENERATED IMAGE DETECTION</span>
        <h1>Is this image <span>real?</span></h1>
        <p>Get a clear signal, confidence score, and visual explanation — without uploading your image to a gallery or dataset.</p>
      </section>

      <Card className={`upload-card ${dragging ? 'is-dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        const dropped = event.dataTransfer.files[0]
        if (dropped) setSelectedFile(dropped)
      }}>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="visually-hidden" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
        {previewUrl && file ? (
          <div className="selected-file">
            <img src={previewUrl} alt="Selected image preview" />
            <div className="selected-file-info"><strong>{file.name}</strong><span className="mono">{formatBytes(file.size)}</span></div>
            <Button variant="ghost" size="sm" onClick={chooseNewImage} aria-label="Remove selected image" disabled={busy}><X size={17} /> Remove</Button>
            <Button variant="primary" onClick={() => void analyze()} disabled={busy || state.status === 'success'}><UploadCloud size={16} /> Analyze image</Button>
          </div>
        ) : (
          <button type="button" className="dropzone" onClick={() => inputRef.current?.click()}>
            <span className="drop-icon"><ImagePlus size={23} /></span>
            <strong>Drop an image here, or <span>browse files</span></strong>
            <span>Paste from clipboard · JPEG, PNG or WebP · Up to 5 MB</span>
          </button>
        )}
        {clientError && <p className="inline-error" role="alert">{clientError}</p>}
      </Card>

      {busy && (
        <Card className="progress-card">
          <div className="progress-copy"><span aria-live="polite">{state.status === 'uploading' ? 'Uploading image…' : analyzingStage === 0 ? 'Running detection model…' : 'Generating heatmap…'}</span><span className="mono">{state.status === 'uploading' ? `${state.progress}%` : 'Please wait'}</span></div>
          <div className="confidence-track"><span style={{ width: `${state.status === 'uploading' ? Math.max(4, state.progress) : 100}%` }} /></div>
          <Button variant="ghost" size="sm" onClick={cancel}>Cancel</Button>
          <div className="loading-preview"><Skeleton /><Skeleton /></div>
        </Card>
      )}

      {currentError && (
        <Card className="error-card" role="alert">
          <AlertTriangle size={20} /><div><h2>{currentError.code === 'model_not_loaded' ? 'Model not loaded' : currentError.code === 'rate_limited' ? 'Slow down for a moment' : 'We couldn’t analyze this image'}</h2><p>{currentError.message}</p>{currentError.code === 'model_not_loaded' && <p>Set up a trained checkpoint at <code>ml/artifacts/best.pt</code> to enable analysis.</p>}</div>
          {currentError.code === 'rate_limited' && <p className="mono retry-countdown" aria-live="polite">Try again in {retryCountdown}s</p>}
          <Button disabled={currentError.code === 'rate_limited' && retryCountdown > 0} onClick={() => void retry()}>Retry</Button>
        </Card>
      )}

      <AnimatePresence mode="wait">
        {state.status === 'success' && <ResultPanel key={state.result.id} result={state.result} onReset={() => { setFile(null); setSelectedFile(null); reset() }} />}
      </AnimatePresence>

      {!busy && state.status !== 'success' && <div className="privacy-note"><span className="privacy-dot" /> Images are processed in memory and never stored. Analysis history keeps only a small thumbnail.</div>}
    </main>
  )
}

export function StyleguidePage() {
  const [showModal, setShowModal] = useState(false)
  return (
    <main className="page-shell styleguide-page">
      <p className="eyebrow">DEVELOPMENT ONLY</p><h1>Interface components</h1>
      <div className="styleguide-grid"><Card><h2>Verdicts</h2><Badge verdict="REAL" /><Badge verdict="FAKE" /><Badge>Neutral</Badge></Card>
        <Card><h2>Controls</h2><div className="button-row"><Button variant="primary">Primary</Button><Button>Secondary</Button><Button variant="ghost">Ghost</Button><Button variant="danger">Danger</Button><Button loading>Loading</Button></div><Segmented options={['Original', 'Heatmap'] as const} value="Original" onChange={() => {}} /><Slider label="Opacity" value={55} onChange={() => {}} /></Card>
        <Card><h2>Feedback</h2><Skeleton className="styleguide-skeleton" /><div className="notice notice-warning"><AlertTriangle size={16} />Low confidence.</div><Toast kind="success" message="Analysis complete" /><Button onClick={() => setShowModal(true)}>Open confirmation</Button></Card>
        <Card><h2>Analysis</h2><ConfidenceMeter value={0.78} /><ProbabilityBar probabilities={{ REAL: 0.78, FAKE: 0.22 }} /><Tooltip text="Warm regions show where the model looked." /></Card>
        <Card><h2>Empty state</h2><EmptyState title="No images yet" description="Start an analysis to see results here." /></Card>
      </div>
      {showModal && <Modal title="Delete result?" onClose={() => setShowModal(false)} onConfirm={() => setShowModal(false)}>This is a preview of the confirmation dialog.</Modal>}
    </main>
  )
}
