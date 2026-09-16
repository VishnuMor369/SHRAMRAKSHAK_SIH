import React, { useState, useEffect } from 'react';
import { 
  X, 
  Clock, 
  MapPin, 
  Video, 
  Users, 
  CheckCircle2, 
  AlertOctagon, 
  Check,
  Camera,
  Plus,
  FileText,
  Brain,
  History,
  ShieldCheck,
  Activity as ActivityIcon
} from 'lucide-react';
import { respondToAlert, resolveAlert, addHSEObservation } from '../services/api';

export default function AlertDetailModal({ alert, isOpen, onClose, currentAlerts = [] }) {
  const [remainingSec, setRemainingSec] = useState(0);
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState(null);

  // HSE Observation state
  const [showHseForm, setShowHseForm] = useState(false);
  const [workerId, setWorkerId] = useState('W-104');
  const [activity, setActivity] = useState('Maintenance');
  const [location, setLocation] = useState('');
  const [observedHazard, setObservedHazard] = useState('Energized equipment');
  const [observationText, setObservationText] = useState(
    'Worker was performing maintenance near energized equipment. Isolation was not verified before maintenance activity.'
  );
  const [hseNotesText, setHseNotesText] = useState('Worker was instructed to leave the area.');
  const [submittingHse, setSubmittingHse] = useState(false);

  // Sync with real-time updates for this specific alert
  const activeAlert = currentAlerts.find(a => a.id === alert?.id) || alert;

  useEffect(() => {
    if (!activeAlert || !isOpen) return;

    if (activeAlert.location) {
      setLocation(activeAlert.location);
    }

    const updateTimer = () => {
      const now = Date.now();
      if (activeAlert.status === 'WAITING_FOR_RESPONSE') {
        const deadline = new Date(activeAlert.response_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((deadline - now) / 1000)));
      } else if (activeAlert.status === 'RESPONDING' && activeAlert.action_deadline) {
        const deadline = new Date(activeAlert.action_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((deadline - now) / 1000)));
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 250);
    return () => clearInterval(interval);
  }, [activeAlert, isOpen]);

  if (!isOpen || !activeAlert) return null;

  const isZone = activeAlert.type === 'Restricted Zone Entry' || activeAlert.title?.toLowerCase().includes('zone');
  const isWaiting = activeAlert.status === 'WAITING_FOR_RESPONSE';
  const isResponding = activeAlert.status === 'RESPONDING';
  const isEscalated = activeAlert.status === 'ESCALATED';
  const isResolved = activeAlert.status === 'RESOLVED';
  const severity = activeAlert.severity || (isZone ? 'CRITICAL' : 'HIGH');

  let displayTitle = activeAlert.title || activeAlert.type;
  if (isZone) {
    displayTitle = 'RESTRICTED ZONE BREACH';
  } else if (activeAlert.type?.includes('Helmet') || activeAlert.title?.includes('Helmet')) {
    displayTitle = 'NO HELMET DETECTED';
  }

  const pipelineStages = [
    { key: 'DETECTED', label: 'AI DETECTED' },
    { key: 'CREATED', label: 'ALERT CREATED' },
    { key: 'RESPONDING', label: 'SUPERVISOR RESPONDING' },
    { key: 'ACTION', label: 'CORRECTIVE ACTION' },
    { key: 'VERIFICATION', label: 'VERIFICATION' },
    { key: 'RESOLVED', label: 'RESOLVED' }
  ];

  let activeStageIndex = 1;
  if (isWaiting) activeStageIndex = 2;
  else if (isResponding) activeStageIndex = 3;
  else if (isEscalated) activeStageIndex = 2;
  else if (isResolved) activeStageIndex = 5;

  const handleRespond = async () => {
    try {
      setLoading(true);
      setError(null);
      await respondToAlert('SUP-01', notes || 'Supervisor Responding to Alert', activeAlert.id);
    } catch (err) {
      console.error('Failed to respond:', err);
      setError('Failed to record response. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    try {
      setLoading(true);
      setError(null);
      await resolveAlert('SUP-01', notes || 'Hazard verified and resolved on site', activeAlert.id);
    } catch (err) {
      console.error('Failed to resolve:', err);
      setError('Failed to resolve alert. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  const handleHseSubmit = async (e) => {
    e.preventDefault();
    if (!observationText.trim()) {
      setError('Observation text is required.');
      return;
    }
    try {
      setSubmittingHse(true);
      setError(null);
      await addHSEObservation(activeAlert.id, {
        worker_identifier: workerId,
        activity,
        location: location || activeAlert.location,
        hazard: observedHazard,
        observation: observationText,
        notes: hseNotesText
      });
      setShowHseForm(false);
    } catch (err) {
      console.error('Failed to add HSE observation:', err);
      setError(err.message || 'Failed to submit observation');
    } finally {
      setSubmittingHse(false);
    }
  };

  const evidenceSrc = activeAlert.evidence_image 
    ? activeAlert.evidence_image 
    : activeAlert.evidence_id 
    ? `/api/evidence/${activeAlert.evidence_id}` 
    : null;

  const incidentIdDisplay = activeAlert.incident_id || activeAlert.id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm overflow-y-auto">
      <div 
        className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full overflow-hidden transition-all my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-3">
            <span className="text-lg leading-none">{isZone ? '🔴' : '🟠'}</span>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                  severity === 'CRITICAL' ? 'bg-red-500 text-white' : 'bg-amber-500 text-slate-950'
                }`}>
                  {severity}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-amber-400 border border-slate-700">
                  INCIDENT {incidentIdDisplay}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-900 text-blue-200 border border-blue-700">
                  SOURCE: {activeAlert.source || 'AI CCTV'}
                </span>
              </div>
              <h2 className="text-sm font-black tracking-tight mt-1 uppercase">
                {displayTitle}
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {!showHseForm && (
              <button
                onClick={() => setShowHseForm(true)}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-black transition-all flex items-center space-x-1 shadow"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>ADD HSE OBSERVATION</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Content */}
        <div className="p-5 space-y-5 max-h-[82vh] overflow-y-auto">

          {/* ADD HSE OBSERVATION MODAL FORM */}
          {showHseForm && (
            <form onSubmit={handleHseSubmit} className="bg-amber-50/70 border-2 border-amber-300 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-amber-200 pb-2">
                <div className="flex items-center space-x-2 text-amber-900">
                  <FileText className="w-4 h-4 text-amber-700" />
                  <span className="text-xs font-black uppercase tracking-wider">
                    Add Manual HSE Field Observation ({incidentIdDisplay})
                  </span>
                </div>
                <button 
                  type="button" 
                  onClick={() => setShowHseForm(false)} 
                  className="text-xs font-bold text-amber-700 hover:text-amber-900"
                >
                  Cancel
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Worker Identifier</label>
                  <input
                    type="text"
                    value={workerId}
                    onChange={(e) => setWorkerId(e.target.value)}
                    placeholder="e.g. W-104"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-900"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Activity</label>
                  <input
                    type="text"
                    value={activity}
                    onChange={(e) => setActivity(e.target.value)}
                    placeholder="e.g. Maintenance"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-900"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Location</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Compressor Area"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-900"
                  />
                </div>
              </div>

              <div className="text-xs space-y-2">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Observed Hazard</label>
                  <input
                    type="text"
                    value={observedHazard}
                    onChange={(e) => setObservedHazard(e.target.value)}
                    placeholder="e.g. Worker near energized equipment without verified isolation"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-900"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Detailed Observation / Description *</label>
                  <textarea
                    rows={2}
                    value={observationText}
                    onChange={(e) => setObservationText(e.target.value)}
                    placeholder="Enter observation..."
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs text-slate-900 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Additional Notes (Optional)</label>
                  <input
                    type="text"
                    value={hseNotesText}
                    onChange={(e) => setHseNotesText(e.target.value)}
                    placeholder="e.g. Worker instructed to leave area until isolation verified"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded text-xs text-slate-900"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowHseForm(false)}
                  className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 rounded text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingHse}
                  className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-amber-400 font-black rounded text-xs transition-all shadow flex items-center space-x-1"
                >
                  <Brain className="w-3.5 h-3.5" />
                  <span>{submittingHse ? 'Analyzing with AI NLP...' : 'SUBMIT & ANALYZE OBSERVATION'}</span>
                </button>
              </div>
            </form>
          )}

          {/* RESPONSE PIPELINE WORKFLOW */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Response Pipeline
              </span>
              <span className="text-[10px] font-mono font-bold text-slate-400">
                SLA: 20s Supervisor / 60s Corrective Action
              </span>
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5 text-center">
              {pipelineStages.map((stage, idx) => {
                const isCompleted = isResolved || idx < activeStageIndex;
                const isCurrent = !isResolved && idx === activeStageIndex;

                let stateClasses = 'bg-white border-slate-200 text-slate-400';
                if (isCompleted) {
                  stateClasses = 'bg-emerald-50 border-emerald-300 text-emerald-800 font-bold';
                } else if (isCurrent) {
                  if (isEscalated) {
                    stateClasses = 'bg-purple-100 border-purple-400 text-purple-900 font-black ring-1 ring-purple-400';
                  } else if (isWaiting) {
                    stateClasses = 'bg-red-50 border-red-300 text-red-800 font-black ring-1 ring-red-300';
                  } else {
                    stateClasses = 'bg-amber-50 border-amber-300 text-amber-900 font-black ring-1 ring-amber-300';
                  }
                }

                return (
                  <div 
                    key={stage.key}
                    className={`px-1.5 py-2 rounded-lg border text-[10px] flex flex-col items-center justify-center transition-all ${stateClasses}`}
                  >
                    <div className="mb-0.5">
                      {isCompleted ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : isCurrent ? (
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping inline-block" />
                      ) : (
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300 inline-block" />
                      )}
                    </div>
                    <span className="leading-tight tracking-tight uppercase">
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SLA COUNTDOWN OR STATUS */}
          {isWaiting && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-red-950">
              <div className="flex items-center space-x-2.5">
                <Clock className="w-5 h-5 text-red-600 animate-spin-slow" />
                <div>
                  <span className="text-[11px] font-bold text-red-600 uppercase tracking-wider block">
                    Supervisor Response SLA
                  </span>
                  <span className="text-xs font-bold text-red-900">
                    Awaiting on-site acknowledgement within 20 seconds
                  </span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-2xl font-black font-mono-timer text-red-700">
                  {remainingSec}s
                </span>
              </div>
            </div>
          )}

          {isResponding && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-amber-950">
              <div className="flex items-center space-x-2.5">
                <Clock className="w-5 h-5 text-amber-600" />
                <div>
                  <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider block">
                    Corrective Action Window
                  </span>
                  <span className="text-xs font-bold text-amber-900">
                    Supervisor en route / correcting hazard within 60 seconds
                  </span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-2xl font-black font-mono-timer text-amber-800">
                  {remainingSec}s
                </span>
              </div>
            </div>
          )}

          {/* CCTV EVIDENCE & INCIDENT METADATA */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                CCTV Evidence Snapshot
              </span>
              <div className="rounded-xl border border-slate-200 bg-slate-900 overflow-hidden relative aspect-video flex items-center justify-center">
                {evidenceSrc ? (
                  <img 
                    src={evidenceSrc} 
                    alt="CCTV Alert Evidence" 
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-center p-6 space-y-1 text-slate-400">
                    <Camera className="w-8 h-8 mx-auto text-slate-500" />
                    <p className="text-xs font-bold text-slate-300">CCTV Frame Captured</p>
                    <p className="text-[11px] text-slate-500">Camera {activeAlert.camera || 'C-01'} • AI Verified</p>
                  </div>
                )}
                <div className="absolute bottom-2 left-2 bg-black/75 px-2 py-0.5 rounded text-[10px] font-mono font-bold text-white border border-white/20">
                  Camera {activeAlert.camera || 'C-01'} • {activeAlert.location || 'Site Area'}
                </div>
              </div>
            </div>

            <div className="bg-slate-50 rounded-xl border border-slate-200 p-3.5 space-y-2 text-xs">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                CCTV Alert Details
              </span>
              <div className="grid grid-cols-2 gap-2 pb-2 border-b border-slate-200">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Camera</span>
                  <span className="font-bold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <Video className="w-3.5 h-3.5 text-slate-500" />
                    <span>Camera {activeAlert.camera || 'C-01'}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Location</span>
                  <span className="font-bold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    <span>{activeAlert.location || 'Site Area'}</span>
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Personnel</span>
                  <span className="font-bold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <Users className="w-3.5 h-3.5 text-slate-500" />
                    <span>{activeAlert.person_count || 1} Person</span>
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Timestamp</span>
                  <span className="font-bold text-slate-800 block mt-0.5">
                    {activeAlert.created_at ? new Date(activeAlert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recorded'}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                  CCTV Automated Summary
                </span>
                <p className="text-xs font-semibold text-slate-800 leading-relaxed bg-white p-2 rounded border border-slate-200">
                  {activeAlert.short_summary || activeAlert.unsafe_condition || activeAlert.details || 'Safety condition detected by automated computer vision system.'}
                </p>
              </div>
            </div>
          </div>

          {/* HSE MANUAL OBSERVATION CARD */}
          {activeAlert.hse_observation_text && (
            <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-4 space-y-2.5 text-xs">
              <div className="flex items-center justify-between border-b border-blue-200 pb-2">
                <div className="flex items-center space-x-2 text-blue-900">
                  <FileText className="w-4 h-4 text-blue-600" />
                  <span className="font-black uppercase tracking-wider">HSE MANUAL FIELD OBSERVATION</span>
                </div>
                <span className="text-[10px] font-mono text-blue-700">
                  Worker: <b>{activeAlert.worker_identifier || 'N/A'}</b>
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-white p-2.5 rounded-lg border border-blue-100">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Activity</span>
                  <span className="font-bold text-slate-900">{activeAlert.hse_activity || 'Maintenance'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Observed Hazard</span>
                  <span className="font-bold text-slate-900">{activeAlert.hse_observed_hazard || 'Energized equipment'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Location</span>
                  <span className="font-bold text-slate-900">{activeAlert.hse_location || activeAlert.location}</span>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-blue-700 font-bold block uppercase mb-0.5">Observation Description</span>
                <p className="p-2.5 bg-white rounded-lg border border-blue-100 text-slate-800 font-semibold leading-relaxed">
                  "{activeAlert.hse_observation_text}"
                </p>
              </div>

              {activeAlert.hse_notes && (
                <div className="text-[11px] text-slate-600 bg-blue-100/50 p-2 rounded border border-blue-200">
                  <b>Notes:</b> {activeAlert.hse_notes}
                </div>
              )}
            </div>
          )}

          {/* AI / NLP ANALYSIS CARD */}
          {(activeAlert.nlp_sif_potential !== null && activeAlert.nlp_sif_potential !== undefined) && (
            <div className="bg-slate-900 text-white rounded-xl p-4 space-y-3 text-xs border border-slate-800">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center space-x-2">
                  <Brain className="w-4 h-4 text-amber-400" />
                  <span className="font-black uppercase tracking-wider text-amber-400">
                    AI / NLP SIF PRECURSOR ANALYSIS
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                    activeAlert.nlp_sif_potential ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                  }`}>
                    SIF POTENTIAL: {activeAlert.nlp_sif_potential ? 'HIGH / POTENTIAL' : 'LOW'}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    CONFIDENCE: {activeAlert.nlp_confidence || 85}%
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Extracted Hazard</span>
                    <span className="font-semibold text-slate-200">{activeAlert.nlp_hazard || 'Energized equipment'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Barrier Failure</span>
                    <span className="font-semibold text-red-300">{activeAlert.nlp_barrier_failure || 'Energy isolation not verified'}</span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Precursor Classification</span>
                    <span className="font-semibold text-amber-300">{activeAlert.nlp_precursor || 'Unverified Energy Isolation'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">IOGP Life-Saving Rules</span>
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {(activeAlert.nlp_life_saving_rules || ['Energy Isolation']).map((rule, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          {rule}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {activeAlert.nlp_reasoning && activeAlert.nlp_reasoning.length > 0 && (
                <div className="pt-2 border-t border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">AI Model Reasoning</span>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                    {activeAlert.nlp_reasoning.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* HISTORICAL PRECURSOR MATCH CARD */}
          {activeAlert.hse_observation_text && (
            <div className={`rounded-xl p-4 space-y-2 text-xs border ${
              activeAlert.has_historical_match 
                ? 'bg-amber-50 border-amber-300 text-amber-950' 
                : 'bg-slate-50 border-slate-200 text-slate-700'
            }`}>
              <div className="flex items-center space-x-2 font-black uppercase tracking-wider border-b pb-1.5 border-amber-200">
                <History className="w-4 h-4 text-amber-700" />
                <span>
                  {activeAlert.has_historical_match ? 'HISTORICAL PRECURSOR MATCH DETECTED' : 'HISTORICAL DATASET PATTERN ANALYSIS'}
                </span>
              </div>

              {activeAlert.has_historical_match ? (
                <div className="space-y-2">
                  <p className="font-semibold text-amber-900">
                    Recurring precursor pattern identified in OIL safety report dataset:
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-white p-2.5 rounded-lg border border-amber-200 font-mono text-[11px]">
                    <div>
                      <span className="text-[9px] font-sans text-slate-400 block uppercase">Pattern Title</span>
                      <span className="font-bold text-slate-900">{activeAlert.historical_pattern_title}</span>
                    </div>
                    <div>
                      <span className="text-[9px] font-sans text-slate-400 block uppercase">Occurrence Count</span>
                      <span className="font-bold text-slate-900">{activeAlert.historical_occurrence_count} reports</span>
                    </div>
                    <div>
                      <span className="text-[9px] font-sans text-slate-400 block uppercase">SIF Reports</span>
                      <span className="font-bold text-red-600">{activeAlert.historical_sif_count}</span>
                    </div>
                    <div>
                      <span className="text-[9px] font-sans text-slate-400 block uppercase">SIF Density</span>
                      <span className="font-bold text-amber-700">{activeAlert.historical_sif_density_pct}%</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500 italic">
                  No recurring historical precursor match found for this observation pattern in the currently active dataset.
                </p>
              )}
            </div>
          )}

          {/* INCIDENT EVIDENCE CORRELATION CARD */}
          {activeAlert.hse_observation_text && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <div className="flex items-center space-x-2 font-black uppercase text-slate-900 tracking-wider">
                  <ShieldCheck className="w-4 h-4 text-slate-700" />
                  <span>INCIDENT EVIDENCE CORRELATION (CCTV vs HSE CLAIM)</span>
                </div>
                <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                  activeAlert.evidence_consistency_status === 'CONSISTENT'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : activeAlert.evidence_consistency_status === 'INCONSISTENCY — HSE REVIEW REQUIRED'
                    ? 'bg-amber-100 text-amber-900 border-amber-300'
                    : 'bg-slate-200 text-slate-700 border-slate-300'
                }`}>
                  {activeAlert.evidence_consistency_status}
                </span>
              </div>

              <div className="space-y-1 pt-1">
                {(activeAlert.consistency_details || [
                  `Time: ${activeAlert.time_consistency || 'Aligned with CCTV alert timestamp'}`,
                  `Location: ${activeAlert.location_consistency || 'Location matches CCTV camera sector'}`,
                  `Activity: ${activeAlert.activity_consistency || 'Activity correlates with CCTV event'}`,
                  `Worker Presence: ${activeAlert.worker_presence || 'CCTV detected worker presence'}`,
                  `Coverage: ${activeAlert.coverage_status || 'CCTV Coverage Available'}`
                ]).map((det, i) => (
                  <div key={i} className="flex items-start space-x-1.5 text-slate-700 font-medium">
                    <span className="text-emerald-600 font-bold">•</span>
                    <span>{det}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CHRONOLOGICAL INCIDENT TIMELINE */}
          {activeAlert.incident_timeline && activeAlert.incident_timeline.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs">
              <div className="flex items-center space-x-2 font-black uppercase text-slate-900 tracking-wider border-b border-slate-200 pb-2">
                <ActivityIcon className="w-4 h-4 text-slate-700" />
                <span>CHRONOLOGICAL INCIDENT TIMELINE</span>
              </div>
              <div className="space-y-2 pt-1">
                {activeAlert.incident_timeline.map((item, idx) => (
                  <div key={idx} className="flex items-start space-x-3 text-xs">
                    <span className="px-2 py-0.5 rounded bg-slate-200 font-mono font-bold text-[10px] text-slate-800 shrink-0">
                      {item.time || 'N/A'}
                    </span>
                    <div>
                      <span className="font-bold text-slate-900 block">{item.title || item.event}</span>
                      {item.details && <span className="text-slate-600 text-[11px] block">{item.details}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SUPERVISOR NOTES INPUT */}
          {!isResolved && (
            <div>
              <label className="text-[11px] font-bold text-slate-700 block mb-1">
                Supervisor Action Notes (Optional):
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Worker instructed to wear helmet; isolation verified on site."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-900 focus:bg-white focus:border-slate-800 outline-none transition-all"
              />
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs font-bold">
              {error}
            </div>
          )}

          {/* WORKFLOW ACTIONS */}
          <div className="pt-2 border-t border-slate-200 flex items-center justify-end space-x-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors"
            >
              {isResolved ? 'Close' : 'Dismiss'}
            </button>

            {isWaiting && (
              <button
                onClick={handleRespond}
                disabled={loading}
                className="px-5 py-2 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
              >
                <span>{loading ? 'Recording...' : "I'M RESPONDING"}</span>
              </button>
            )}

            {isResponding && (
              <button
                onClick={handleResolve}
                disabled={loading}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
              >
                <span>{loading ? 'Resolving...' : 'FIXED / RESOLVED'}</span>
              </button>
            )}

            {isEscalated && (
              <button
                onClick={handleResolve}
                disabled={loading}
                className="px-5 py-2 bg-purple-700 hover:bg-purple-800 active:bg-purple-900 text-white font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
              >
                <span>{loading ? 'Resolving...' : 'RESOLVE ON-SITE'}</span>
              </button>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
