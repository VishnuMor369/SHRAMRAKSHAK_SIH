import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, 
  MapPin, 
  Video, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  ArrowRight, 
  RotateCcw, 
  Check, 
  X, 
  AlertOctagon,
  Eye,
  History,
  Activity,
  Layers,
  Sparkles
} from 'lucide-react';
import { 
  respondToAlert, 
  markActionTaken, 
  verifyAlert, 
  verifyCctvCondition, 
  fetchAlertHistory 
} from '../services/api';

export default function Supervisor({ stateData }) {
  const status = stateData?.status;
  const isConnected = stateData?.isConnected;

  const rawActiveAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);
  const emergencyAlerts = rawActiveAlerts.filter(a => a.alert_class !== 'PATTERN_ACTION');
  const patternActions = rawActiveAlerts.filter(a => a.alert_class === 'PATTERN_ACTION');
  const activeAlert = emergencyAlerts[0] || null;
  const activePatternAction = patternActions[0] || null;

  // Active view: 'operational' | 'history'
  const [activeTab, setActiveTab] = useState('operational');
  
  // Operational step progression within the 2-3 second mobile flow:
  // 'INITIAL' -> 'ACTION_REQUIRED' -> 'IN_PROGRESS' -> 'AWAITING_VERIFICATION' -> 'VERIFIED' | 'FAILED'
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [showDeepDetails, setShowDeepDetails] = useState(false);

  // History state
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // SLA timer
  const [remainingSec, setRemainingSec] = useState(20);

  useEffect(() => {
    if (!activeAlert) return;
    const updateTimer = () => {
      const now = Date.now();
      if (activeAlert.status === 'WAITING_FOR_RESPONSE' && activeAlert.response_deadline) {
        const dl = new Date(activeAlert.response_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((dl - now) / 1000)));
      } else if (activeAlert.action_deadline) {
        const dl = new Date(activeAlert.action_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((dl - now) / 1000)));
      }
    };
    updateTimer();
    const interval = setInterval(updateTimer, 250);
    return () => clearInterval(interval);
  }, [activeAlert]);

  const loadHistory = async () => {
    try {
      setLoadingHistory(true);
      const res = await fetchAlertHistory();
      setHistoryList(res?.history || res?.alerts || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  // Operational Action Handlers (Connecting to Backend State)
  const handleAcknowledge = async () => {
    if (!activeAlert || submitting) return;
    try {
      setSubmitting(true);
      await respondToAlert('SUP-FIELD-01', 'Supervisor acknowledged alert and en route', activeAlert.id);
      setFeedback({ type: 'success', text: 'Acknowledged. Moving on-site.' });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to acknowledge' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleActionTaken = async (alertId = null) => {
    const targetId = alertId || activeAlert?.id;
    if (!targetId || submitting) return;
    try {
      setSubmitting(true);
      await markActionTaken('SUP-FIELD-01', 'Worker cleared from exclusion zone; lift paused', 'Action Taken', targetId);
      setFeedback({ type: 'success', text: 'Action taken. Awaiting CCTV verification.' });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to mark action' });
    } finally {
      setSubmitting(false);
    }
  };

  const handlePatternActionCompleted = async (alertId) => {
    if (!alertId || submitting) return;
    try {
      setSubmitting(true);
      await markActionTaken('SUP-FIELD-01', 'Personnel cleared and restricted boundary secured as assigned by HSE', 'Zone Secured', alertId);
      setFeedback({ type: 'success', text: 'Pattern Action reported completed. Status: Awaiting Verification.' });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to mark action completed' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCctvVerify = async (simulateRebreach = false, alertId = null) => {
    const targetId = alertId || activeAlert?.id || activePatternAction?.id;
    if (!targetId || submitting) return;
    try {
      setSubmitting(true);
      const res = await verifyCctvCondition(targetId, simulateRebreach, 'SUP-FIELD-01');
      if (res.verified) {
        setFeedback({ type: 'success', text: '✓ VERIFIED: Observable zone clearance confirmed!' });
      } else {
        setFeedback({ type: 'error', text: '✕ VERIFICATION FAILED: Re-breach detected in zone! Action reopened.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Verification check failed' });
    } finally {
      setSubmitting(false);
    }
  };

  const isWaiting = activeAlert?.status === 'WAITING_FOR_RESPONSE';
  const isResponding = activeAlert?.status === 'RESPONDING' || activeAlert?.action_status === 'IN_PROGRESS';
  const isAwaitingVerification = activeAlert?.verification_status === 'AWAITING_VERIFICATION' || activeAlert?.lifecycle_state === 'AWAITING_VERIFICATION';
  const isResolved = activeAlert?.status === 'RESOLVED' || activeAlert?.verification_status === 'VERIFIED';

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans max-w-md mx-auto border-x border-slate-800 shadow-2xl">
      
      {/* Mobile Top App Bar */}
      <header className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-black tracking-wider uppercase text-white">
              SHRAMRAKSHAK • SUPERVISOR
            </h1>
            <span className="text-[10px] text-slate-400 font-mono">
              Unit: SUP-01 • Rig 04 Deck
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab(activeTab === 'operational' ? 'history' : 'operational')}
            className={`p-1.5 rounded-lg border text-[11px] font-bold transition-colors ${
              activeTab === 'history' 
                ? 'bg-amber-500 text-slate-950 border-amber-500' 
                : 'bg-slate-800 text-slate-300 border-slate-700'
            }`}
          >
            {activeTab === 'operational' ? 'History' : 'Live'}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 flex flex-col justify-center">

        {feedback && (
          <div className={`mb-3 p-3 rounded-xl border text-xs font-bold flex items-center justify-between animate-fade-in ${
            feedback.type === 'success' 
              ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200' 
              : 'bg-red-950/80 border-red-500 text-red-200'
          }`}>
            <span>{feedback.text}</span>
            <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
        )}

        {/* VIEW 1: HISTORY */}
        {activeTab === 'history' ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-300">
                Resolved Event Audit Log ({historyList.length})
              </h2>
              <button onClick={loadHistory} className="text-[11px] text-amber-400 hover:underline">
                Refresh
              </button>
            </div>

            {loadingHistory ? (
              <p className="text-xs text-slate-500 text-center py-8">Loading history...</p>
            ) : historyList.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-8">No previous events logged.</p>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-[70vh]">
                {historyList.map(h => (
                  <div key={h.id} className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold text-amber-400">{h.id}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {h.verification_status || 'VERIFIED'}
                      </span>
                    </div>
                    <p className="text-xs font-bold text-white line-clamp-1">{h.title || h.type}</p>
                    <p className="text-[10px] text-slate-400">{h.location} • Verified by {h.verified_by || 'Supervisor'}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* VIEW 2: OPERATIONAL ALERT CONSOLE (Dual Alert Class Architecture) */
          <div className="space-y-4">
            {!activeAlert && !activePatternAction ? (
              /* All Clear State */
              <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h2 className="text-base font-black tracking-tight text-white uppercase">
                  Perimeter Nominal
                </h2>
                <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
                  Zero active zone violations or pending corrective actions. Active surveillance monitoring Camera C-01.
                </p>
                <div className="pt-2">
                  <span className="inline-block px-2.5 py-1 rounded bg-slate-800 text-slate-400 text-[10px] font-mono">
                    Node: C-01 • Ground-Contact Active
                  </span>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                
                {/* ======================================================== */}
                {/* CLASS 1 — LIVE CCTV EMERGENCY ALERT                      */}
                {/* ======================================================== */}
                {activeAlert && (
                  <div className="space-y-3">
                    {/* Header Card (2-Second Visual Anchor) */}
                    <div className="p-5 rounded-2xl bg-red-950/90 border-2 border-red-500 shadow-lg shadow-red-950/50 space-y-3 animate-fade-in">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black uppercase tracking-wider text-red-300 flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping inline-block" />
                          🔴 EMERGENCY — LIVE SAFETY ALERT
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white font-mono">
                          SIF: {activeAlert.sif_level || 'CRITICAL'}
                        </span>
                      </div>

                      {/* Primary Narrative */}
                      <div>
                        <h2 className="text-lg font-black tracking-tight text-white leading-snug">
                          {activeAlert.short_summary || activeAlert.title || 'Worker entered lifting exclusion zone.'}
                        </h2>
                        <span className="text-xs text-red-200 mt-1 block">
                          Location: <b>{activeAlert.location || 'Lifting Zone 03'}</b> • Camera {activeAlert.camera || 'C-01'}
                        </span>
                      </div>

                      {/* Action Directive */}
                      <div className="p-3 bg-red-900/60 rounded-xl border border-red-700/80">
                        <span className="text-[10px] font-black uppercase tracking-wider text-red-200 block mb-0.5">
                          IMMEDIATE ACTION DIRECTIVE
                        </span>
                        <p className="text-xs font-black text-white">
                          {activeAlert.immediate_action || 'Stop/hold lifting and clear the exclusion zone.'}
                        </p>
                      </div>

                      {/* Timer */}
                      {isWaiting && (
                        <div className="flex items-center justify-between text-[11px] text-red-200 pt-1">
                          <span>Response SLA Countdown:</span>
                          <span className="text-lg font-mono font-black text-white">{remainingSec}s</span>
                        </div>
                      )}
                    </div>

                    {/* Operational Action Console for Emergency Alert */}
                    <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
                      {isWaiting && (
                        <div className="space-y-2">
                          <button
                            onClick={handleAcknowledge}
                            disabled={submitting}
                            className="w-full py-3.5 bg-red-600 hover:bg-red-500 active:bg-red-700 text-white font-black text-sm rounded-xl shadow-lg transition-transform active:scale-95 flex items-center justify-center space-x-2"
                          >
                            <Clock className="w-4 h-4" />
                            <span>[ I'M RESPONDING — ON SITE ]</span>
                          </button>
                        </div>
                      )}

                      {isResponding && !isAwaitingVerification && (
                        <div className="space-y-2">
                          <div className="p-3 rounded-xl bg-amber-950/60 border border-amber-600/70 text-amber-200 text-xs">
                            <span className="font-black uppercase block text-[10px] text-amber-400">ACTION IN PROGRESS</span>
                            Supervisor on site. Halt crane operation and clear personnel.
                          </div>
                          <button
                            onClick={() => handleActionTaken(activeAlert.id)}
                            disabled={submitting}
                            className="w-full py-3.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-sm rounded-xl shadow-lg flex items-center justify-center space-x-2"
                          >
                            <Check className="w-4 h-4" />
                            <span>[ ACTION TAKEN — PERIMETER SECURED ]</span>
                          </button>
                        </div>
                      )}

                      {isAwaitingVerification && (
                        <div className="space-y-3">
                          <div className="p-3 rounded-xl bg-purple-950/60 border border-purple-600/70 text-purple-200 text-xs">
                            <span className="font-black uppercase block text-[10px] text-purple-300">AWAITING VERIFICATION</span>
                            Objective CCTV confirmation required before closure.
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            <button
                              onClick={() => handleCctvVerify(false, activeAlert.id)}
                              disabled={submitting}
                              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs rounded-xl shadow flex items-center justify-center space-x-1.5"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                              <span>✓ CCTV CHECK: ZONE CLEAR → VERIFY</span>
                            </button>
                            <button
                              onClick={() => handleCctvVerify(true, activeAlert.id)}
                              disabled={submitting}
                              className="w-full py-3 bg-rose-700 hover:bg-rose-600 text-white font-black text-xs rounded-xl shadow flex items-center justify-center space-x-1.5"
                            >
                              <RotateCcw className="w-4 h-4" />
                              <span>✕ CCTV CHECK: RE-BREACH → REOPEN</span>
                            </button>
                          </div>
                        </div>
                      )}

                      {isResolved && (
                        <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500 text-emerald-200 text-xs text-center space-y-1">
                          <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto" />
                          <span className="font-black uppercase block text-sm text-white">✓ EVENT FORMALLY VERIFIED</span>
                          <p className="text-[11px] text-emerald-300">
                            Observable clearance confirmed. Event committed to Safety Memory.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* ======================================================== */}
                {/* CLASS 2 — PATTERN CORRECTIVE ACTION (HSE Assigned)        */}
                {/* ======================================================== */}
                {activePatternAction && (
                  <div className="p-5 rounded-2xl bg-amber-950/80 border-2 border-amber-500/90 shadow-lg space-y-3 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                        <Layers className="w-4 h-4 text-amber-400" />
                        🟠 PATTERN ACTION — CORRECTIVE ACTION REQUIRED
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500 text-slate-950 font-mono">
                        PRIORITY: {activePatternAction.severity || 'HIGH'}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-black tracking-tight text-white leading-snug">
                        {activePatternAction.pattern_title || activePatternAction.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-amber-200">
                        <span>Location: <b>{activePatternAction.location || 'Lifting Zone 03'}</b></span>
                        <span>•</span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-900/80 text-amber-300 font-bold text-[10px]">
                          {activePatternAction.pattern_occurrence_count || activePatternAction.independent_occurrences_count || 6} INDEPENDENT OCCURRENCES
                        </span>
                      </div>
                    </div>

                    <div className="p-3 bg-amber-900/50 rounded-xl border border-amber-700/70 text-xs space-y-1">
                      <span className="text-[10px] font-black uppercase tracking-wider text-amber-300 block">
                        REQUIRED CORRECTIVE ACTION (Assigned by HSE)
                      </span>
                      <p className="font-bold text-white">
                        {activePatternAction.immediate_action || 'Clear unauthorized personnel and secure the restricted zone.'}
                      </p>
                      <span className="text-[10px] text-amber-300/80 block pt-0.5">
                        Verification Method: <b>{activePatternAction.verification_type || 'CCTV_VERIFIABLE'}</b>
                      </span>
                    </div>

                    {/* Operational Progression for Pattern Action */}
                    <div className="pt-1">
                      {activePatternAction.verification_status === 'AWAITING_VERIFICATION' ? (
                        <div className="p-3.5 rounded-xl bg-purple-950/80 border border-purple-500 text-xs space-y-2.5">
                          <div className="flex items-center space-x-1.5 text-purple-300 font-bold">
                            <Clock className="w-4 h-4 text-purple-400" />
                            <span>🟡 AWAITING VERIFICATION</span>
                          </div>
                          <p className="text-[11px] text-slate-300">
                            Action reported completed by supervisor. Objective verification required before closure.
                          </p>
                          <div className="grid grid-cols-1 gap-2 pt-1">
                            <button
                              onClick={() => handleCctvVerify(false, activePatternAction.id)}
                              disabled={submitting}
                              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg shadow flex items-center justify-center space-x-1.5"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                              <span>✓ CCTV CHECK: ZONE CLEAR → VERIFY</span>
                            </button>
                            <button
                              onClick={() => handleCctvVerify(true, activePatternAction.id)}
                              disabled={submitting}
                              className="w-full py-2.5 bg-rose-700 hover:bg-rose-600 text-white font-bold text-xs rounded-lg shadow flex items-center justify-center space-x-1.5"
                            >
                              <RotateCcw className="w-4 h-4" />
                              <span>✕ CCTV CHECK: RE-BREACH → REOPEN</span>
                            </button>
                          </div>
                        </div>
                      ) : activePatternAction.verification_status === 'VERIFIED' ? (
                        <div className="p-3 rounded-xl bg-emerald-950/70 border border-emerald-500 text-emerald-200 text-xs text-center space-y-1">
                          <CheckCircle2 className="w-5 h-5 text-emerald-400 mx-auto" />
                          <span className="font-bold uppercase text-white block">✓ PATTERN ACTION VERIFIED</span>
                          <span className="text-[11px] text-emerald-300">
                            Observable clearance confirmed. Pattern ready for formal HSE closure in Safety Memory.
                          </span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <button
                            onClick={() => handlePatternActionCompleted(activePatternAction.id)}
                            disabled={submitting}
                            className="w-full py-3.5 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 font-black text-sm rounded-xl shadow-lg transition-transform active:scale-95 flex items-center justify-center space-x-2"
                          >
                            <Check className="w-4 h-4" />
                            <span>[ ACTION COMPLETED — ZONE SECURED ]</span>
                          </button>
                          <p className="text-[10px] text-amber-300/80 text-center">
                            Physically clear the zone and tap to report completion. HSE will verify via CCTV.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Progressive Disclosure: Deep SIF Details */}
                {activeAlert && (
                  <div className="text-center pt-2">
                    <button
                      onClick={() => setShowDeepDetails(!showDeepDetails)}
                      className="text-[11px] font-bold text-slate-400 hover:text-white transition-colors underline"
                    >
                      {showDeepDetails ? 'Hide Deep Safety Ontology ▲' : 'Inspect SIF Reasoning & Evidence Spans ▼'}
                    </button>

                    {showDeepDetails && (
                      <div className="mt-3 p-4 rounded-xl bg-slate-900 border border-slate-800 text-left text-xs space-y-2 text-slate-300 animate-fade-in">
                        <div>
                          <span className="text-[10px] text-slate-500 font-bold uppercase block">Hazard & Barrier</span>
                          <span className="font-bold text-white">{activeAlert.hazard || 'Mechanical Crane Hoisting'}</span> • <span className="text-red-400">{activeAlert.critical_barrier || 'Exclusion Zone Barrier'}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 font-bold uppercase block">IOGP Life-Saving Rule</span>
                          <span className="font-bold text-amber-400">{activeAlert.life_saving_rule || 'Line of Fire'}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 font-bold uppercase block">Safety Memory Recurrence</span>
                          <span className="font-mono text-purple-300">
                            {activeAlert.independent_occurrences_count || 5} independent occurrences in memory
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}
          </div>
        )}

      </main>

      {/* Mobile Footer */}
      <footer className="p-3 bg-slate-900/90 border-t border-slate-800 text-center text-[10px] text-slate-500">
        SHRAMRAKSHAK Mobile • Operational Edge • OIL SIH26165
      </footer>

    </div>
  );
}
