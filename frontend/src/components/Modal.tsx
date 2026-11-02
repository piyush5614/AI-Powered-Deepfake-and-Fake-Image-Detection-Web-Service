import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Button } from './Button'

export function Modal({
  title,
  children,
  confirmLabel = 'Confirm',
  onConfirm,
  onClose,
}: {
  title: string
  children: ReactNode
  confirmLabel?: string
  onConfirm: () => void
  onClose: () => void
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="modal card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <h2 id="modal-title">{title}</h2><p>{children}</p>
        <div className="modal-actions"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button variant="danger" onClick={onConfirm}>{confirmLabel}</Button></div>
      </section>
    </div>
  )
}
