import type { Lang } from './i18n'

export interface GlossaryEntry {
  term: string
  definition: string
}

// Plain-language definitions for every technical term that shows up
// somewhere on the dashboard (table headers, verdicts, badges). Surfaced
// via VisibilityPanel so a non-technical viewer isn't left guessing.
export const GLOSSARY: Record<Lang, GlossaryEntry[]> = {
  es: [
    {
      term: 'Estructuración (structuring)',
      definition:
        'Dividir una operación grande en varias transacciones más pequeñas, cada una justo por debajo de un umbral de reporte, para evitar que se registre. Se reconoce por varias transferencias del mismo monto aproximado, cercanas entre sí en el tiempo.',
    },
    {
      term: 'Velocidad anómala',
      definition:
        'Una cuenta que de repente hace muchas más transacciones de las que hace normalmente, en muy poco tiempo. Puede indicar una cuenta comprometida o un script automatizado.',
    },
    {
      term: 'Beneficiario nuevo (new payee risk)',
      definition:
        'Una transferencia grande a alguien que la cuenta nunca le había enviado dinero antes. No es sospechoso por sí solo, pero combinado con un monto inusualmente alto es una señal clásica de fraude.',
    },
    {
      term: 'Anomalía de sucursal/canal',
      definition:
        'Una transacción hecha desde una sucursal o canal (app, web, cajero) distinto al que la cuenta usa normalmente, en una ventana de tiempo que no encaja con su patrón habitual.',
    },
    {
      term: 'Layering',
      definition:
        'Mover fondos rápidamente a través de una cuenta —típicamente un depósito grande seguido de transferencias salientes a beneficiarios nuevos— para dificultar el rastreo del origen del dinero. Es una técnica clásica de lavado de dinero.',
    },
    {
      term: 'AML (Anti-Money Laundering)',
      definition: 'El conjunto de controles que usan los bancos para detectar y prevenir el lavado de dinero.',
    },
    {
      term: 'UAF (Unidad de Análisis Financiero)',
      definition: 'La unidad de inteligencia financiera de Panamá, encargada de recibir y analizar reportes de operaciones sospechosas.',
    },
    {
      term: 'Congelamiento automático',
      definition:
        'Cuando QVAC da un veredicto de fraude/AML con 85% de confianza o más, la cuenta se congela automáticamente (sin esperar revisión humana) y se notifica de inmediato. Por debajo de ese umbral, la alerta queda en cola para revisión manual.',
    },
    {
      term: 'Cola de QVAC',
      definition:
        'QVAC solo puede evaluar una transacción a la vez en este equipo (unos 15-25 segundos cada una). Los heurísticos, en cambio, corren a la velocidad completa del stream. Esa diferencia de ritmo crea una cola visible ("en cola para QVAC") entre la detección y el veredicto final.',
    },
    {
      term: 'Veredicto',
      definition:
        'La clasificación final que da el modelo para una transacción sospechosa: benigna, structuring, velocity_anomaly, new_payee_risk, geo_channel_anomaly o layering.',
    },
    {
      term: 'Confianza',
      definition:
        'Qué tan seguro está el modelo de su propio veredicto, de 0 a 100%. No mide qué tan riesgosa es la transacción, sino cuánta certeza tiene el modelo en su respuesta.',
    },
    {
      term: 'Heurístico',
      definition:
        'Una regla simple y rápida (no un modelo de IA) que detecta un patrón sospechoso, por ejemplo "¿está este monto justo debajo de un umbral conocido?". Filtra candidatos antes de gastar una llamada al modelo, que es más lenta.',
    },
    {
      term: 'Cola de casos de cumplimiento',
      definition:
        'El sistema donde un banco real gestiona las alertas de fraude/AML confirmadas para que un analista las revise. Este prototipo le entrega alertas en un formato JSON que ese tipo de sistema puede leer directamente.',
    },
    {
      term: 'QVAC / on-device',
      definition:
        'El SDK que permite correr modelos de IA completos en esta misma máquina, sin enviar ningún dato a un servidor externo. Es el requisito no negociable de este proyecto: ningún dato de cliente sale del dispositivo ni de la infraestructura del banco.',
    },
  ],
  en: [
    {
      term: 'Structuring',
      definition:
        'Splitting a large operation into several smaller transactions, each just under a reporting threshold, to avoid it being logged. Recognizable by several transfers of roughly the same amount, close together in time.',
    },
    {
      term: 'Velocity anomaly',
      definition:
        'An account suddenly making far more transactions than it normally does, in a very short time. Can indicate a compromised account or an automated script.',
    },
    {
      term: 'New payee risk',
      definition:
        "A large transfer to someone the account has never sent money to before. Not suspicious on its own, but combined with an unusually high amount it's a classic fraud signal.",
    },
    {
      term: 'Geo/channel anomaly',
      definition:
        "A transaction made from a branch or channel (app, web, ATM) different from the account's usual one, in a time window that doesn't fit its established pattern.",
    },
    {
      term: 'Layering',
      definition:
        'Rapidly moving funds through an account — typically a large deposit followed by outgoing transfers to new payees — to make the origin of the money harder to trace. A classic money-laundering technique.',
    },
    {
      term: 'AML (Anti-Money Laundering)',
      definition: 'The set of controls banks use to detect and prevent money laundering.',
    },
    {
      term: 'UAF (Unidad de Análisis Financiero)',
      definition: "Panama's financial intelligence unit, responsible for receiving and analyzing suspicious activity reports.",
    },
    {
      term: 'Automatic freeze',
      definition:
        "When QVAC returns a fraud/AML verdict at 85% confidence or above, the account is frozen automatically (no human review needed first) and a notification fires immediately. Below that bar, the alert sits in a manual-review queue instead.",
    },
    {
      term: 'QVAC queue',
      definition:
        'QVAC can only evaluate one transaction at a time on this machine (roughly 15-25 seconds each). Heuristics, by contrast, run at the stream\'s full rate. That pace difference creates a visible queue ("queued for QVAC") between detection and a final verdict.',
    },
    {
      term: 'Verdict',
      definition:
        "The model's final classification for a suspicious transaction: benign, structuring, velocity_anomaly, new_payee_risk, geo_channel_anomaly, or layering.",
    },
    {
      term: 'Confidence',
      definition:
        'How sure the model is of its own verdict, from 0 to 100%. It does not measure how risky the transaction is, only how certain the model is in its answer.',
    },
    {
      term: 'Heuristic',
      definition:
        'A simple, fast rule, not an AI model, that flags a suspicious pattern, for example "is this amount just under a known threshold?". Filters candidates before spending a call on the slower model.',
    },
    {
      term: 'Compliance case queue',
      definition:
        'The system a real bank uses to manage confirmed fraud/AML alerts for an analyst to review. This prototype hands it alerts in a JSON format that kind of system can read directly.',
    },
    {
      term: 'QVAC / on-device',
      definition:
        "The SDK that runs full AI models on this same machine, without sending any data to an external server. The non-negotiable requirement of this project: no customer data leaves the device or the bank's infrastructure.",
    },
  ],
}
