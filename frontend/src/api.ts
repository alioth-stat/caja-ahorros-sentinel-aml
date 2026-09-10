export interface Alert {
  id: number
  account_id: string
  amount: number
  tx_type: string
  payee_id: string
  branch: string
  channel: string
  heuristic_kind: string
  heuristic_score: number
  verdict: string
  confidence: number
  reasoning: string
  tier: 'review' | 'critical'
  created_at: string
  analyst_action: string | null
}

export type AnalystAction = 'freeze' | 'skip' | 'contact' | 'escalate'

export interface FeedItem {
  id: number
  ts: number
  account_id: string
  amount: number
  tx_type: string
  branch: string
  channel: string
  status: string
  heuristic_kind?: string
  tier?: 'review' | 'critical'
  confidence?: number
  reasoning?: string
}

export interface FrozenAccount {
  account_id: string
  reason: string
  confidence: number
  alert_id: number
  frozen_at: string
}

export interface Stats {
  total_alerts: number
  by_kind: Record<string, number>
  by_tier: Record<string, number>
  frozen_accounts: number
  tx_per_second: number
  pending_review: number
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export function getAlerts(limit = 50): Promise<Alert[]> {
  return fetch(`/api/alerts?limit=${limit}`).then(unwrap<Alert[]>)
}

export function getFeed(limit = 20): Promise<FeedItem[]> {
  return fetch(`/api/feed?limit=${limit}`).then(unwrap<FeedItem[]>)
}

export function getFrozen(limit = 50): Promise<FrozenAccount[]> {
  return fetch(`/api/frozen?limit=${limit}`).then(unwrap<FrozenAccount[]>)
}

export function getStats(): Promise<Stats> {
  return fetch('/api/stats').then(unwrap<Stats>)
}

export function postAlertAction(alertId: number, action: AnalystAction): Promise<Alert> {
  return fetch(`/api/alerts/${alertId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  }).then(unwrap<Alert>)
}
