/**
 * Renders a FHIR DiagnosticReport JSON as a professional PDF-style medical report.
 * Opens a new window with formatted HTML and triggers print/save-as-PDF.
 */
export function generateFhirPdf(fhirJson: any, patientName?: string) {
  const dr = fhirJson?.doctorReview || {}
  const conclusion = fhirJson?.conclusion || dr.clinicalConclusion || ''
  const codes = Array.isArray(fhirJson?.conclusionCode) ? fhirJson.conclusionCode : []
  const diagnosis = codes[0]?.display || dr.overrideDiagnosis || fhirJson?.code?.text || 'N/A'
  const issued = fhirJson?.issued ? new Date(fhirJson.issued).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
  const reportId = fhirJson?.id || fhirJson?.report_id || ''
  const status = fhirJson?.status || 'final'
  const patientRef = fhirJson?.subject?.display || patientName || 'Patient'
  const doctorRef = fhirJson?.performer?.[0]?.display || dr.doctorName || 'Reviewing Physician'
  const patientSummary = dr.patientSummary || ''
  const reviewedAt = dr.reviewedAt ? new Date(dr.reviewedAt).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : ''
  const category = fhirJson?.category?.[0]?.coding?.[0]?.display || 'Radiology'
  const effectiveDate = fhirJson?.effectiveDateTime ? new Date(fhirJson.effectiveDateTime).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : issued

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Diagnostic Report — ${patientRef}</title>
<style>
  @page { margin: 20mm 15mm; size: A4; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#1a1a1a; font-size:11pt; line-height:1.5; background:#fff; padding:0; }
  .page { max-width:700px; margin:0 auto; padding:40px 0; }
  .header { border-bottom:3px solid #1e40af; padding-bottom:16px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:flex-start; }
  .header-left h1 { font-size:20pt; color:#1e40af; font-weight:700; letter-spacing:-0.5px; }
  .header-left p { font-size:9pt; color:#64748b; margin-top:2px; }
  .header-right { text-align:right; font-size:9pt; color:#64748b; }
  .header-right .status { display:inline-block; background:#dcfce7; color:#166534; padding:2px 10px; border-radius:4px; font-weight:600; text-transform:uppercase; font-size:8pt; letter-spacing:0.5px; }

  .meta-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px; }
  .meta-box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px 16px; }
  .meta-box .label { font-size:8pt; color:#94a3b8; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; margin-bottom:4px; }
  .meta-box .value { font-size:11pt; color:#0f172a; font-weight:600; }
  .meta-box .sub { font-size:9pt; color:#64748b; margin-top:2px; }

  .section { margin-bottom:20px; }
  .section-title { font-size:10pt; color:#1e40af; text-transform:uppercase; letter-spacing:1px; font-weight:700; border-bottom:1px solid #e2e8f0; padding-bottom:6px; margin-bottom:10px; }
  .section-body { font-size:11pt; color:#334155; line-height:1.7; }

  .diagnosis-box { background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:16px 20px; margin-bottom:20px; }
  .diagnosis-box .diag-label { font-size:8pt; color:#3b82f6; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; }
  .diagnosis-box .diag-value { font-size:16pt; font-weight:700; color:#1e3a5f; margin-top:4px; }
  .diagnosis-box .diag-code { font-size:9pt; color:#64748b; margin-top:4px; }

  .patient-summary { background:#f0fdf4; border-left:4px solid #22c55e; padding:14px 18px; border-radius:0 6px 6px 0; margin-bottom:20px; }
  .patient-summary .ps-label { font-size:8pt; color:#16a34a; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; margin-bottom:6px; }
  .patient-summary .ps-body { font-size:11pt; color:#334155; }

  .footer { border-top:2px solid #e2e8f0; padding-top:16px; margin-top:32px; display:flex; justify-content:space-between; font-size:8pt; color:#94a3b8; }
  .footer .sig { text-align:right; }
  .footer .sig .name { font-size:10pt; color:#0f172a; font-weight:600; }

  @media print {
    body { padding:0; }
    .page { padding:0; }
    .no-print { display:none !important; }
  }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="header-left">
      <h1>FHIR Diagnostic Report</h1>
      <p>DementiaNext AI Diagnostic Center</p>
    </div>
    <div class="header-right">
      <div class="status">${status}</div>
      <p style="margin-top:6px;">Report ID: ${reportId}</p>
      <p>Issued: ${issued}</p>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-box">
      <div class="label">Patient</div>
      <div class="value">${patientRef}</div>
    </div>
    <div class="meta-box">
      <div class="label">Reviewing Physician</div>
      <div class="value">${doctorRef}</div>
      ${reviewedAt ? `<div class="sub">Reviewed: ${reviewedAt}</div>` : ''}
    </div>
    <div class="meta-box">
      <div class="label">Category</div>
      <div class="value">${category}</div>
    </div>
    <div class="meta-box">
      <div class="label">Effective Date</div>
      <div class="value">${effectiveDate}</div>
    </div>
  </div>

  <div class="diagnosis-box">
    <div class="diag-label">Final Diagnosis</div>
    <div class="diag-value">${diagnosis}</div>
    ${codes[0]?.code ? `<div class="diag-code">SNOMED CT: ${codes[0].code} — ${codes[0].display || ''}</div>` : ''}
  </div>

  ${conclusion ? `
  <div class="section">
    <div class="section-title">Clinical Conclusion</div>
    <div class="section-body">${conclusion}</div>
  </div>
  ` : ''}

  ${patientSummary ? `
  <div class="patient-summary">
    <div class="ps-label">Patient Summary</div>
    <div class="ps-body">${patientSummary}</div>
  </div>
  ` : ''}

  <div class="footer">
    <div>
      <p>Generated by DementiaNext FHIR R4</p>
      <p>This report is for clinical use only.</p>
    </div>
    <div class="sig">
      <div class="name">${doctorRef}</div>
      <p>${reviewedAt || issued}</p>
    </div>
  </div>
</div>

<script>
  window.onload = function() { window.print(); };
</script>
</body>
</html>`

  const win = window.open('', '_blank')
  if (win) {
    win.document.write(html)
    win.document.close()
  }
}
