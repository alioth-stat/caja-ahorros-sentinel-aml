# Sentinel-AML — Reto Caja de Ahorros

Agente QVAC para el reto corporativo **"Soluciones de AI Descentralizada para la Banca"**
de Caja de Ahorros (Decentralized AI Hackathon, ISD Summit Panamá). Se conecta como
consumidor adicional de un stream de transacciones bancarias y detecta patrones de fraude
y lavado de dinero (AML) en tiempo real, con toda la inferencia corriendo on-device.

## Reuso (requerido por las reglas del hackathon)

Este proyecto reutiliza base de dos submissions previas del mismo equipo, en este mismo
hackathon:

De [`Challenges/phillips-installed-base-intelligence/`](../phillips-installed-base-intelligence):
- `qvac_client.py`, copiado sin cambios.
- La forma de `api.py`/`db.py` (FastAPI delgado, sqlite plano).
- Frontend: `Background.tsx`, `GlassPanel.tsx`, `GlassSurface.tsx`, `GradientWaves.tsx` y
  sus dependencias, `ui/badge.tsx`, `ui/table.tsx`.

De [`Challenges/ovnicom-sentinel-dns/`](../ovnicom-sentinel-dns) — no solo código, sino la
**arquitectura completa del pipeline** (stream → heurísticos → veredicto QVAC →
dashboard), adaptada de detección de amenazas DNS a detección de fraude transaccional:
- `detectors.py` → mismo rol (filtrar candidatos con reglas baratas antes de llamar a
  QVAC), heurísticos nuevos para el dominio bancario.
- `qvac_judge.py` → mismo patrón (JSON-schema-constrained decoding, reintento de 2
  intentos, fallback seguro), esquema y prompt nuevos.
- `pipeline.py` → misma forma exacta (tarea de fondo en el lifespan de FastAPI,
  `run_in_executor` para no bloquear el loop).
- `wazuh_sink.py` → `compliance_sink.py`, mismo patrón de log JSON, reencuadrado como cola
  de casos de cumplimiento en vez de regla de SIEM.
- `run.sh` (selección automática de puerto libre) y el panel de Transparencia y glosario
  (`VisibilityPanel.tsx`) → reusados con contenido nuevo.

Repo independiente por decisión del equipo, igual que Ovnicom.

## Cómo funciona

1. `generator.py` simula ~150 cuentas bancarias sintéticas, cada una con su propio perfil
   (escala de monto, beneficiarios conocidos, sucursal/canal habitual), y emite un stream de
   transacciones a ~10/s (el stand-in de demo para los ~600 tx/s reales de Caja de Ahorros —
   10/s es lo demostrable en una máquina de desarrollo). La distribución de montos (log-normal,
   media ~$298, cola larga) y la mezcla de canales (Sucursal/ATM/Online) están calibradas
   contra el dataset público de Kaggle **["Bank Transaction Dataset for Fraud
   Detection"](https://www.kaggle.com/datasets/valakhorasani/bank-transaction-dataset-for-fraud-detection)**
   (valakhorasani, 2,512 transacciones) — se usaron solo sus estadísticos (media, desviación,
   proporciones por canal), nunca sus filas; ninguna fila de ese dataset está en este repo.
   ~5% del volumen son ráfagas de anomalías inyectadas deliberadamente.
2. `detectors.py` filtra el stream con 5 heurísticos baratos, sin modelo, a la velocidad
   completa del stream: **estructuración** (transferencias justo debajo de un umbral),
   **velocidad anómala**, **beneficiario nuevo** con monto grande, **anomalía de
   sucursal/canal**, y **layering** (depósito grande seguido de transferencias salientes a
   beneficiarios nuevos).
3. QVAC (Qwen3-1.7B-Instruct, local) da veredicto final, confianza y motivo en español para
   cada candidato filtrado. QVAC es el recurso lento del pipeline (~15-25s por veredicto en
   esta máquina, serializado por diseño en `qvac_client.py`), así que `pipeline.py` separa la
   ingesta (rápida, al ritmo del stream) del juicio de QVAC (una cola independiente, drenada
   a su propio ritmo) — meterlos en el mismo loop, como hace Ovnicom Sentinel-DNS, dejaría la
   ingesta esperando a QVAC.
4. **Política de decisión por confianza**: un veredicto no-benigno con **85% de confianza o
   más** se trata como suficientemente seguro para actuar solo — la cuenta se congela
   automáticamente (`db.freeze_account`) y se notifica de inmediato (banner en el dashboard).
   Por debajo de ese umbral, la alerta queda en la cola de revisión manual (`tier=review`)
   para un analista. Las transacciones de una cuenta ya congelada se rechazan de inmediato,
   sin gastar heurísticos ni QVAC en ellas.
5. Todo veredicto sospechoso (no benigno) se guarda en sqlite y en `compliance_case_log.log`.
6. El dashboard muestra un stream de transacciones en vivo (normal/en revisión/bloqueada) y
   una tabla de alertas confirmadas, con conteos y estadísticas de rendimiento (tx/s, cola
   pendiente para QVAC, cuentas congeladas).

## On-device, sin excepciones

`qvac_judge.classify` corre 100% local vía `tetherto.qvac_sdk`. El código no usa
`requests`/`urllib`/`httpx` ni abre sockets salientes. Desconecta la red de la máquina y
sigue funcionando igual — ningún dato de cliente sale del dispositivo ni de la
infraestructura del banco.

## Datos

100% sintéticos, generados en `generator.py`. No se usa ni se necesita ningún dato real de
clientes de ninguna entidad financiera, conforme a las reglas del reto. Los montos, cuentas,
beneficiarios y sucursales son ficticios.

## Real vs. simulado

| En un banco real | Aquí |
|---|---|
| Núcleo bancario (core banking) | `generator.py`, stream sintético de transacciones |
| Motor de reglas + modelo de riesgo | `detectors.py` + `qvac_judge.py` |
| Base de datos transaccional | sqlite (`db.py`) |
| Consola de analista AML | Dashboard React, polling cada 3s |
| Cola de casos de cumplimiento | `compliance_case_log.log`: JSON que un sistema de casos real puede leer directamente |

## Interfaz

Dashboard React de una sola pantalla. Paneles con efecto de vidrio (`GlassSurface`, React
Bits) sobre un fondo animado (`GradientWaves`, React Bits vía `ogl`). Selector ES/EN para la
interfaz; el contenido del modelo (veredicto, motivo) siempre queda en español.

Un botón abre un panel de **Transparencia y glosario**: explica el pipeline paso a paso y
define cada término (estructuración, layering, AML, UAF, etc.) en pantalla.

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

Si el worker de QVAC no aparece solo: `.venv/bin/python -m tetherto.qvac_sdk install-worker`

## Ejecutar

```bash
./run.sh
```

Detecta puertos libres automáticamente (útil si otras submissions del mismo workspace ya
están corriendo en 8000/5173); imprime los puertos reales al arrancar. Ctrl+C detiene ambos
servidores. El stream de transacciones (~10/s) arranca de inmediato; la primera clasificación
de QVAC tarda ~50s (carga del modelo), así que la tabla de alertas confirmadas queda vacía
hasta entonces aunque el stream ya se vea corriendo.

Manual: `.venv/bin/uvicorn api:app --port 8000` y `cd frontend && npm run dev`.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Lógica pura de los 5 heurísticos. Sin modelo, corre en milisegundos.

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `qvac_client.py` | Conexión y carga de modelos vía QVAC SDK (reusado de Philips) |
| `generator.py` | Stream sintético de cuentas y transacciones a ~10 tx/s, con anomalías inyectadas |
| `detectors.py` | 5 heurísticos que filtran candidatos antes de gastar una llamada a QVAC |
| `qvac_judge.py` | Veredicto estructurado de QVAC sobre los candidatos filtrados |
| `db.py` | sqlite (alertas + cuentas congeladas) |
| `compliance_sink.py` | Alertas confirmadas como JSON, formato ingerible por un sistema de casos |
| `pipeline.py` | Dos tareas de fondo: ingesta rápida (heurísticos, congelamiento) + juicio QVAC en cola |
| `api.py` | FastAPI: `/api/feed`, `/api/alerts`, `/api/frozen`, `/api/stats` |
| `frontend/` | Dashboard React (Vite + TypeScript + Tailwind + shadcn/ui) |

## Limitaciones conocidas

- Los 5 heurísticos usan umbrales fijos calibrados para el ritmo de esta demo, no
  calibración estadística sobre datos reales.
- El umbral de estructuración ($10,000) es un valor de demo, no una cita de un umbral
  regulatorio real de ningún país. El umbral de congelamiento automático (85% de confianza)
  también es un valor de demo, elegido para que el flujo sea visible, no una recomendación
  de política de riesgo.
- `layering` depende de que el depósito grande y la transferencia saliente caigan dentro
  de la misma ventana de 30s del pipeline; en tráfico muy disperso puede no coincidir.
- QVAC solo juzga ~1 transacción cada 15-25s en esta máquina (una limitación de hardware, no
  del diseño): a 10 tx/s con ~5% de anomalías, la cola de revisión pendiente crece durante la
  demo. Es una limitación real y visible (`stats.pending_review`), no oculta.
- El primer intento de veredicto del modelo, en frío, a veces confirmaba el kind equivocado
  (mismo problema de fondo que Ovnicom documenta con dga/typosquat): mostrarle al modelo el
  diccionario completo de señales heurísticas lo confundía más que ayudarlo. Se corrigió
  pasándole solo el tipo de sospecha ya determinado por el heurístico como un hecho a
  confirmar/reclasificar, no una lista de puntajes a comparar (ver `qvac_judge._format_candidate`).

## Guión de demo (para el video)

1. Dashboard recién levantado con el stream en vivo vacío (~50s de carga del modelo).
2. Desconectar la red de la máquina en cámara, antes de la primera alerta.
3. Mostrar el stream de transacciones corriendo a ~10/s, la mayoría normales.
4. Esperar alertas de varios tipos: structuring, velocity_anomaly, new_payee_risk,
   geo_channel_anomaly, layering — y al menos una de alta confianza para ver el banner de
   congelamiento automático en rojo.
5. Abrir el panel de Transparencia y glosario.
6. `tail -f compliance_case_log.log` en una terminal.
7. Mencionar el reuso de la base de Philips y de la arquitectura de Ovnicom Sentinel-DNS, y
   la calibración de datos contra el dataset público de Kaggle.

## Fuera de alcance (deliberado)

- Núcleo bancario / base de datos transaccional real, sistema de casos real: sustituidos
  como en la tabla de arriba.
- Calibración estadística de umbrales sobre datos históricos reales: no hay datos reales
  disponibles ni permitidos para este reto.
- Un sexto heurístico de "cuenta mula" (muchas entradas pequeñas seguidas de una salida
  grande) quedó fuera del alcance por tiempo; `layering` ya cubre el caso más común
  (depósito grande → salidas rápidas).
