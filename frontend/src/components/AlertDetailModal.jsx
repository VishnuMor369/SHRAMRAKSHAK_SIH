import React, { useState, useEffect, useRef } from 'react';
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
import { respondToAlert, resolveAlert, addHSEObservation, markActionTaken, verifyAlert } from '../services/api';
import { UnifiedModal } from './common';

export default function AlertDetailModal({ alert, isOpen, onClose, currentAlerts = [] }) {
  const [remainingSec, setRemainingSec] = useState(0);
  const [loading, setLoading] = useState(false);
  const isRespondingRef = useRef(false);
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

  const isProximity = activeAlert.is_high_priority || activeAlert.type === 'Person–Vehicle Proximity';
  const isFire = activeAlert.fire_detected || activeAlert.type?.toLowerCase().includes('fire') || activeAlert.title?.toLowerCase().includes('fire');
  const isZone = activeAlert.type === 'Restricted Zone Entry' || activeAlert.title?.toLowerCase().includes('zone');
  const isWaiting = activeAlert.status === 'WAITING_FOR_RESPONSE';
  const isResponding = activeAlert.status === 'RESPONDING';
  const isEscalated = activeAlert.status === 'ESCALATED';
  const isResolved = activeAlert.status === 'RESOLVED';
  const severity = activeAlert.severity || (isProximity || isFire || isZone ? 'CRITICAL' : 'HIGH');

  const actionStatus = activeAlert.action_status || (isResolved ? 'RESOLVED' : isResponding ? 'IN_PROGRESS' : 'ASSIGNED');
  const verificationStatus = activeAlert.verification_status || (isResolved ? 'VERIFIED' : 'PENDING');

  let displayTitle = activeAlert.title || activeAlert.type;
  if (isProximity) {
    displayTitle = 'PERSON–VEHICLE PROXIMITY ALERT';
  } else if (isFire) {
    displayTitle = 'FIRE DETECTED — CONFIRMED HAZARD';
  } else if (isZone) {
    displayTitle = 'RESTRICTED ZONE BREACH';
  } else if (activeAlert.type?.includes('Helmet') || activeAlert.title?.includes('Helmet')) {
    displayTitle = 'NO HELMET DETECTED';
  }

  const pipelineStages = [
    { key: 'DETECTED', label: 'AI DETECTED' },
    { key: 'ASSIGNED', label: 'ALERT ASSIGNED' },
    { key: 'IN_PROGRESS', label: 'IN PROGRESS' },
    { key: 'COMPLETED', label: 'ACTION TAKEN' },
    { key: 'VERIFICATION', label: 'VERIFYING' },
    { key: 'VERIFIED', label: 'VERIFIED & CLOSED' }
  ];

  let activeStageIndex = 1;
  if (isResolved || verificationStatus === 'VERIFIED') activeStageIndex = 5;
  else if (verificationStatus === 'AWAITING_VERIFICATION') activeStageIndex = 4;
  else if (actionStatus === 'COMPLETED') activeStageIndex = 3;
  else if (actionStatus === 'IN_PROGRESS' || isResponding) activeStageIndex = 2;
  else if (isWaiting || actionStatus === 'ASSIGNED') activeStageIndex = 1;

  const handleRespond = async () => {
    if (loading || isRespondingRef.current || activeAlert.status !== 'WAITING_FOR_RESPONSE') return;
    try {
      isRespondingRef.current = true;
      setLoading(true);
      setError(null);
      await respondToAlert('SUP-01', notes || 'Supervisor Responding to Alert', activeAlert.id);
    } catch (err) {
      console.error('Failed to respond:', err);
      setError('Failed to record response. Please retry.');
    } finally {
      setLoading(false);
      isRespondingRef.current = false;
    }
  };

  const handleResolve = async () => {
    if (loading || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setLoading(true);
      setError(null);
      await resolveAlert('SUP-01', notes || 'Hazard verified and resolved on site', activeAlert.id);
    } catch (err) {
      console.error('Failed to resolve:', err);
      setError('Failed to resolve alert. Please retry.');
    } finally {
      setLoading(false);
      isRespondingRef.current = false;
    }
  };

  const handleActionTaken = async () => {
    if (loading || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setLoading(true);
      setError(null);
      await markActionTaken('SUP-01', notes || 'Corrective action taken on site', 'Action Taken', activeAlert.id);
    } catch (err) {
      console.error('Failed to mark action taken:', err);
      setError('Failed to record action. Please retry.');
    } finally {
      setLoading(false);
      isRespondingRef.current = false;
    }
  };

  const handleVerify = async (decision = 'VERIFIED', method = 'CCTV_VERIFIED') => {
    if (loading || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setLoading(true);
      setError(null);
      await verifyAlert('SUP-01', decision, method, notes || `Verification: ${decision}`, activeAlert.id);
    } catch (err) {
      console.error('Failed to record verification:', err);
      setError('Failed to record verification. Please retry.');
    } finally {
      setLoading(false);
      isRespondingRef.current = false;
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

  const personCropSrc = activeAlert.person_crop_url 
    || (activeAlert.person_crop_base64 ? (activeAlert.person_crop_base64.startsWith('data:') ? activeAlert.person_crop_base64 : `data:image/jpeg;base64,${activeAlert.person_crop_base64}`) : null)
    || (activeAlert.person_findings?.[0]?.evidence_crop_base64 ? (activeAlert.person_findings[0].evidence_crop_base64.startsWith('data:') ? activeAlert.person_findings[0].evidence_crop_base64 : `data:image/jpeg;base64,${activeAlert.person_findings[0].evidence_crop_base64}`) : null)
    || activeAlert.person_findings?.[0]?.evidence_crop_url
    || null;

  const vehicleCropSrc = activeAlert.vehicle_crop_url
    || (activeAlert.vehicle_crop_base64 ? (activeAlert.vehicle_crop_base64.startsWith('data:') ? activeAlert.vehicle_crop_base64 : `data:image/jpeg;base64,${activeAlert.vehicle_crop_base64}`) : null)
    || (activeAlert.vehicle_findings?.[0]?.evidence_crop_base64 ? (activeAlert.vehicle_findings[0].evidence_crop_base64.startsWith('data:') ? activeAlert.vehicle_findings[0].evidence_crop_base64 : `data:image/jpeg;base64,${activeAlert.vehicle_findings[0].evidence_crop_base64}`) : null)
    || activeAlert.vehicle_findings?.[0]?.evidence_crop_url
    || null;

  const incidentIdDisplay = activeAlert.incident_id || activeAlert.id;

  return (
    <UnifiedModal
      isOpen={isOpen}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
    >
      {/* Header */}
        <div className="px-5 py-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-3">
            <span className="text-lg leading-none">{isZone ? '🔴' : '🟠'}</span>
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                  (activeAlert.sif_potential || severity === 'CRITICAL') ? 'bg-red-500 text-white' : 'bg-amber-500 text-slate-950'
                }`}>
                  SIF POTENTIAL: {activeAlert.sif_level || (activeAlert.sif_potential ? 'HIGH' : 'LOW')}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-amber-400 border border-slate-700">
                  EVENT {activeAlert.event_id || incidentIdDisplay}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-900 text-blue-200 border border-blue-700">
                  {activeAlert.verification_type === 'CCTV_VERIFIABLE' ? 'CCTV VERIFIABLE' : 'FIELD VERIFICATION'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                  {actionStatus} / {verificationStatus}
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

          {/* SIF PRECURSOR INTELLIGENCE: WHY SIF POTENTIAL */}
          <div className="bg-red-50/80 border-2 border-red-300 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-red-200 pb-2">
              <div className="flex items-center space-x-2">
                <span className="text-base leading-none">🚨</span>
                <span className="text-xs font-black uppercase tracking-wider text-red-950">
                  SIF PRECURSOR INTELLIGENCE — WHY SIF POTENTIAL?
                </span>
              </div>
              <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-red-600 text-white">
                POTENTIAL: {activeAlert.sif_level || 'HIGH'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 text-xs">
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Hazardous Activity</span>
                <span className="font-black text-slate-900 mt-0.5 block">{activeAlert.activity || 'Industrial Operation'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Worker Exposure</span>
                <span className="font-black text-red-700 mt-0.5 block">{activeAlert.exposure || 'Personnel in hazardous area'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Critical Barrier</span>
                <span className="font-black text-slate-900 mt-0.5 block">{activeAlert.critical_barrier || 'Physical Barrier'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Barrier Condition</span>
                <span className="font-black text-red-600 mt-0.5 block">{activeAlert.barrier_condition || 'COMPROMISED / INEFFECTIVE'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Potential Consequence</span>
                <span className="font-black text-red-800 mt-0.5 block">{activeAlert.potential_consequence || 'Severe crush or impact trauma'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-red-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">IOGP Life-Saving Rule</span>
                <span className="font-black text-amber-700 mt-0.5 block">{activeAlert.life_saving_rule || 'Work Authorization & Line of Fire'}</span>
              </div>
            </div>

            {activeAlert.sif_why && activeAlert.sif_why.length > 0 && (
              <div className="bg-white p-3 rounded-lg border border-red-200 space-y-1">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Precursor Factors:</span>
                <div className="space-y-1">
                  {activeAlert.sif_why.map((reason, idx) => (
                    <div key={idx} className="flex items-start space-x-1.5 text-xs text-slate-800">
                      <span className="text-red-500 font-bold">•</span>
                      <span className="font-semibold">{reason}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* EVENT-SPECIFIC ACTION RECOMMENDATION */}
          <div className="bg-amber-50/80 border-2 border-amber-300 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-amber-200 pb-2">
              <div className="flex items-center space-x-2 text-amber-950">
                <span className="text-base leading-none">🛡️</span>
                <span className="text-xs font-black uppercase tracking-wider">
                  EVENT-SPECIFIC CORRECTIVE ACTION RECOMMENDATION
                </span>
              </div>
              <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border ${
                activeAlert.verification_type === 'CCTV_VERIFIABLE'
                  ? 'bg-blue-100 text-blue-900 border-blue-300'
                  : 'bg-purple-100 text-purple-900 border-purple-300'
              }`}>
                {activeAlert.verification_type === 'CCTV_VERIFIABLE' ? 'CCTV-Verifiable Barrier' : 'Field Inspection Required'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-white p-3 rounded-lg border border-amber-200">
                <span className="text-[10px] text-amber-800 font-black uppercase tracking-wider block mb-1">
                  IMMEDIATE ACTION REQUIRED:
                </span>
                <p className="font-black text-slate-900 leading-snug">
                  {activeAlert.immediate_action || 'Halt unsafe activity immediately and secure exclusion perimeter.'}
                </p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-amber-200">
                <span className="text-[10px] text-red-800 font-black uppercase tracking-wider block mb-1">
                  CONSEQUENCE IF NOT ADDRESSED:
                </span>
                <p className="font-bold text-red-700 leading-snug">
                  {activeAlert.consequence_if_not_addressed || 'Imminent risk of critical safety barrier failure.'}
                </p>
              </div>
            </div>
          </div>

          {/* FORMAL SAFETY VERIFICATION CARD */}
          {verificationStatus === 'AWAITING_VERIFICATION' && (
            <div className="bg-purple-50/90 border-2 border-purple-300 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-purple-200 pb-2">
                <div className="flex items-center space-x-2 text-purple-950">
                  <span className="text-base leading-none">🔍</span>
                  <span className="text-xs font-black uppercase tracking-wider">
                    SAFETY VERIFICATION IN PROGRESS (ACTION COMPLETED)
                  </span>
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-purple-600 text-white">
                  AWAITING VERIFICATION
                </span>
              </div>
              <p className="text-xs text-purple-900 font-semibold">
                Corrective action was marked completed by <b>{activeAlert.action_taken_by || 'Supervisor'}</b> at {activeAlert.action_taken_at ? new Date(activeAlert.action_taken_at).toLocaleTimeString() : 'Recorded'}. 
                {activeAlert.verification_type === 'CCTV_VERIFIABLE'
                  ? ' Exclusion zone clearance is verifiable via live CCTV or field visual inspection.'
                  : ' This action requires physical on-site verification before closure.'}
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                {activeAlert.verification_type === 'CCTV_VERIFIABLE' && (
                  <button
                    onClick={() => handleVerify('VERIFIED', 'CCTV_VERIFIED')}
                    disabled={loading}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-black text-xs rounded shadow"
                  >
                    VERIFY FIX VIA CCTV
                  </button>
                )}
                <button
                  onClick={() => handleVerify('VERIFIED', 'FIELD_VERIFIED')}
                  disabled={loading}
                  className="px-3 py-1.5 bg-purple-700 hover:bg-purple-800 text-white font-black text-xs rounded shadow"
                >
                  VERIFY ON-SITE (PHYSICAL INSPECTION)
                </button>
                <button
                  onClick={() => handleVerify('FAILED', 'FIELD_VERIFIED')}
                  disabled={loading}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-black text-xs rounded shadow"
                >
                  FAILED — REOPEN ACTION
                </button>
                <button
                  onClick={() => handleVerify('HSE_REVIEW_REQUIRED', 'FIELD_VERIFIED')}
                  disabled={loading}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white font-black text-xs rounded shadow"
                >
                  REQUEST HSE REVIEW
                </button>
              </div>
            </div>
          )}

          {verificationStatus === 'VERIFIED' && (
            <div className="bg-emerald-50 border-2 border-emerald-300 rounded-xl p-3.5 flex items-center justify-between text-emerald-950">
              <div className="flex items-center space-x-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <div>
                  <span className="text-xs font-black uppercase text-emerald-900 block">
                    FORMALLY VERIFIED & CLOSED ({activeAlert.verification_type === 'CCTV_VERIFIABLE' ? 'CCTV VERIFIED' : 'ON-SITE INSPECTED'})
                  </span>
                  <span className="text-[11px] text-emerald-800 font-semibold">
                    Verified by {activeAlert.verified_by || 'Supervisor'} • {activeAlert.verification_notes || 'All clear verified'}
                  </span>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded bg-emerald-600 text-white text-xs font-black uppercase">
                RESOLVED
              </span>
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
                    <span>{(activeAlert.person_findings?.length || activeAlert.person_count || 1)} {(activeAlert.person_findings?.length || activeAlert.person_count || 1) === 1 ? 'Person' : 'People'} Detected</span>
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 font-bold block uppercase">Timestamp</span>
                  <span className="font-bold text-slate-800 block mt-0.5">
                    {activeAlert.created_at ? new Date(activeAlert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Recorded'}
                  </span>
                </div>
              </div>

              {/* MULTI-VIOLATION BADGES */}
              {activeAlert.violations && activeAlert.violations.length > 0 && (
                <div className="pt-2 border-t border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                    Detected Safety Violations
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeAlert.violations.map((v, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-100 border border-red-300 text-red-800 flex items-center space-x-1"
                      >
                        <span>⚠</span>
                        <span>{v}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}


              {/* PPE STATUS BREAKDOWN */}
              {activeAlert.ppe_status && Object.keys(activeAlert.ppe_status).length > 0 && (
                <div className="pt-2 border-t border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">
                    PPE Verification Matrix
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-[10px]">
                    {Object.entries(activeAlert.ppe_status).map(([item, stat]) => {
                      const isViolation = stat === 'VIOLATION' || stat === 'MISSING';
                      const isClear = stat === 'COMPLIANT' || stat === 'OK';
                      return (
                        <div
                          key={item}
                          className={`p-1.5 rounded border flex items-center justify-between ${
                            isViolation
                              ? 'bg-red-50 border-red-200 text-red-800 font-bold'
                              : isClear
                              ? 'bg-emerald-50 border-emerald-200 text-emerald-800 font-bold'
                              : 'bg-slate-50 border-slate-200 text-slate-600'
                          }`}
                        >
                          <span className="capitalize">{item.replace('_', ' ')}</span>
                          <span>{isViolation ? '✗ MISSING' : isClear ? '✓ OK' : 'UNCERTAIN'}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

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

          {/* PROXIMITY EVIDENCE: PERSON & VEHICLE CROPS SIDE-BY-SIDE */}
          {isProximity && (
            <div className="bg-red-50/70 border-2 border-red-300 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-red-200 pb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-base leading-none">🚨</span>
                  <span className="text-xs font-black uppercase tracking-wider text-red-950">
                    PERSON–VEHICLE PROXIMITY EVIDENCE & CROPS
                  </span>
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-red-600 text-white animate-pulse">
                  HIGH PRIORITY • PROXIMITY CONFIRMED
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Person Evidence Crop */}
                <div className="bg-white rounded-xl border border-red-200 overflow-hidden shadow-xs flex flex-col">
                  <div className="bg-slate-900 aspect-video relative flex items-center justify-center overflow-hidden border-b border-slate-200">
                    {personCropSrc ? (
                      <img 
                        src={personCropSrc} 
                        alt={activeAlert.person_id || 'Person'} 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center p-4 text-slate-500 space-y-1">
                        <Users className="w-6 h-6 mx-auto text-slate-600" />
                        <span className="text-[10px] font-mono block">Person Evidence Crop</span>
                      </div>
                    )}
                    <div className="absolute top-2 left-2 bg-black/85 backdrop-blur-xs px-2 py-0.5 rounded text-[10px] font-black text-white border border-white/20">
                      {activeAlert.person_id || 'Person #3'}
                    </div>
                  </div>
                  <div className="p-2.5 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Detected Worker</span>
                    <span className="font-black text-slate-900">{activeAlert.person_id || 'Person #3'}</span>
                    <div className="text-[11px] text-red-700 font-bold mt-0.5">Inside Vehicle Danger Perimeter</div>
                  </div>
                </div>

                {/* Vehicle Evidence Crop */}
                <div className="bg-white rounded-xl border border-blue-200 overflow-hidden shadow-xs flex flex-col">
                  <div className="bg-slate-900 aspect-video relative flex items-center justify-center overflow-hidden border-b border-slate-200">
                    {vehicleCropSrc ? (
                      <img 
                        src={vehicleCropSrc} 
                        alt={activeAlert.vehicle_id || 'Vehicle'} 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center p-4 text-slate-500 space-y-1">
                        <Video className="w-6 h-6 mx-auto text-slate-600" />
                        <span className="text-[10px] font-mono block">Vehicle Evidence Crop</span>
                      </div>
                    )}
                    <div className="absolute top-2 left-2 bg-blue-950/90 backdrop-blur-xs px-2 py-0.5 rounded text-[10px] font-black text-blue-200 border border-blue-400/30">
                      {activeAlert.vehicle_id || 'Vehicle #1'}
                    </div>
                  </div>
                  <div className="p-2.5 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Detected Vehicle</span>
                    <span className="font-black text-slate-900">
                      {activeAlert.vehicle_id || 'Vehicle #1'} {activeAlert.vehicle_type ? `(${activeAlert.vehicle_type.toUpperCase()})` : ''}
                    </span>
                    <div className="text-[11px] text-blue-700 font-bold mt-0.5">Safety Perimeter Breached</div>
                  </div>
                </div>
              </div>

              <div className="text-[11px] text-slate-600 bg-white p-2.5 rounded-lg border border-red-200 flex items-center space-x-2">
                <span className="text-amber-500 font-bold">ℹ</span>
                <span>Camera image-space calibrated proximity zone: sustained {activeAlert.proximity_status || 'Proximity Confirmed'} over consecutive frames.</span>
              </div>
            </div>
          )}

          {/* FIRE EVIDENCE BLOCK (Feature 3) */}
          {isFire && (
            <div className="bg-orange-50/70 border-2 border-orange-300 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-orange-200 pb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-base leading-none">🔥</span>
                  <span className="text-xs font-black uppercase tracking-wider text-orange-950">
                    FIRE DETECTION EVIDENCE & STATUS
                  </span>
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-orange-600 text-white animate-pulse">
                  CRITICAL SIF HAZARD • FIRE CONFIRMED
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Fire Region Crop */}
                <div className="bg-white rounded-xl border border-orange-200 overflow-hidden shadow-xs flex flex-col">
                  <div className="bg-slate-900 aspect-video relative flex items-center justify-center overflow-hidden border-b border-slate-200">
                    {activeAlert.fire_crop_url || activeAlert.fire_crop_base64 ? (
                      <img 
                        src={activeAlert.fire_crop_url || activeAlert.fire_crop_base64} 
                        alt="Fire Region Crop" 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center p-4 text-slate-500 space-y-1">
                        <span className="text-2xl block">🔥</span>
                        <span className="text-[10px] font-mono block">Fire Region Evidence Crop</span>
                      </div>
                    )}
                    <div className="absolute top-2 left-2 bg-orange-950/90 backdrop-blur-xs px-2 py-0.5 rounded text-[10px] font-black text-orange-200 border border-orange-400/30">
                      FIRE CROP
                    </div>
                  </div>
                  <div className="p-2.5 text-xs">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Thermal Ignition Target</span>
                    <span className="font-black text-slate-900">Confirmed Open Flame</span>
                    <div className="text-[11px] text-orange-700 font-bold mt-0.5">
                      {activeAlert.fire_confidence ? `${Math.round(activeAlert.fire_confidence * 100)}% Model Confidence` : 'Sustained Temporal Confirmation'}
                    </div>
                  </div>
                </div>

                {/* Fire Response Protocol */}
                <div className="bg-white rounded-xl border border-orange-200 p-3 flex flex-col justify-between space-y-2">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold uppercase block mb-1">Emergency Protocol</span>
                    <h4 className="text-xs font-black text-slate-900 mb-1">Immediate Fire Mitigation Protocol</h4>
                    <ul className="text-[11px] text-slate-700 space-y-1 list-disc list-inside">
                      <li>Sound local emergency alarm and stop high-risk work</li>
                      <li>Evacuate all non-essential personnel from sector</li>
                      <li>Deploy designated trained fire response squad</li>
                      <li>Isolate fuel/gas manifolds and mechanical equipment</li>
                    </ul>
                  </div>
                  <div className="bg-orange-100/80 rounded p-2 text-[10px] font-mono text-orange-900 font-bold border border-orange-200">
                    Sustained fire confirmed by AI vision edge model over consecutive frames.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* PERSON-WISE EVIDENCE & INDIVIDUAL STATUS */}
          {activeAlert.person_findings && activeAlert.person_findings.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-base leading-none">📸</span>
                  <span className="text-xs font-black uppercase tracking-wider text-slate-900">
                    PERSON-WISE EVIDENCE & PPE STATUS
                  </span>
                </div>
                <div className="text-[11px] font-mono font-bold text-slate-600">
                  <span>{activeAlert.person_findings.length} People Tracked</span>
                  <span className="text-slate-300 mx-1.5">•</span>
                  <span className={activeAlert.person_findings.filter(p => p.overall_ppe_status === 'VIOLATION' || (p.violations && p.violations.length > 0)).length > 0 ? "text-red-600 font-black" : "text-emerald-600 font-bold"}>
                    {activeAlert.person_findings.filter(p => p.overall_ppe_status === 'VIOLATION' || (p.violations && p.violations.length > 0)).length} With Issues
                  </span>
                </div>
              </div>

              {/* Responsive Wrap Grid of Person-wise Evidence Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {activeAlert.person_findings.map((person) => {
                  const hasViolations = person.overall_ppe_status === 'VIOLATION' || (person.violations && person.violations.length > 0);
                  const personSrc = person.evidence_crop_url 
                    || (person.evidence_crop_base64 
                        ? (person.evidence_crop_base64.startsWith('data:') ? person.evidence_crop_base64 : `data:image/jpeg;base64,${person.evidence_crop_base64}`) 
                        : null);

                  return (
                    <div 
                      key={person.person_id}
                      className={`bg-white rounded-xl border overflow-hidden transition-all flex flex-col shadow-xs ${
                        hasViolations 
                          ? 'border-red-300 ring-1 ring-red-200' 
                          : 'border-slate-200'
                      }`}
                    >
                      {/* Person Individual Crop Image */}
                      <div className="bg-slate-900 aspect-square relative flex items-center justify-center overflow-hidden border-b border-slate-200">
                        {personSrc ? (
                          <img 
                            src={personSrc} 
                            alt={person.person_id} 
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="text-center p-4 text-slate-500 space-y-1">
                            <Camera className="w-6 h-6 mx-auto text-slate-600" />
                            <span className="text-[10px] font-mono block">Frame Crop Stored</span>
                          </div>
                        )}
                        <div className="absolute top-2 left-2 bg-black/85 backdrop-blur-xs px-2 py-0.5 rounded text-[10px] font-black text-white border border-white/20 shadow-sm">
                          {person.person_id}
                        </div>
                        <div className="absolute bottom-2 right-2">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase shadow tracking-wider ${
                            hasViolations ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                          }`}>
                            {person.overall_ppe_status || (hasViolations ? 'VIOLATION' : 'OK')}
                          </span>
                        </div>
                      </div>

                      {/* Individual Status Details */}
                      <div className="p-3 space-y-2 flex-1 flex flex-col justify-between text-xs">
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-black text-slate-900 uppercase text-xs">
                              {person.person_id}
                            </span>
                            <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded ${
                              hasViolations ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                            }`}>
                              {hasViolations ? 'PPE VIOLATION' : 'PPE OK'}
                            </span>
                          </div>

                          {/* Specific Issues / Violations list */}
                          {person.violations && person.violations.length > 0 ? (
                            <div className="space-y-1 my-1.5">
                              {person.violations.map((v, i) => (
                                <div key={i} className="text-[11px] font-black text-red-700 flex items-center space-x-1">
                                  <span>⚠</span>
                                  <span>{v.toUpperCase()}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-[11px] font-bold text-emerald-700 flex items-center space-x-1 my-1.5">
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                              <span>ALL PPE OK</span>
                            </div>
                          )}
                        </div>

                        {/* Micro PPE Matrix Breakdown (Helmet, Vest, Gloves) */}
                        <div className="grid grid-cols-3 gap-1 text-[10px] pt-2 border-t border-slate-100">
                          <div className={`p-1 rounded text-center border font-bold ${
                            person.helmet_status === 'OK' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                            person.helmet_status === 'VIOLATION' ? 'bg-red-50 border-red-200 text-red-800' :
                            'bg-slate-50 border-slate-200 text-slate-600'
                          }`}>
                            <div className="text-[8px] text-slate-400 uppercase">HELMET</div>
                            <div className="truncate">{person.helmet_status || 'OK'}</div>
                          </div>
                          <div className={`p-1 rounded text-center border font-bold ${
                            person.vest_status === 'OK' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                            person.vest_status === 'VIOLATION' ? 'bg-red-50 border-red-200 text-red-800' :
                            'bg-slate-50 border-slate-200 text-slate-600'
                          }`}>
                            <div className="text-[8px] text-slate-400 uppercase">VEST</div>
                            <div className="truncate">{person.vest_status || 'OK'}</div>
                          </div>
                          <div className={`p-1 rounded text-center border font-bold ${
                            person.glove_status === 'OK' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
                            person.glove_status === 'VIOLATION' ? 'bg-red-50 border-red-200 text-red-800' :
                            'bg-slate-50 border-slate-200 text-slate-600'
                          }`}>
                            <div className="text-[8px] text-slate-400 uppercase">GLOVES</div>
                            <div className="truncate">{person.glove_status || 'OK'}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

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

            {(isWaiting || actionStatus === 'ASSIGNED') && (
              <button
                onClick={handleRespond}
                disabled={loading || activeAlert.status !== 'WAITING_FOR_RESPONSE'}
                className="px-5 py-2 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
              >
                <span>{loading ? 'Recording...' : "ACKNOWLEDGE / I'M RESPONDING"}</span>
              </button>
            )}

            {(isResponding || actionStatus === 'IN_PROGRESS' || isEscalated) && (
              <>
                <button
                  onClick={handleActionTaken}
                  disabled={loading}
                  className="px-5 py-2 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <span>{loading ? 'Recording...' : 'ACTION TAKEN / EXECUTE FIX'}</span>
                </button>
                <button
                  onClick={handleResolve}
                  disabled={loading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-black rounded-lg text-xs transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <span>{loading ? 'Resolving...' : 'DIRECT RESOLVE'}</span>
                </button>
              </>
            )}

            {actionStatus === 'COMPLETED' && verificationStatus === 'AWAITING_VERIFICATION' && (
              <div className="flex items-center space-x-2">
                {activeAlert.verification_type === 'CCTV_VERIFIABLE' && (
                  <button
                    onClick={() => handleVerify('VERIFIED', 'CCTV_VERIFIED')}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-black rounded-lg text-xs transition-all shadow-md"
                  >
                    VERIFY VIA CCTV
                  </button>
                )}
                <button
                  onClick={() => handleVerify('VERIFIED', 'FIELD_VERIFIED')}
                  disabled={loading}
                  className="px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white font-black rounded-lg text-xs transition-all shadow-md"
                >
                  VERIFY ON-SITE
                </button>
                <button
                  onClick={() => handleVerify('FAILED', 'FIELD_VERIFIED')}
                  disabled={loading}
                  className="px-3 py-2 bg-rose-600 hover:bg-rose-700 text-white font-black rounded-lg text-xs transition-all shadow-md"
                >
                  FAILED — REOPEN
                </button>
              </div>
            )}
          </div>

        </div>
    </UnifiedModal>
  );
}
