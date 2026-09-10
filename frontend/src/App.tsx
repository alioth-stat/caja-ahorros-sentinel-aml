import { useEffect, useRef, useState } from 'react'
import { getAlerts, getFeed, getFrozen, getStats } from '@/api'
import { Background } from '@/components/Background'
import { GlassPanel } from '@/components/GlassPanel'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { VisibilityPanel } from '@/components/VisibilityPanel'
import { usePolling } from '@/hooks/use-polling'
import { STRINGS, type Lang } from '@/lib/i18n'

// Rough severity split so a glance at the table tells kinds apart -- mirrors
// compliance_sink.py's per-kind case severity (structuring/layering > new
// payee > velocity/geo).
const VERDICT_VARIANT: Record<string, 'destructive' | 'secondary' | 'outline'> = {
  structuring: 'destructive',
  layering: 'destructive',
  new_payee_risk: 'secondary',
  velocity_anomaly: 'secondary',
  geo_channel_anomaly: 'outline',
}

// Feed rows carry more statuses than confirmed alerts do (normal/pending/
// frozen_blocked on top of the 5 verdict kinds) -- tier wins over kind when
// both are present, since "critical" is the more consequential fact.
function feedVariant(item: { status: string; tier?: string }): 'destructive' | 'secondary' | 'outline' {
  if (item.tier === 'critical') return 'destructive'
  if (item.status === 'pending') return 'secondary'
  if (item.status === 'frozen_blocked') return 'destructive'
  return VERDICT_VARIANT[item.status] ?? 'outline'
}

const LANG_STORAGE_KEY = 'sentinel-aml-lang'

function readStoredLang(): Lang {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(LANG_STORAGE_KEY) : null
  return stored === 'en' ? 'en' : 'es'
}

function formatTime(ts: number | string): string {
  const ms = typeof ts === 'number' ? ts * 1000 : new Date(ts).getTime()
  return new Date(ms).toLocaleTimeString()
}

function formatAmount(n: number): string {
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function App() {
  const { data: alerts, error: alertsError } = usePolling(() => getAlerts(30), 3000)
  const { data: feed } = usePolling(() => getFeed(20), 1500)
  const { data: frozen } = usePolling(() => getFrozen(50), 3000)
  const { data: stats } = usePolling(getStats, 3000)
  const [visibilityOpen, setVisibilityOpen] = useState(false)
  const [lang, setLang] = useState<Lang>(readStoredLang)
  const t = STRINGS[lang]

  const seenFrozenIds = useRef<Set<string>>(new Set())
  const [banner, setBanner] = useState<{ accountId: string; reason: string; confidencePct: number } | null>(null)

  useEffect(() => {
    if (!frozen) return
    for (const f of frozen) {
      if (!seenFrozenIds.current.has(f.account_id)) {
        seenFrozenIds.current.add(f.account_id)
        setBanner({ accountId: f.account_id, reason: f.reason, confidencePct: Math.round(f.confidence * 100) })
        setTimeout(() => setBanner((cur) => (cur?.accountId === f.account_id ? null : cur)), 8000)
        break
      }
    }
  }, [frozen])

  const toggleLang = () => {
    const next: Lang = lang === 'es' ? 'en' : 'es'
    setLang(next)
    try {
      localStorage.setItem(LANG_STORAGE_KEY, next)
    } catch {
      // private browsing or storage disabled -- toggle still works for this session
    }
  }

  return (
    <>
      <Background />
      <VisibilityPanel open={visibilityOpen} onClose={() => setVisibilityOpen(false)} lang={lang} />
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 md:p-10">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-primary">Sentinel-AML</h1>
            <p className="text-sm text-muted-foreground">{t.subtitle}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={toggleLang}
              aria-label={lang === 'es' ? 'Switch to English' : 'Cambiar a español'}
              className="rounded-full border border-border px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-accent active:scale-[0.97]"
            >
              {lang === 'es' ? 'EN' : 'ES'}
            </button>
            <button
              type="button"
              onClick={() => setVisibilityOpen(true)}
              className="rounded-full border border-border px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-accent active:scale-[0.97]"
            >
              {t.transparencyButton}
            </button>
          </div>
        </header>

        {alertsError && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t.backendError}</p>
        )}

        {banner && (
          <div className="rounded-md border border-destructive bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive">
            {t.frozenBanner(banner.accountId, t.statusLabels[banner.reason] ?? banner.reason, banner.confidencePct)}
          </div>
        )}

        {stats && (
          <div className="flex flex-wrap items-center gap-3">
            <GlassPanel className="max-w-none px-4 py-2">
              <span className="text-xs text-muted-foreground">{t.statsTotal}</span>{' '}
              <span className="font-semibold text-primary">{stats.total_alerts}</span>
            </GlassPanel>
            <GlassPanel className="max-w-none px-4 py-2">
              <span className="text-xs text-muted-foreground">{t.statsThroughput}</span>{' '}
              <span className="font-semibold text-primary">{stats.tx_per_second}</span>
            </GlassPanel>
            <GlassPanel className="max-w-none px-4 py-2">
              <span className="text-xs text-muted-foreground">{t.statsPending}</span>{' '}
              <span className="font-semibold text-primary">{stats.pending_review}</span>
            </GlassPanel>
            <GlassPanel className="max-w-none px-4 py-2">
              <span className="text-xs text-muted-foreground">{t.statsFrozen}</span>{' '}
              <span className="font-semibold text-primary">{stats.frozen_accounts}</span>
            </GlassPanel>
            {Object.entries(stats.by_kind).map(([kind, count]) => (
              <Badge key={kind} variant={VERDICT_VARIANT[kind] ?? 'outline'}>
                {t.statusLabels[kind] ?? kind}: {count}
              </Badge>
            ))}
          </div>
        )}

        <GlassPanel className="max-w-none">
          <h2 className="mb-4 text-lg font-medium text-primary">{t.feedTitle}</h2>
          <div className="max-h-72 overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.feedColumns.time}</TableHead>
                  <TableHead>{t.feedColumns.account}</TableHead>
                  <TableHead>{t.feedColumns.amount}</TableHead>
                  <TableHead>{t.feedColumns.status}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {feed === null && (
                  <TableRow>
                    <TableCell colSpan={4}>{t.loading}</TableCell>
                  </TableRow>
                )}
                {feed?.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="whitespace-nowrap">{formatTime(item.ts)}</TableCell>
                    <TableCell title={item.account_id}>{item.account_id}</TableCell>
                    <TableCell className="whitespace-nowrap">{formatAmount(item.amount)}</TableCell>
                    <TableCell className="whitespace-nowrap">
                      <Badge variant={feedVariant(item)} className={item.status === 'pending' ? 'animate-pulse' : ''}>
                        {t.statusLabels[item.status] ?? item.status}
                      </Badge>
                      {item.confidence != null && (
                        <span className="ml-1 text-xs text-muted-foreground">{Math.round(item.confidence * 100)}%</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </GlassPanel>

        <GlassPanel className="max-w-none">
          <h2 className="mb-4 text-lg font-medium text-primary">{t.alertsTitle}</h2>
          <div className="max-h-[32rem] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.alertsColumns.time}</TableHead>
                  <TableHead>{t.alertsColumns.account}</TableHead>
                  <TableHead>{t.alertsColumns.amount}</TableHead>
                  <TableHead>{t.alertsColumns.type}</TableHead>
                  <TableHead>{t.alertsColumns.verdict}</TableHead>
                  <TableHead>{t.alertsColumns.reason}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts === null && (
                  <TableRow>
                    <TableCell colSpan={6}>{t.loading}</TableCell>
                  </TableRow>
                )}
                {alerts?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-muted-foreground">
                      {t.noAlertsYet}
                    </TableCell>
                  </TableRow>
                )}
                {alerts?.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="align-top whitespace-nowrap">{formatTime(a.created_at)}</TableCell>
                    <TableCell className="align-top" title={a.account_id}>{a.account_id}</TableCell>
                    <TableCell className="align-top whitespace-nowrap">{formatAmount(a.amount)}</TableCell>
                    <TableCell className="align-top">{a.tx_type}</TableCell>
                    <TableCell className="align-top whitespace-nowrap">
                      <Badge variant={a.tier === 'critical' ? 'destructive' : (VERDICT_VARIANT[a.verdict] ?? 'outline')}>
                        {t.statusLabels[a.verdict] ?? a.verdict}
                      </Badge>
                      <span className="ml-1 text-xs text-muted-foreground">{Math.round(a.confidence * 100)}%</span>
                    </TableCell>
                    <TableCell className="max-w-80 min-w-48 align-top" title={a.reasoning}>
                      <p className="line-clamp-2 whitespace-normal text-muted-foreground">{a.reasoning}</p>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </GlassPanel>
      </div>
    </>
  )
}

export default App
