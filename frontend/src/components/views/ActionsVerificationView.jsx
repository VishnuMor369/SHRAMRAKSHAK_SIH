import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertOctagon, 
  Clock, 
  ShieldCheck, 
  Video, 
  Eye, 
  RotateCcw, 
  ArrowRight, 
  Check, 
  X,
  FileCheck,
  AlertTriangle
} from 'lucide-react';
import { 
  respondToAlert, 
  markActionTaken, 
  verifyAlert, 
  verifyCctvCondition 
} from '../../services/api';

export default function ActionsVerificationView({ status, onSelectAlert }) {
  const [submittingId, setSubmittingId] = useState(null);
  const [notes, setNotes] = useState('');
  const [feedback, setFeedback] = useState(null);

  const activeAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);

  const handleRespond = async (alertId) => {
    try {
      setSubmittingId(alertId);
      await respondToAlert('SUP-01', notes || 'Supervisor responding on site', alertId);
      setFeedback({ type: 'success', msg: 'Alert acknowledged. Status: ACTION IN PROGRESS' });
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message || 'Failed to acknowledge alert' });
    } finally {
      setSubmittingId(null);
    }
  };

  const handleActionTaken = async (alertId) => {
    try {
      setSubmittingId(alertId);
      await markActionTaken('SUP-01', notes || 'Worker cleared from zone; mechanical lift held', 'Action Taken', alertId);
      setFeedback({ type: 'success', msg: 'Corrective action taken. Status: AWAITING VERIFICATION ("Completion is not proof")' });
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message || 'Failed to record action' });
    } finally {
      setSubmittingId(null);
    }
  };

  const handleCctvVerify = async (alertId, simulateRebreach = false) => {
    try {
      setSubmittingId(alertId);
      const res = await verifyCctvCondition(alertId, simulateRebreach, 'SUP-01');
      if (res.verified) {
        setFeedback({ 
          type: 'success', 
          msg: `✓ CCTV VERIFIED: ${res.verification_notes}` 
        });
      } else {
        setFeedback({ 
          type: 'error', 
          msg: `✕ VERIFICATION FAILED: Re-breach detected in zone. Corrective action REOPENED!` 
        });
      }
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message || 'CCTV verification failed' });
    } finally {
      setSubmittingId(null);
    }
  };

  const handleFieldVerify = async (alertId, decision) => {
    try {
      setSubmittingId(alertId);
      await verifyAlert('SUP-01', decision, 'FIELD_VERIFIED', notes || `Physical field inspection: ${decision}`, alertId);
      setFeedback({ 
        type: decision === 'VERIFIED' ? 'success' : 'error', 
        msg: `Field verification recorded: ${decision}` 
      });
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message || 'Field verification failed' });
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-100 text-emerald-900 border border-emerald-200">
              EVIDENCE-BASED VERIFICATION
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Closed-Loop Safety Governance ("Completion is not proof")
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Corrective Action & CCTV Verification
          </h1>
        </div>

        <div className="text-xs text-slate-500 max-w-sm sm:text-right">
          If condition returns: <b className="text-red-700">VERIFICATION FAILED — RE-BREACH DETECTED</b> and action is reopened.
        </div>
      </div>

      {feedback && (
        <div className={`p-4 rounded-xl border font-bold text-xs flex items-center justify-between animate-fade-in ${
          feedback.type === 'success' 
            ? 'bg-emerald-50 border-emerald-300 text-emerald-950' 
            : 'bg-red-50 border-red-300 text-red-950'
        }`}>
          <div className="flex items-center space-x-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <AlertOctagon className="w-5 h-5 text-red-600" />
            )}
            <span>{feedback.msg}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="text-slate-500 hover:text-slate-800 text-xs">✕</button>
        </div>
      )}

      {/* 2. State Machine Pipeline Visualizer */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
          Enterprise Safety Lifecycle State Machine (Backend Enforced)
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
          <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-900 font-bold">
            1. ACTION REQUIRED
            <span className="block text-[10px] font-normal text-red-700 mt-0.5">SLA Assigned</span>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 font-bold">
            2. IN PROGRESS
            <span className="block text-[10px] font-normal text-amber-700 mt-0.5">Supervisor En Route</span>
          </div>
          <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 font-bold">
            3. ACTION TAKEN
            <span className="block text-[10px] font-normal text-blue-700 mt-0.5">Hazard Rectified</span>
          </div>
          <div className="p-2.5 rounded-lg bg-purple-50 border border-purple-200 text-purple-900 font-bold">
            4. VERIFYING
            <span className="block text-[10px] font-normal text-purple-700 mt-0.5">CCTV Observation Check</span>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 font-bold">
            5. VERIFIED & CLOSED
            <span className="block text-[10px] font-normal text-emerald-700 mt-0.5">Learning Recorded</span>
          </div>
        </div>
      </div>

      {/* 3. Operational Alerts & Verification Actions */}
      <div className="space-y-4">
        <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
          Operational Event Actions ({activeAlerts.length})
        </h2>

        {activeAlerts.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <p className="text-sm font-bold text-slate-800">No Open Corrective Actions</p>
            <p className="text-xs text-slate-500">
              All safety alerts have been verified and resolved.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {activeAlerts.map(alert => {
              const isWaiting = alert.status === 'WAITING_FOR_RESPONSE';
              const isResponding = alert.status === 'RESPONDING' || alert.action_status === 'IN_PROGRESS';
              const isAwaitingVerification = alert.verification_status === 'AWAITING_VERIFICATION' || alert.lifecycle_state === 'AWAITING_VERIFICATION';
              const isResolved = alert.status === 'RESOLVED' || alert.verification_status === 'VERIFIED';

              return (
                <div 
                  key={alert.id}
                  className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white">
                          SIF: {alert.sif_level || 'HIGH'}
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-700">
                          {alert.event_id || alert.id}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-200">
                          STATE: {alert.lifecycle_state || alert.status}
                        </span>
                      </div>
                      <h3 className="text-sm font-black text-slate-900">
                        {alert.title || alert.type}
                      </h3>
                      <p className="text-xs text-slate-600">
                        Location: <b className="text-slate-800">{alert.location}</b> • Required Action: <b className="text-red-700">{alert.immediate_action}</b>
                      </p>
                    </div>

                    <button
                      onClick={() => onSelectAlert(alert)}
                      className="text-xs font-bold text-slate-600 hover:text-slate-900 underline"
                    >
                      Audit Details →
                    </button>
                  </div>

                  {/* Lifecycle-Specific Action Buttons */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Supervisor / HSE Action Console
                    </span>

                    {/* Stage 1: Action Required */}
                    {isWaiting && (
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          onClick={() => handleRespond(alert.id)}
                          disabled={submittingId === alert.id}
                          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-black text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5"
                        >
                          <Clock className="w-4 h-4" />
                          <span>ACKNOWLEDGE & RESPOND ON SITE</span>
                        </button>
                        <span className="text-xs text-slate-500">
                          Acknowledges assignment and initiates field response timer.
                        </span>
                      </div>
                    )}

                    {/* Stage 2: In Progress */}
                    {isResponding && !isAwaitingVerification && (
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          onClick={() => handleActionTaken(alert.id)}
                          disabled={submittingId === alert.id}
                          className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5"
                        >
                          <Check className="w-4 h-4" />
                          <span>MARK ACTION TAKEN (PERIMETER CLEARED)</span>
                        </button>
                        <span className="text-xs text-amber-900 font-semibold">
                          Transitions to AWAITING VERIFICATION ("Completion is not proof").
                        </span>
                      </div>
                    )}

                    {/* Stage 3: Awaiting Verification (The SIH Differentiator) */}
                    {isAwaitingVerification && (
                      <div className="space-y-2">
                        <div className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
                          <Eye className="w-4 h-4 text-purple-700" />
                          <span>Physical Action Reported Completed. Verification Required via Objective Evidence:</span>
                        </div>

                        <div className="flex flex-wrap gap-2.5 pt-1">
                          {/* CCTV Check: Clean Condition -> Verified */}
                          <button
                            onClick={() => handleCctvVerify(alert.id, false)}
                            disabled={submittingId === alert.id}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5"
                          >
                            <Video className="w-4 h-4" />
                            <span>CCTV CHECK (ZONE CLEAR → VERIFIED)</span>
                          </button>

                          {/* CCTV Check: Re-Breach -> Failed & Reopened */}
                          <button
                            onClick={() => handleCctvVerify(alert.id, true)}
                            disabled={submittingId === alert.id}
                            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-black text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5"
                          >
                            <RotateCcw className="w-4 h-4" />
                            <span>CCTV CHECK (SIMULATE RE-BREACH → REOPEN)</span>
                          </button>

                          {/* Field Physical Inspection */}
                          <button
                            onClick={() => handleFieldVerify(alert.id, 'VERIFIED')}
                            disabled={submittingId === alert.id}
                            className="px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-lg transition-colors"
                          >
                            Field Inspection (Physical)
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Stage 4: Verified */}
                    {isResolved && (
                      <div className="flex items-center space-x-2 text-xs text-emerald-800 font-bold">
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                        <span>Formally Verified by {alert.verified_by || 'Supervisor'} via {alert.verification_method || 'CCTV_VERIFIED'}. Event closed and committed to Safety Memory.</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
