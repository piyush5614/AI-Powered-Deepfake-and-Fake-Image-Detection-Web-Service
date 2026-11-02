import { ImageOff } from 'lucide-react'
import { Link } from 'react-router-dom'

export function EmptyState({ title, description, link = false }: { title: string; description: string; link?: boolean }) {
  return (
    <div className="empty-state">
      <ImageOff size={28} aria-hidden="true" />
      <h2>{title}</h2><p>{description}</p>
      {link && <Link className="text-link" to="/">Analyze an image</Link>}
    </div>
  )
}
