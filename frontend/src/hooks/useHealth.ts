import { useEffect, useState } from 'react'
import { getHealth } from '../api'
import type { HealthResponse } from '../types'

export type HealthState =
  | { status: 'loading' }
  | { status: 'offline' }
  | { status: 'online'; health: HealthResponse }

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    const poll = async () => {
      try {
        const health = await getHealth()
        if (active) setState({ status: 'online', health })
      } catch {
        if (active) setState({ status: 'offline' })
      }
    }
    void poll()
    const timer = window.setInterval(() => void poll(), 30_000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  return state
}
