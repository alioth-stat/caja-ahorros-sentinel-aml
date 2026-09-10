export type Lang = 'es' | 'en'

interface Strings {
  subtitle: string
  transparencyButton: string
  backendError: string
  feedTitle: string
  feedColumns: { time: string; account: string; amount: string; status: string }
  statusLabels: Record<string, string>
  alertsTitle: string
  alertsColumns: { time: string; account: string; amount: string; type: string; verdict: string; reason: string }
  loading: string
  noAlertsYet: string
  statsTotal: string
  statsThroughput: string
  statsPending: string
  statsFrozen: string
  frozenBanner: (accountId: string, reason: string, confidencePct: number) => string
  panel: {
    title: string
    close: string
    howItWorksHeading: string
    steps: string[]
    dataNote: string
    glossaryHeading: string
  }
}

export const STRINGS: Record<Lang, Strings> = {
  es: {
    subtitle: 'Detección de transacciones sospechosas en tiempo real, con inferencia local vía QVAC.',
    transparencyButton: 'Transparencia y glosario',
    backendError: 'No se pudo conectar con el backend. Verifica que esté corriendo.',
    feedTitle: 'Stream de transacciones en vivo',
    feedColumns: { time: 'Hora', account: 'Cuenta', amount: 'Monto', status: 'Estado' },
    statusLabels: {
      normal: 'Normal', benign: 'Revisada: OK', pending: 'En revisión…', frozen_blocked: 'Bloqueada (cuenta congelada)',
      structuring: 'Estructuración', velocity_anomaly: 'Velocidad anómala', new_payee_risk: 'Beneficiario nuevo',
      geo_channel_anomaly: 'Anomalía sucursal/canal', layering: 'Layering',
    },
    alertsTitle: 'Alertas de fraude y AML',
    alertsColumns: { time: 'Hora', account: 'Cuenta', amount: 'Monto', type: 'Tipo', verdict: 'Veredicto', reason: 'Motivo' },
    loading: 'Cargando…',
    noAlertsYet: 'Sin alertas todavía. El pipeline sigue observando el stream de transacciones.',
    statsTotal: 'Alertas totales',
    statsThroughput: 'Transacciones/seg',
    statsPending: 'En cola para QVAC',
    statsFrozen: 'Cuentas congeladas',
    frozenBanner: (accountId, reason, confidencePct) =>
      `🚨 Cuenta ${accountId} congelada automáticamente — ${reason} (${confidencePct}% de confianza). Notificado a un analista.`,
    panel: {
      title: 'Transparencia del sistema',
      close: 'Cerrar',
      howItWorksHeading: 'Cómo funciona',
      steps: [
        '1. Heurísticos, sin IA. Reglas rápidas (estructuración cerca de un umbral, velocidad de transacciones, beneficiarios nuevos, cambios de sucursal/canal, depósitos seguidos de transferencias) corren sobre cada transacción del stream, a su ritmo completo, y deciden cuáles son candidatas sospechosas antes de gastar una llamada al modelo.',
        '2. Modelo QVAC local. Solo los candidatos filtrados llegan a un modelo de lenguaje pequeño (Qwen3-1.7B-Instruct) que corre en esta misma máquina, vía QVAC. Recibe únicamente la transacción y el tipo de sospecha ya identificado, nunca el historial completo de la cuenta, y devuelve un veredicto, un nivel de confianza y una explicación. QVAC es el recurso más lento del pipeline: por eso existe una cola ("en cola para QVAC" arriba) entre la detección y el veredicto final.',
        '3. Política de decisión. Un veredicto con 85% de confianza o más se trata como suficientemente seguro para actuar solo: la cuenta se congela automáticamente y se marca en rojo. Por debajo de ese umbral, la alerta queda en la cola de revisión manual para un analista.',
        '4. Cero llamadas a la nube. Todo el paso anterior ocurre sin conexión a internet. Se puede desconectar la red de esta máquina y el sistema sigue clasificando exactamente igual.',
        '5. Qué se guarda. Solo las alertas confirmadas (no las transacciones benignas), en una base de datos local en este equipo. Las alertas también se escriben a un archivo de log en un formato que un sistema de gestión de casos de cumplimiento puede leer directamente.',
        '6. Datos. Todas las cuentas y transacciones son 100% sintéticas, generadas para esta demo (la distribución de montos y canales está calibrada contra un dataset público de Kaggle, sin usar ninguna de sus filas). Nunca se usan datos reales de clientes.',
      ],
      dataNote:
        'Nota: el contenido que genera el modelo (veredicto y motivo) siempre aparece en español, sin importar este idioma de interfaz. Así fue instruido el modelo.',
      glossaryHeading: 'Glosario de términos',
    },
  },
  en: {
    subtitle: 'Real-time suspicious transaction detection, with inference running locally via QVAC.',
    transparencyButton: 'Transparency & glossary',
    backendError: "Couldn't connect to the backend. Check that it's running.",
    feedTitle: 'Live transaction stream',
    feedColumns: { time: 'Time', account: 'Account', amount: 'Amount', status: 'Status' },
    statusLabels: {
      normal: 'Normal', benign: 'Reviewed: OK', pending: 'Reviewing…', frozen_blocked: 'Blocked (account frozen)',
      structuring: 'Structuring', velocity_anomaly: 'Velocity anomaly', new_payee_risk: 'New payee risk',
      geo_channel_anomaly: 'Geo/channel anomaly', layering: 'Layering',
    },
    alertsTitle: 'Fraud & AML alerts',
    alertsColumns: { time: 'Time', account: 'Account', amount: 'Amount', type: 'Type', verdict: 'Verdict', reason: 'Reason' },
    loading: 'Loading…',
    noAlertsYet: 'No alerts yet. The pipeline is still watching the transaction stream.',
    statsTotal: 'Total alerts',
    statsThroughput: 'Transactions/sec',
    statsPending: 'Queued for QVAC',
    statsFrozen: 'Frozen accounts',
    frozenBanner: (accountId, reason, confidencePct) =>
      `🚨 Account ${accountId} automatically frozen — ${reason} (${confidencePct}% confidence). An analyst has been notified.`,
    panel: {
      title: 'System transparency',
      close: 'Close',
      howItWorksHeading: 'How it works',
      steps: [
        '1. Rule-based checks, no AI. Fast checks (near-threshold structuring, transaction velocity, new payees, branch/channel changes, deposits followed by transfers) run on every transaction in the stream, at its full rate, and decide which ones are worth escalating before spending a call on the model.',
        '2. Local QVAC model. Only the filtered candidates reach a small language model (Qwen3-1.7B-Instruct) running on this same machine, via QVAC. It receives only the transaction and the already-identified suspicion type, never the account’s full history, and returns a verdict, a confidence level, and an explanation. QVAC is the slowest part of the pipeline, which is why there’s a queue ("queued for QVAC" above) between detection and a final verdict.',
        "3. Decision policy. A verdict at 85% confidence or above is treated as certain enough to act on automatically: the account is frozen and flagged red. Below that bar, the alert sits in a manual-review queue for an analyst.",
        '4. Zero cloud calls. All of the above happens with no internet connection. You can disconnect this machine from the network and the system keeps classifying exactly the same.',
        '5. What gets stored. Only confirmed alerts, not benign transactions, in a local database on this machine. Alerts are also written to a log file in a format a compliance case-management system can read directly.',
        '6. Data. Every account and transaction is 100% synthetic, generated for this demo (amount and channel distributions are calibrated against a public Kaggle dataset, without using any of its rows). No real customer data is ever used.',
      ],
      dataNote:
        "Note: content generated by the model (verdict and reasoning) always appears in Spanish, regardless of this interface language. That's how the model was prompted.",
      glossaryHeading: 'Glossary',
    },
  },
}
