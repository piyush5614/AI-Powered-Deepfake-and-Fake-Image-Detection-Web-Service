import { Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { clearHistory, deleteHistoryItem, getHistory } from '../api'
import { Badge } from '../components/Badge'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { Modal } from '../components/Modal'
import { Skeleton } from '../components/Skeleton'
import type { HistoryItem } from '../types'

function relativeTime(timestamp: string): string {
  const minutes = Math.round((Date.now() - new Date(timestamp).getTime()) / 60_000)
  if (!Number.isFinite(minutes)) return 'recently'
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  if (Math.abs(minutes) < 60) return formatter.format(-minutes, 'minute')
  if (Math.abs(minutes) < 1440) return formatter.format(-Math.round(minutes / 60), 'hour')
  return formatter.format(-Math.round(minutes / 1440), 'day')
}

export function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<{ id?: string; clear?: boolean } | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setItems(await getHistory(50)) } catch { setError('Could not load history. Check that the API is available.') } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  const remove = async () => {
    if (!pending) return
    const previous = items
    setItems(pending.clear ? [] : items.filter((item) => item.id !== pending.id))
    const target = pending
    setPending(null)
    try {
      if (target.clear) await clearHistory()
      else if (target.id) await deleteHistoryItem(target.id)
    } catch {
      setItems(previous)
      setError('Could not delete the selected history. Your list has been restored; please try again.')
    }
  }

  return (
    <main className="page-shell">
      <div className="page-title-row"><div><p className="eyebrow">YOUR ANALYSES</p><h1>History</h1><p className="page-subtitle">Recent results and their small preview images.</p></div>
        {items.length > 0 && <Button variant="ghost" onClick={() => setPending({ clear: true })}><Trash2 size={16} /> Clear all</Button>}
      </div>
      {error && <Card className="error-card" role="alert"><p>{error}</p><Button size="sm" onClick={() => void refresh()}>Retry</Button></Card>}
      {loading ? <div className="history-grid">{Array.from({ length: 6 }, (_, index) => <Card key={index}><Skeleton className="history-skeleton" /></Card>)}</div> :
        items.length === 0 ? <EmptyState title="No analyses yet" description="Your recent results will appear here after you analyze an image." link /> :
          <div className="history-grid">{items.map((item) => (
            <Card className="history-card" key={item.id}>
              <img className="history-thumbnail" src={item.thumbnail} alt={`Preview of ${item.filename}`} />
              <div className="history-card-heading"><Badge verdict={item.verdict}>{item.verdict === 'REAL' ? 'Likely real' : 'Likely AI-generated'}</Badge><Button variant="ghost" size="sm" aria-label={`Delete ${item.filename}`} onClick={() => setPending({ id: item.id })}><Trash2 size={15} /></Button></div>
              <strong className="history-filename">{item.filename}</strong>
              <p>{(item.confidence * 100).toFixed(1)}% confidence · {relativeTime(item.created_at)}</p>
            </Card>
          ))}</div>}
      {pending && <Modal title={pending.clear ? 'Clear all history?' : 'Delete this analysis?'} confirmLabel={pending.clear ? 'Clear all' : 'Delete'} onClose={() => setPending(null)} onConfirm={() => void remove()}>This action cannot be undone.</Modal>}
    </main>
  )
}
