import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileCheck2, FileSpreadsheet, ShieldCheck, Upload } from 'lucide-react'
import { apiRequest, API_BASE_URL } from '../lib/api.js'
import { supabase } from '../lib/supabase.js'

const money = value => '₱' + Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const labels = { senior_id: 'Senior citizen ID', pwd_id: 'PWD ID', philhealth_id: 'PhilHealth ID', insurance: 'Insurance', other: 'Other' }

async function downloadExport(path, filename) {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw new Error(error.message)
  const token = data.session?.access_token
  if (!token) throw new Error('Please sign in again.')
  const response = await fetch(API_BASE_URL + path, { headers: { Authorization: 'Bearer ' + token } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || 'Export failed.')
  }
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function FinancialAssistancePage({ roles = [] }) {
  const canReview = roles.some(role => ['administrator', 'cashier'].includes(role))
  const client = useQueryClient()
  const [patientId, setPatientId] = useState('')
  const [documentType, setDocumentType] = useState('senior_id')
  const [file, setFile] = useState(null)
  const [discount, setDiscount] = useState({ bill_id: '', document_id: '', discount_type: 'senior_citizen', requested_amount: '' })
  const [estimate, setEstimate] = useState({ bill_id: '', estimate_type: 'philhealth', estimated_coverage: '0', estimated_discount: '0' })
  const [reviewNotes, setReviewNotes] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [exporting, setExporting] = useState('')

  const patients = useQuery({ queryKey: ['patients', 'financial-assistance'], queryFn: () => apiRequest('/patients?limit=100') })
  const bills = useQuery({ queryKey: ['bills', 'financial-assistance'], queryFn: () => apiRequest('/bills?limit=100') })
  const documents = useQuery({ queryKey: ['patient-documents', patientId], queryFn: () => apiRequest('/patients/' + patientId + '/documents'), enabled: Boolean(patientId) })
  const applications = useQuery({ queryKey: ['discount-applications'], queryFn: () => apiRequest('/discount-applications') })
  const estimates = useQuery({ queryKey: ['benefit-estimates'], queryFn: () => apiRequest('/benefit-estimates') })
  const patientRows = patients.data || []
  const billRows = bills.data || []
  const patientName = id => {
    const row = patientRows.find(item => item.id === id)
    return row ? row.last_name + ', ' + row.first_name : id || '—'
  }

  const upload = useMutation({
    mutationFn: () => {
      if (!patientId || !file) throw new Error('Choose a patient and a document file.')
      const body = new FormData()
      body.append('document_type', documentType)
      body.append('file', file)
      return apiRequest('/patients/' + patientId + '/documents', { method: 'POST', body })
    },
    onSuccess: () => { setFile(null); setNotice('Document uploaded and queued for verification.'); setError(''); client.invalidateQueries({ queryKey: ['patient-documents', patientId] }) },
    onError: err => setError(err.message),
  })
  const requestDiscount = useMutation({
    mutationFn: () => {
      const bill = billRows.find(row => row.id === discount.bill_id)
      if (!bill) throw new Error('Choose a bill.')
      return apiRequest('/discount-applications', { method: 'POST', body: {
        patient_id: bill.patient_id, bill_id: bill.id, discount_type: discount.discount_type,
        requested_amount: discount.requested_amount, document_id: discount.document_id || null,
      } })
    },
    onSuccess: () => { setNotice('Discount request submitted for staff review.'); setError(''); setDiscount({ bill_id: '', document_id: '', discount_type: 'senior_citizen', requested_amount: '' }); client.invalidateQueries({ queryKey: ['discount-applications'] }) },
    onError: err => setError(err.message),
  })
  const reviewDocument = useMutation({
    mutationFn: ({ id, status }) => apiRequest('/patient-documents/' + id + '/review?verification_status=' + status + '&review_notes=' + encodeURIComponent(reviewNotes), { method: 'PATCH' }),
    onSuccess: () => { setNotice('Document review saved.'); setError(''); setReviewNotes(''); client.invalidateQueries({ queryKey: ['patient-documents', patientId] }) },
    onError: err => setError(err.message),
  })
  const reviewDiscount = useMutation({
    mutationFn: ({ id, status, amount }) => apiRequest('/discount-applications/' + id + '/review', { method: 'PATCH', body: { status, approved_amount: status === 'approved' ? amount : '0', review_notes: reviewNotes || null } }),
    onSuccess: () => { setNotice('Discount decision saved.'); setError(''); setReviewNotes(''); client.invalidateQueries({ queryKey: ['discount-applications'] }); client.invalidateQueries({ queryKey: ['bills'] }); client.invalidateQueries({ queryKey: ['bill-balance'] }) },
    onError: err => setError(err.message),
  })
  const createEstimate = useMutation({
    mutationFn: () => {
      const bill = billRows.find(row => row.id === estimate.bill_id)
      if (!bill) throw new Error('Choose a bill.')
      return apiRequest('/benefit-estimates', { method: 'POST', body: {
        patient_id: bill.patient_id, bill_id: bill.id, estimate_type: estimate.estimate_type,
        estimated_coverage: estimate.estimated_coverage, estimated_discount: estimate.estimated_discount,
        rules_version: 'manual-estimate-v1',
      } })
    },
    onSuccess: () => { setNotice('Estimate saved. It is not an official PhilHealth determination.'); setError(''); client.invalidateQueries({ queryKey: ['benefit-estimates'] }) },
    onError: err => setError(err.message),
  })

  async function exportData(path, filename) {
    setExporting(filename); setError(''); setNotice('')
    try { await downloadExport(path, filename); setNotice('Export downloaded.') }
    catch (err) { setError(err.message) }
    finally { setExporting('') }
  }
  async function openDocument(id) {
    try {
      const result = await apiRequest('/patient-documents/' + id + '/signed-url')
      window.open(result.url, '_blank', 'noopener,noreferrer')
    } catch (err) { setError(err.message) }
  }

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">FINANCIAL MANAGEMENT</div><h1>Discounts & Benefits</h1><p className="page-description">Verify supporting documents, review discount requests, estimate deductions, and export authorized financial records.</p></div><span className="phase-tag"><ShieldCheck size={14}/> Staff access</span></div>
    {error && <div className="error-panel" role="alert"><strong>Action could not be completed</strong><p>{error}</p></div>}
    {notice && <div className="success-panel" role="status"><FileCheck2 size={16}/><span>{notice}</span><button className="table-action" onClick={() => setNotice('')}>Dismiss</button></div>}

    <section className="data-form">
      <h2><Upload size={16}/> Supporting ID documents</h2>
      <div className="form-grid">
        <label>Patient<select required value={patientId} onChange={event => setPatientId(event.target.value)}><option value="">Choose patient</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>
        <label>Document type<select value={documentType} onChange={event => setDocumentType(event.target.value)}>{Object.entries(labels).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
        <label>File (PDF, JPG, PNG; max 10 MB)<input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" onChange={event => setFile(event.target.files?.[0] || null)}/></label>
      </div>
      <button className="primary-button" disabled={upload.isPending || !patientId || !file} onClick={() => upload.mutate()}>{upload.isPending ? 'Uploading…' : 'Upload document'}</button>
      {patientId && <div className="history-section"><h3>Documents for {patientName(patientId)}</h3>{documents.isPending ? <p>Loading documents…</p> : documents.isError ? <p className="form-error">{documents.error.message}</p> : !documents.data?.length ? <p>No supporting documents uploaded.</p> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>File</th><th>Type</th><th>Status</th><th>Uploaded</th><th>Actions</th></tr></thead><tbody>{documents.data.map(row => <tr key={row.id}><td>{row.original_filename}</td><td>{labels[row.document_type] || row.document_type}</td><td>{row.verification_status}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td><td><div className="row-actions"><button className="table-action" onClick={() => openDocument(row.id)}>View securely</button>{canReview && row.verification_status === 'pending' && <><button className="table-action" onClick={() => reviewDocument.mutate({ id: row.id, status: 'approved' })}>Approve</button><button className="table-action" onClick={() => reviewDocument.mutate({ id: row.id, status: 'rejected' })}>Reject</button></>}</div></td></tr>)}</tbody></table></div>}</div>}
    </section>

    <section className="data-form">
      <h2>Request a bill deduction</h2><p className="page-description">Requests require review. An approved amount is applied to the selected bill by the server.</p>
      <form onSubmit={event => { event.preventDefault(); requestDiscount.mutate() }}><div className="form-grid">
        <label>Bill<select required value={discount.bill_id} onChange={event => { const bill = billRows.find(row => row.id === event.target.value); setDiscount({ ...discount, bill_id: event.target.value, document_id: '' }); if (bill) setPatientId(bill.patient_id) }}><option value="">Choose bill</option>{billRows.filter(row => ['open', 'partially_paid'].includes(row.status)).map(row => <option key={row.id} value={row.id}>{row.bill_number} · {patientName(row.patient_id)} · {money(row.total)}</option>)}</select></label>
        <label>Deduction type<select value={discount.discount_type} onChange={event => setDiscount({ ...discount, discount_type: event.target.value })}><option value="senior_citizen">Senior citizen</option><option value="pwd">PWD</option><option value="philhealth">PhilHealth</option><option value="insurance">Insurance</option><option value="other">Other</option></select></label>
        <label>Requested amount (PHP)<input type="number" min="0" step="0.01" required value={discount.requested_amount} onChange={event => setDiscount({ ...discount, requested_amount: event.target.value })}/></label>
        <label>Verified supporting document<select value={discount.document_id} onChange={event => setDiscount({ ...discount, document_id: event.target.value })}><option value="">No document linked</option>{(documents.data || []).filter(row => row.verification_status === 'approved').map(row => <option key={row.id} value={row.id}>{labels[row.document_type] || row.document_type} · {row.original_filename}</option>)}</select></label>
      </div><button className="primary-button" disabled={requestDiscount.isPending}>{requestDiscount.isPending ? 'Submitting…' : 'Submit discount request'}</button></form>
      <div className="history-section"><h3>Discount requests</h3>{applications.isPending ? <p>Loading requests…</p> : applications.isError ? <p className="form-error">{applications.error.message}</p> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Patient</th><th>Bill</th><th>Type</th><th>Requested</th><th>Approved</th><th>Status</th>{canReview && <th>Decision</th>}</tr></thead><tbody>{(applications.data || []).map(row => <tr key={row.id}><td>{patientName(row.patient_id)}</td><td>{row.bill_id || '—'}</td><td>{row.discount_type}</td><td>{money(row.requested_amount)}</td><td>{money(row.approved_amount)}</td><td>{row.status}</td>{canReview && <td>{row.status === 'pending' ? <div className="row-actions"><button className="table-action" onClick={() => reviewDiscount.mutate({ id: row.id, status: 'approved', amount: row.requested_amount })}>Approve full</button><button className="table-action" onClick={() => reviewDiscount.mutate({ id: row.id, status: 'rejected', amount: 0 })}>Reject</button></div> : '—'}</td>}</tr>)}</tbody></table></div>}</div>
    </section>

    <section className="data-form">
      <h2>Deduction & PhilHealth estimate calculator</h2><p className="page-description">Enter a proposed coverage and discount to estimate the remaining balance. This is not an official PhilHealth claim or guarantee of benefits.</p>
      <form onSubmit={event => { event.preventDefault(); createEstimate.mutate() }}><div className="form-grid">
        <label>Bill<select required value={estimate.bill_id} onChange={event => setEstimate({ ...estimate, bill_id: event.target.value })}><option value="">Choose bill</option>{billRows.map(row => <option key={row.id} value={row.id}>{row.bill_number} · {patientName(row.patient_id)} · {money(row.total)}</option>)}</select></label>
        <label>Estimate type<select value={estimate.estimate_type} onChange={event => setEstimate({ ...estimate, estimate_type: event.target.value })}><option value="philhealth">PhilHealth estimate</option><option value="insurance">Insurance estimate</option><option value="discount">Discount estimate</option></select></label>
        <label>Estimated coverage (PHP)<input type="number" min="0" step="0.01" required value={estimate.estimated_coverage} onChange={event => setEstimate({ ...estimate, estimated_coverage: event.target.value })}/></label>
        <label>Additional discount (PHP)<input type="number" min="0" step="0.01" required value={estimate.estimated_discount} onChange={event => setEstimate({ ...estimate, estimated_discount: event.target.value })}/></label>
      </div><button className="primary-button" disabled={createEstimate.isPending}>{createEstimate.isPending ? 'Calculating…' : 'Calculate & save estimate'}</button></form>
      <div className="history-section"><h3>Saved estimates</h3>{estimates.isPending ? <p>Loading estimates…</p> : estimates.isError ? <p className="form-error">{estimates.error.message}</p> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Patient</th><th>Type</th><th>Gross</th><th>Coverage</th><th>Discount</th><th>Estimated balance</th></tr></thead><tbody>{(estimates.data || []).map(row => <tr key={row.id}><td>{patientName(row.patient_id)}</td><td>{row.estimate_type}</td><td>{money(row.gross_amount)}</td><td>{money(row.estimated_coverage)}</td><td>{money(row.estimated_discount)}</td><td><strong>{money(row.estimated_patient_balance)}</strong></td></tr>)}</tbody></table></div>}</div>
    </section>

    <section className="data-form">
      <h2><FileSpreadsheet size={16}/> Authorized exports</h2><p className="page-description">Exports are authenticated, role-restricted, and recorded in the audit trail.</p>
      <div className="row-actions">{[['/exports/patients.xlsx','patients.xlsx','Patients (Excel)'],['/exports/appointments.xlsx','appointments.xlsx','Appointments (Excel)'],['/exports/bills.xlsx','bills.xlsx','Bills (Excel)'],['/exports/payments.xlsx','payments.xlsx','Payments (Excel)'],['/exports/inventory.xlsx','inventory.xlsx','Inventory (Excel)'],['/exports/statistics.xlsx','statistics.xlsx','Statistics (Excel)'],['/exports/bills.csv','bills.csv','Bills (CSV)'],['/exports/payments.csv','payments.csv','Payments (CSV)']].map(([path, filename, label]) => <button key={path} className="secondary-button" disabled={Boolean(exporting)} onClick={() => exportData(path, filename)}>{exporting === filename ? 'Exporting…' : label}</button>)}</div>
    </section>
  </section>
}
