import { useEffect, useState } from 'react'

export function ConfidenceMeter({ value }: { value: number }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100)
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    let frame = 0
    const started = performance.now()
    const animate = (now: number) => {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        setDisplayed(percent)
        return
      }
      const progress = Math.min(1, (now - started) / 650)
      setDisplayed(Math.round(percent * progress))
      if (progress < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [percent])

  return (
    <div className="confidence">
      <div className="confidence-track" role="progressbar" aria-label="Prediction confidence" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}><span style={{ width: `${displayed}%` }} /></div>
      <div className="confidence-label"><span>Confidence</span><strong className="mono">{displayed}%</strong></div>
    </div>
  )
}
