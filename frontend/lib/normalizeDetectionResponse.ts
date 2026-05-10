/** Raw JSON from DRF is usually snake_case; unwrap `data` and accept camelCase fallbacks. */

function asRecord(v: unknown): Record<string, unknown> | null {
  if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>
  return null
}

function pick(r: Record<string, unknown>, snake: string, camel: string): unknown {
  if (r[snake] !== undefined && r[snake] !== null) return r[snake]
  if (r[camel] !== undefined && r[camel] !== null) return r[camel]
  return undefined
}

export type NormalizedDetection = Record<string, unknown> & {
  id?: unknown
  predicted_class?: unknown
  predicted_class_display?: unknown
  confidence_score?: unknown
  processing_time?: unknown
  prediction_probability?: unknown
  analysis_details?: unknown
  created_at?: unknown
  model_version?: unknown
  model_type?: unknown
  status?: unknown
}

export function normalizeDetectionResponse(raw: unknown): NormalizedDetection {
  let r = asRecord(raw)
  if (!r) return {}

  const inner = asRecord(r.data)
  if (inner) r = inner

  const pred = pick(r, 'predicted_class', 'predictedClass')
  const conf =
    pick(r, 'confidence_score', 'confidenceScore') ??
    pick(r, 'confidence', 'confidence')
  const prob =
    pick(r, 'prediction_probability', 'predictionProbability') ??
    r.probabilities

  return {
    ...r,
    id: r.id,
    predicted_class: pred,
    predicted_class_display: pick(r, 'predicted_class_display', 'predictedClassDisplay'),
    confidence_score: conf,
    processing_time: pick(r, 'processing_time', 'processingTime'),
    prediction_probability: prob,
    analysis_details:
      pick(r, 'analysis_details', 'analysisDetails') ??
      pick(r, 'analysis', 'analysis'),
    created_at: pick(r, 'created_at', 'createdAt'),
    model_version: pick(r, 'model_version', 'modelVersion'),
    model_type: pick(r, 'model_type', 'modelType'),
    status: r.status,
  }
}
