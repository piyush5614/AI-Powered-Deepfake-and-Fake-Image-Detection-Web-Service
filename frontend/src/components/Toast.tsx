import { CircleCheck, CircleX } from 'lucide-react'

export function Toast({ kind, message }: { kind: 'success' | 'error'; message: string }) {
  const Icon = kind === 'success' ? CircleCheck : CircleX
  return <div className={`toast toast-${kind}`} role="status"><Icon aria-hidden="true" size={18} />{message}</div>
}
