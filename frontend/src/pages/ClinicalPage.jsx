import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, ClipboardPlus, Stethoscope } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const blankEncounter = { patient_id: '', department_id: '', encounter_type: 'consultation', chief_complaint: '' }
const blankVitals = { temperature_c: '', pulse_bpm: '', respiratory_rate: '', systolic_bp: '', diastolic_bp: '', oxygen_saturation: '', weight_kg: '', height_cm: '' }

function numberOrNull(value) { return value === '' ? null : Number(value) }

function useEncounterDetail(encounterId, suffix, enabled = true) {
  return useQuery({ queryKey: ['encounter-detail', encounterId, suffix], queryFn: () => apiRequest('/encounters/' + encounterId + '/' + suffix), enabled: Boolean(encounterId) && enabled })
}

export function ClinicalPage({ roles = [], nursingOnly = false }) {
  const isDoctor = roles.includes('doctor')
  const isNurse = roles.includes('nurse')
  const canWriteVitals = isDoctor || isNurse
  const [encounterForm, setEncounterForm] = useState(blankEncounter)
  const [selectedEncounterId, setSelectedEncounterId] = useState('')
  const [vitals, setVitals] = useState(blankVitals)
  const [diagnosis, setDiagnosis] = useState({ code: '', description: '', is_primary: false })
  const [note, setNote] = useState({ note_type: nursingOnly ? 'assessment' : 'progress', content: '' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const encounters = useQuery({ queryKey: ['encounters'], queryFn: () => apiRequest('/encounters?limit=100') })
  const patients = useQuery({ queryKey: ['patients', 'encounter-options'], queryFn: () => apiRequest('/patients?limit=100'), enabled: isDoctor || isNurse })
  const departments = useQuery({ queryKey: ['departments'], queryFn: () => apiRequest('/departments'), enabled: isDoctor && !nursingOnly })
  const vitalRows = useEncounterDetail(selectedEncounterId, 'vitals', canWriteVitals)
  const diagnoses = useEncounterDetail(selectedEncounterId, 'diagnoses', isDoctor && !nursingOnly)
  const consultationNotes = useEncounterDetail(selectedEncounterId, 'consultation-notes', isDoctor && !nursingOnly)
  const nursingNotes = useEncounterDetail(selectedEncounterId, 'nursing-notes', isNurse || nursingOnly)

  const createEncounter = useMutation({
    mutationFn: () => apiRequest('/encounters', { method: 'POST', body: {
      patient_id: encounterForm.patient_id, department_id: encounterForm.department_id || null,
      encounter_type: encounterForm.encounter_type, chief_complaint: encounterForm.chief_complaint || null,
    } }),
    onSuccess: data => { setEncounterForm(blankEncounter); setError(''); setSelectedEncounterId(data.id); client.invalidateQueries({ queryKey: ['encounters'] }) },
    onError: err => setError(err.message),
  })
  const addVitals = useMutation({
    mutationFn: () => apiRequest('/encounters/' + selectedEncounterId + '/vitals', { method: 'POST', body: Object.fromEntries(Object.entries(vitals).map(([key, value]) => [key, numberOrNull(value)]).filter(([, value]) => value !== null)) }),
    onSuccess: () => { setVitals(blankVitals); setError(''); client.invalidateQueries({ queryKey: ['encounter-detail', selectedEncounterId, 'vitals'] }) },
    onError: err => setError(err.message),
  })
  const addDiagnosis = useMutation({
    mutationFn: () => apiRequest('/encounters/' + selectedEncounterId + '/diagnoses', { method: 'POST', body: { code: diagnosis.code || null, description: diagnosis.description, is_primary: diagnosis.is_primary } }),
    onSuccess: () => { setDiagnosis({ code: '', description: '', is_primary: false }); setError(''); client.invalidateQueries({ queryKey: ['encounter-detail', selectedEncounterId, 'diagnoses'] }) },
    onError: err => setError(err.message),
  })
  const addNote = useMutation({
    mutationFn: () => apiRequest('/encounters/' + selectedEncounterId + (nursingOnly ? '/nursing-notes' : '/consultation-notes'), { method: 'POST', body: nursingOnly ? { content: note.content } : { note_type: note.note_type, content: note.content } }),
    onSuccess: () => { setNote({ note_type: nursingOnly ? 'assessment' : 'progress', content: '' }); setError(''); client.invalidateQueries({ queryKey: ['encounter-detail', selectedEncounterId, nursingOnly ? 'nursing-notes' : 'consultation-notes'] }) },
    onError: err => setError(err.message),
  })
  const encounterRows = encounters.data || []
  const patientRows = patients.data || []
  const patientById = Object.fromEntries(patientRows.map(row => [row.id, row]))

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">CLINICAL SERVICES</div><h1>{nursingOnly ? 'Nursing Station' : 'Consultations'}</h1><p className="page-description">{nursingOnly ? 'Review open encounters, record vital signs, and add append-only nursing notes.' : 'Open clinical encounters, record diagnoses and vitals, and write append-only consultation notes.'}</p></div><span className="phase-tag">Clinical roles</span></div>
    {isDoctor && !nursingOnly && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); createEncounter.mutate() }}><h2><Stethoscope size={16}/> Open encounter</h2><div className="form-grid">
      <label>Patient<select required value={encounterForm.patient_id} onChange={event => setEncounterForm({ ...encounterForm, patient_id: event.target.value })}><option value="">Choose patient</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>
      <label>Department<select value={encounterForm.department_id} onChange={event => setEncounterForm({ ...encounterForm, department_id: event.target.value })}><option value="">No department selected</option>{(departments.data || []).map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <label>Encounter type<select value={encounterForm.encounter_type} onChange={event => setEncounterForm({ ...encounterForm, encounter_type: event.target.value })}><option value="consultation">Consultation</option><option value="outpatient">Outpatient</option><option value="follow_up">Follow-up</option><option value="inpatient">Inpatient</option><option value="observation">Observation</option><option value="emergency">Emergency</option></select></label>
      <label>Chief complaint<input maxLength="5000" value={encounterForm.chief_complaint} onChange={event => setEncounterForm({ ...encounterForm, chief_complaint: event.target.value })}/></label>
    </div><button className="primary-button" type="submit" disabled={createEncounter.isPending || !patientRows.length}>{createEncounter.isPending ? 'Opening…' : 'Open encounter'}</button></form>}
    <div className="section-heading"><h2>{nursingOnly ? 'Encounter queue' : 'Clinical encounters'}</h2><span>{encounterRows.length} RECORDS</span></div>
    {encounters.isPending ? <div className="empty-state">Loading encounters…</div> : encounters.isError ? <div className="error-panel"><strong>Encounter queue unavailable</strong><p>{encounters.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Encounter</th><th>Patient</th><th>Type</th><th>Status</th><th>Chief complaint</th><th>Action</th></tr></thead><tbody>{encounterRows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{patientById[row.patient_id] ? patientById[row.patient_id].last_name + ', ' + patientById[row.patient_id].first_name : row.patient_id}</td><td>{row.encounter_type}</td><td>{row.status}</td><td>{row.chief_complaint || '—'}</td><td><button className="table-action" onClick={() => { setSelectedEncounterId(row.id); setError('') }}>Open</button></td></tr>)}</tbody></table></div>}
    {selectedEncounterId && <section className="data-form receive-panel"><div className="section-heading"><h2><Activity size={16}/> Encounter workspace</h2><button className="secondary-button" onClick={() => setSelectedEncounterId('')}>Close</button></div><p className="muted-small">Encounter ID: {selectedEncounterId}</p>
      {canWriteVitals && <form onSubmit={event => { event.preventDefault(); setError(''); addVitals.mutate() }}><h3>Record vital signs</h3><div className="form-grid">{[['temperature_c','Temperature °C'],['pulse_bpm','Pulse bpm'],['respiratory_rate','Respiratory rate'],['systolic_bp','Systolic BP'],['diastolic_bp','Diastolic BP'],['oxygen_saturation','Oxygen saturation %'],['weight_kg','Weight kg'],['height_cm','Height cm']].map(([key,label]) => <label key={key}>{label}<input type="number" step="any" value={vitals[key]} onChange={event => setVitals({ ...vitals, [key]: event.target.value })}/></label>)}</div><button className="primary-button" type="submit" disabled={addVitals.isPending}>{addVitals.isPending ? 'Saving…' : 'Save vitals'}</button></form>}
      {isDoctor && !nursingOnly && <form onSubmit={event => { event.preventDefault(); setError(''); addDiagnosis.mutate() }}><h3>Add diagnosis</h3><div className="form-grid"><label>Diagnosis code (optional)<input value={diagnosis.code} onChange={event => setDiagnosis({ ...diagnosis, code: event.target.value })}/></label><label>Description<input required minLength="2" value={diagnosis.description} onChange={event => setDiagnosis({ ...diagnosis, description: event.target.value })}/></label><label className="checkbox-inline"><input type="checkbox" checked={diagnosis.is_primary} onChange={event => setDiagnosis({ ...diagnosis, is_primary: event.target.checked })}/> Primary diagnosis</label></div><button className="primary-button" type="submit" disabled={addDiagnosis.isPending}>{addDiagnosis.isPending ? 'Saving…' : 'Save diagnosis'}</button></form>}
      {(isDoctor && !nursingOnly || isNurse || nursingOnly) && <form onSubmit={event => { event.preventDefault(); setError(''); addNote.mutate() }}><h3>{nursingOnly ? 'Add nursing note' : 'Add consultation note'}</h3><div className="form-grid"><label>Note type<select value={note.note_type} onChange={event => setNote({ ...note, note_type: event.target.value })}>{(nursingOnly ? ['assessment','progress','intervention','handover'] : ['initial','progress','follow_up','discharge']).map(type => <option key={type} value={type}>{type.replaceAll('_',' ')}</option>)}</select></label><label>Note content<textarea required minLength="2" maxLength="20000" rows="4" value={note.content} onChange={event => setNote({ ...note, content: event.target.value })}/></label></div><button className="primary-button" type="submit" disabled={addNote.isPending}>{addNote.isPending ? 'Saving…' : 'Save note'}</button></form>}
      {isDoctor && !nursingOnly && <div className="history-section"><h3>Diagnoses</h3>{diagnoses.isError ? <p className="history-empty">Could not load diagnoses.</p> : (diagnoses.data || []).map(row => <p key={row.id}>{row.description} {row.is_primary ? '· Primary' : ''}</p>)}</div>}
      {isDoctor && !nursingOnly && <div className="history-section"><h3>Consultation notes</h3>{consultationNotes.isError ? <p className="history-empty">Could not load notes.</p> : (consultationNotes.data || []).map(row => <p key={row.id}>{row.note_type}: {row.content}</p>)}</div>}
      {(isNurse || nursingOnly) && <div className="history-section"><h3>Nursing notes</h3>{nursingNotes.isError ? <p className="history-empty">Could not load notes.</p> : (nursingNotes.data || []).map(row => <p key={row.id}>{row.note_type}: {row.content}</p>)}</div>}
      {canWriteVitals && <div className="history-section"><h3>Vital sign records</h3>{vitalRows.isError ? <p className="history-empty">Could not load vitals.</p> : (vitalRows.data || []).map(row => <p key={row.id}>{row.recorded_at ? new Date(row.recorded_at).toLocaleString() : ''} · {row.temperature_c ?? '—'} °C · Pulse {row.pulse_bpm ?? '—'} · BP {row.systolic_bp ?? '—'}/{row.diastolic_bp ?? '—'}</p>)}</div>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>}
    <div className="disclaimer">Clinical notes are append-only through the API. This system has not been validated for real patient care.</div>
  </section>
}
