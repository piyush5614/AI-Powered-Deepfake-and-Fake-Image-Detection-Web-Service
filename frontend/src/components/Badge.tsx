import type { ReactNode } from 'react'
import type { Verdict } from '../types'

export function Badge({ verdict, children }: { verdict?: Verdict | 'neutral'; children?: ReactNode }) {
  const label = children ?? (verdict === 'REAL' ? 'Likely real' : verdict === 'FAKE' ? 'Likely AI-generated' : 'Neutral')
  return <span className={`badge badge-${verdict === 'REAL' ? 'real' : verdict === 'FAKE' ? 'fake' : 'neutral'}`}>{label}</span>
}
