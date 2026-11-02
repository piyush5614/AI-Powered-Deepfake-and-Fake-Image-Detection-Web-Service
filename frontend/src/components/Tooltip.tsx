import type { ReactNode } from 'react'
import { Info } from 'lucide-react'

export function Tooltip({ text, children }: { text: string; children?: ReactNode }) {
  return <span className="tooltip" tabIndex={0} aria-label={text} title={text}>{children ?? <Info size={15} aria-hidden="true" />}</span>
}
