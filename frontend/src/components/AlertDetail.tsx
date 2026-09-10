import { useState } from 'react'
import type { Alert, AnalystAction } from '@/api'
import { postAlertAction } from '@/api'
import type { Lang } from '@/lib/i18n'
import { STRINGS } from '@/lib/i18n'
import { Badge } from './ui/badge'

interface AlertDetailProps {
  alert: Alert | null
  onClose: () => void
  onUpdated: (updated: Alert) => void
  lang: Lang
}

const TIER_VARIANT: Record<string, 'destructive' | 'secondary'> = { critical: 'destructive', review: 'secondary' }

// Simple click-through demo actions on a confirmed alert -- freeze ties into
// the same db.freeze_account path the automatic 85%-confidence policy uses,
// so a manual freeze from here shows up in the frozen-accounts banner and
// blocks that account's future transactions exactly like an automatic one.
export function AlertDetail({ alert, onClose, onUpdated, lang }: AlertDetailProps) {
  const t = STRINGS[lang].detail
  const [pending, setPending] = useState<AnalystAction | null>(null)
  const [error, setError] = useState(false)

  if (!alert) return null

  const act = async (action: AnalystAction) => {
    setPending(action)
    setError(false)
    try {
      const updated = await postAlertAction(alert.id, action)
      onUpdated(updated)
    } catch {
      setError(true)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-primary">{t.title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground active:scale-[0.97]"
          >
            ✕
          </button>
        </div>

        <dl className="space-y-2 text-sm">
          <Row label={t.fields.account} value={alert.account_id} />
          <Row label={t.fields.amount} value={`$${alert.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
          <Row label={t.fields.type} value={alert.tx_type} />
          <Row label={t.fields.payee} value={alert.payee_id} />
          <Row label={t.fields.branchChannel} value={`${alert.branch} / ${alert.channel}`} />
          <Row label={t.fields.heuristic} value={`${alert.heuristic_kind} (${alert.heuristic_score})`} />
          <Row
            label={t.fields.verdict}
            value={
              <>
                {alert.verdict} <span className="text-muted-foreground">({Math.round(alert.confidence * 100)}%)</span>
              </>
            }
          />
          <Row label={t.fields.tier} value={<Badge variant={TIER_VARIANT[alert.tier]}>{t.tierLabels[alert.tier]}</Badge>} />
          <Row label={t.fields.created} value={new Date(alert.created_at).toLocaleString()} />
          <div>
            <dt className="text-muted-foreground">{t.fields.reasoning}</dt>
            <dd className="mt-1 whitespace-pre-wrap text-foreground">{alert.reasoning}</dd>
          </div>
        </dl>

        <div className="mt-6 flex flex-wrap gap-2">
          <ActionButton label={t.actions.freeze} pending={pending === 'freeze'} onClick={() => act('freeze')} />
          <ActionButton label={t.actions.skip} pending={pending === 'skip'} onClick={() => act('skip')} />
          <ActionButton label={t.actions.contact} pending={pending === 'contact'} onClick={() => act('contact')} />
          <ActionButton label={t.actions.escalate} pending={pending === 'escalate'} onClick={() => act('escalate')} />
        </div>

        {alert.analyst_action && !error && (
          <p className="mt-3 text-xs text-muted-foreground">{t.actionTaken(alert.analyst_action)}</p>
        )}
        {error && <p className="mt-3 text-xs text-destructive">{t.actionError}</p>}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right text-foreground">{value}</dd>
    </div>
  )
}

function ActionButton({ label, pending, onClick }: { label: string; pending: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={pending}
      onClick={onClick}
      className="rounded-full border border-border px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-accent active:scale-[0.97] disabled:opacity-50"
    >
      {pending ? '…' : label}
    </button>
  )
}
