import type { Probabilities } from '../types'

export function ProbabilityBar({ probabilities }: { probabilities: Probabilities }) {
  return (
    <div className="probability-list" aria-label="Class probabilities">
      {(['REAL', 'FAKE'] as const).map((label) => (
        <div className="probability-row" key={label}>
          <div className="probability-caption"><span>{label === 'REAL' ? 'Real' : 'AI-generated'}</span><span className="mono">{(probabilities[label] * 100).toFixed(1)}%</span></div>
          <div className={`confidence-track probability-${label.toLowerCase()}`}><span style={{ width: `${probabilities[label] * 100}%` }} /></div>
        </div>
      ))}
    </div>
  )
}
