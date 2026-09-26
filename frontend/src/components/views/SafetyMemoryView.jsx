import React, { useState, useEffect } from 'react';
import { 
  Database, 
  ShieldCheck, 
  AlertOctagon, 
  CheckCircle2, 
  XCircle, 
  ArrowRight, 
  FileCheck, 
  Layers, 
  Clock, 
  Check, 
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  UserCheck,
  History,
  ShieldAlert,
  ChevronRight
} from 'lucide-react';
import { 
  fetchSafetyMemoryPatterns, 
  validateSafetyMemoryPattern, 
  checkWorkPackage, 
  fetchSafetyMemorySummary 
} from '../../services/api';

const TASK_EVIDENCE_MAP = {
  'Mechanical Lifting': [
    { key: 'PHYSICAL_PERIMETER_DEMARCATION', label: 'Physical Perimeter Demarcation (Barricades / Tape)' },
    { key: 'AUTHORIZED_ENTRANTS_PASSPORT', label: 'Authorized Entrants Temporary Safety Passport' },
    { key: 'OBSERVABLE_CCTV_CLEAR_ZONE', label: 'Observable CCTV Clear Zone Verification' },
  ],
  'Electrical Maintenance (LOTO)': [
    { key: 'ZERO_ENERGY_TEST_LOG', label: 'Zero-Energy Try-Step Physical Verification Log' },
    { key: 'LOTO_PADLOCK_REGISTER', label: 'LOTO Padlock Register & Key Custody Sign-Off' },
    { key: 'ELECTRICAL_ISOLATION_CERTIFICATE', label: 'Certified Electrical Isolation Certificate' },
  ],
  'Confined Space Entry': [
    { key: 'CALIBRATED_4GAS_TEST_RECORD', label: 'Calibrated 4-Gas Atmospheric Test Record' },
    { key: 'STANDBY_RESCUE_PERSONNEL', label: 'Designated Standby Rescue Personnel Log' },
    { key: 'VENTILATION_CONFIRMATION', label: 'Continuous Forced Ventilation Verification' },
  ]
};

export default function SafetyMemoryView() {
  const [patterns, setPatterns] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [validatingId, setValidatingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL | CANDIDATE | VALIDATED | REJECTED

  // Interactive Work Package Precondition Check Form
  const [wpTaskType, setWpTaskType] = useState('Mechanical Lifting');
  const [wpLocation, setWpLocation] = useState('Drilling Rig 04 - Wellhead Area');
  const [wpEvidenceProvided, setWpEvidenceProvided] = useState(['PHYSICAL_PERIMETER_DEMARCATION']);
  const [wpChecking, setWpChecking] = useState(false);
  const [wpResult, setWpResult] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sum, pats] = await Promise.all([
        fetchSafetyMemorySummary(),
        fetchSafetyMemoryPatterns()
      ]);
      setSummary(sum);
      setPatterns(pats?.patterns || []);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load safety memory:', err);
      setFeedbackMsg('Failed to refresh Safety Memory from server');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleValidate = async (patternId, decision) => {
    try {
      setValidatingId(patternId);
      await validateSafetyMemoryPattern(patternId, decision, 'HSE-Lead-01', 'Reviewed in SIH Demonstration workflow');
      setFeedbackMsg(`Pattern ${patternId} successfully ${decision === 'CONFIRM' ? 'confirmed as Validated Safety Learning' : 'marked as REJECTED'}.`);
      await loadData();
      setTimeout(() => setFeedbackMsg(null), 5000);
    } catch (err) {
      console.error('Validation failed:', err);
      setFeedbackMsg(`Failed to validate pattern: ${err.message}`);
    } finally {
      setValidatingId(null);
    }
  };

  const handleTaskTypeChange = (newTaskType) => {
    setWpTaskType(newTaskType);
    const defaults = TASK_EVIDENCE_MAP[newTaskType] || [];
    setWpEvidenceProvided(defaults.length > 0 ? [defaults[0].key] : []);
    setWpResult(null);
  };

  const handleToggleEvidence = (key) => {
    setWpEvidenceProvided(prev => 
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const handleRunWpCheck = async () => {
    try {
      setWpChecking(true);
      const evidenceObj = {};
      wpEvidenceProvided.forEach(k => {
        evidenceObj[k] = true;
      });

      const res = await checkWorkPackage({
        package_id: 'WP-OIL-2026-PRECON-01',
        activity: wpTaskType,
        task_type: wpTaskType,
        location: wpLocation,
        submitted_evidence: evidenceObj,
        evidence_provided: wpEvidenceProvided
      });
      setWpResult(res);
    } catch (err) {
      console.error('Work package check failed:', err);
      setFeedbackMsg('Work package check failed. Review server connection.');
    } finally {
      setWpChecking(false);
    }
  };

  const filteredPatterns = patterns.filter(p => {
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'CANDIDATE') return p.validation_status === 'CANDIDATE' || !p.is_validated;
    if (statusFilter === 'VALIDATED') return p.validation_status === 'HSE_VALIDATED' || p.is_validated;
    if (statusFilter === 'REJECTED') return p.validation_status === 'REJECTED';
    return true;
  });

  const candidateCount = patterns.filter(p => p.validation_status === 'CANDIDATE').length;
  const validatedCount = patterns.filter(p => p.validation_status === 'HSE_VALIDATED').length;
  const rejectedCount = patterns.filter(p => p.validation_status === 'REJECTED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-purple-100 text-purple-900 border border-purple-200">
              SAFETY MEMORY ARCHITECTURE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Underlying Control Breaches • HSE Human-in-Loop • Future Preconditions
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            Safety Memory & Organizational Learning
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {lastRefreshed && (
            <span className="text-[11px] font-mono text-slate-500">
              Updated: {lastRefreshed}
            </span>
          )}
          <button 
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-sm flex items-center gap-1.5 text-xs font-bold disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-purple-600' : ''}`} />
            <span>{loading ? 'Refreshing...' : 'Refresh Memory'}</span>
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div className="p-3 rounded-xl bg-purple-50 border border-purple-300 text-purple-950 font-bold text-xs flex items-center justify-between animate-fade-in shadow-sm">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-purple-700 flex-shrink-0" />
            <span>{feedbackMsg}</span>
          </div>
          <button onClick={() => setFeedbackMsg(null)} className="text-purple-700 hover:text-purple-900 text-xs font-bold">✕</button>
        </div>
      )}

      {/* 2. Top Metric Telemetry */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total Safety Observations</span>
          <span className="text-2xl font-black text-slate-900 mt-1 block">{summary?.total_events ?? patterns.reduce((a, b) => a + (b.occurrence_count || 1), 0)}</span>
          <span className="text-[11px] text-slate-500 mt-1 block">Cross-report persistent events</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Independent Occurrences</span>
          <span className="text-2xl font-black text-purple-700 mt-1 block">
            {patterns.reduce((acc, p) => acc + (p.independent_occurrences || p.occurrence_count || 0), 0)}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Distinct underlying control events</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Duplicates Filtered</span>
          <span className="text-2xl font-black text-slate-700 mt-1 block">{summary?.duplicate_count ?? 0}</span>
          <span className="text-[11px] text-slate-500 mt-1 block">Filtered by polarity & timeline</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Validated Safety Learning</span>
          <span className="text-2xl font-black text-emerald-700 mt-1 block">
            {validatedCount}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">HSE-confirmed future controls</span>
        </div>
      </div>

      {/* 3. Filter Navigation Tabs (Section 12 & 24) */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'ALL'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Patterns ({patterns.length})
          </button>
          <button
            onClick={() => setStatusFilter('CANDIDATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'CANDIDATE'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200'
            }`}
          >
            Candidate Queue ({candidateCount})
          </button>
          <button
            onClick={() => setStatusFilter('VALIDATED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'VALIDATED'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200'
            }`}
          >
            Validated Learning ({validatedCount})
          </button>
          <button
            onClick={() => setStatusFilter('REJECTED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'REJECTED'
                ? 'bg-slate-700 text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            Rejected ({rejectedCount})
          </button>
        </div>

        <span className="text-xs text-slate-500 hidden sm:inline">
          Showing <strong className="text-slate-800">{filteredPatterns.length}</strong> patterns
        </span>
      </div>

      {/* 4. Pattern Cards Display */}
      <div className="space-y-4">
        {filteredPatterns.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 space-y-2">
            <Layers className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-xs font-bold text-slate-700">No recurring control patterns in this category.</p>
            <p className="text-[11px] text-slate-400">Patterns are discovered by two-stage recurrence analysis and reviewed by HSE.</p>
          </div>
        ) : (
          filteredPatterns.map((p) => {
            const isValidated = p.validation_status === 'HSE_VALIDATED' || p.is_validated;
            const isRejected = p.validation_status === 'REJECTED';
            const isCandidate = !isValidated && !isRejected;

            return (
              <div 
                key={p.pattern_id}
                className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition-all ${
                  isValidated 
                    ? 'border-emerald-300 ring-1 ring-emerald-200 bg-emerald-50/10' 
                    : isRejected
                    ? 'border-slate-300 bg-slate-50/60 opacity-80'
                    : 'border-amber-200 ring-1 ring-amber-100'
                }`}
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border">
                        {p.pattern_id}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                        isValidated 
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                          : isRejected
                          ? 'bg-slate-200 text-slate-700 border-slate-300'
                          : 'bg-amber-100 text-amber-800 border-amber-300'
                      }`}>
                        {isValidated 
                          ? '✓ HSE VALIDATED SAFETY LEARNING' 
                          : isRejected
                          ? '✕ REJECTED BY HSE'
                          : '⚡ CANDIDATE PATTERN (Awaiting HSE Decision)'}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
                        {p.independent_occurrences || p.occurrence_count || 1} INDEPENDENT OCCURRENCES
                      </span>
                    </div>
                    <h3 className="text-sm font-black text-slate-900 mt-1">
                      {p.pattern_title || p.title}
                    </h3>
                  </div>

                  {/* HSE Decision Buttons */}
                  <div className="flex items-center space-x-2">
                    {isCandidate && (
                      <>
                        <button
                          onClick={() => handleValidate(p.pattern_id, 'CONFIRM')}
                          disabled={validatingId === p.pattern_id}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>CONFIRM AS VALIDATED</span>
                        </button>
                        <button
                          onClick={() => handleValidate(p.pattern_id, 'REJECT')}
                          disabled={validatingId === p.pattern_id}
                          className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition-colors"
                        >
                          Reject
                        </button>
                      </>
                    )}

                    {isValidated && (
                      <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Validated by {p.reviewer_role || 'HSE Lead'}
                      </span>
                    )}

                    {isRejected && (
                      <button
                        onClick={() => handleValidate(p.pattern_id, 'CONFIRM')}
                        disabled={validatingId === p.pattern_id}
                        className="px-2.5 py-1 text-slate-500 hover:text-slate-800 text-[11px] font-bold border border-slate-200 rounded-lg hover:bg-white"
                      >
                        Re-evaluate
                      </button>
                    )}
                  </div>
                </div>

                {/* Underlying Control Mechanism Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Activity / Hazard</span>
                    <span className="font-bold text-slate-900 mt-1 block">
                      {p.activity} • {p.energy || p.hazard || 'Mechanical Hazard'}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Failed Critical Control</span>
                    <span className="font-bold text-red-700 mt-1 block">
                      {p.barrier || p.critical_barrier} ({p.barrier_condition || 'Control Breached'})
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Recurrence Verification</span>
                    <span className="font-bold text-slate-800 mt-1 block">
                      {p.independent_occurrences || p.occurrence_count || 1} independent control failures
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {p.duplicate_count || 0} duplicate reports filtered
                    </span>
                  </div>
                </div>

                {/* Future Safety Preconditions Banner (Section 13) */}
                {isValidated && p.future_work_requirements && p.future_work_requirements.length > 0 && (
                  <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-lg space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-emerald-900 font-bold text-xs uppercase tracking-wider">
                      <FileCheck className="w-4 h-4 text-emerald-700" />
                      <span>Active Future-Work Precondition Applied:</span>
                    </div>
                    {p.future_work_requirements.map((req, i) => (
                      <div key={i} className="text-xs text-slate-800 pl-5">
                        • <strong>{req.title}</strong>: {req.description} ({req.evidence_type})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* 5. Future Work Package Safety Verification (Section 14) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <FileCheck className="w-4 h-4 text-blue-600" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Future-Work Safety Evidence Check (Pre-Job Authorization)
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Test how validated Safety Memory automatically evaluates upcoming work packages for required observable safety evidence before permit authorization.
            SHRAMRAKSHAK does <strong>not</strong> autonomously approve permits; it flags missing critical safety evidence for human HSE review.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Work Package Task Type</label>
            <select
              value={wpTaskType}
              onChange={(e) => handleTaskTypeChange(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-300 bg-white text-slate-900 font-semibold"
            >
              <option value="Mechanical Lifting">Mechanical Lifting Operations</option>
              <option value="Electrical Maintenance (LOTO)">Electrical Maintenance (LOTO)</option>
              <option value="Confined Space Entry">Confined Space Entry</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Target Location</label>
            <input
              type="text"
              value={wpLocation}
              onChange={(e) => setWpLocation(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-300 text-slate-900 font-semibold"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Submitted Safety Evidence</label>
            <div className="space-y-1.5 pt-1">
              {(TASK_EVIDENCE_MAP[wpTaskType] || []).map((evItem) => (
                <label key={evItem.key} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={wpEvidenceProvided.includes(evItem.key)}
                    onChange={() => handleToggleEvidence(evItem.key)}
                    className="rounded text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-slate-800 text-[11px]">{evItem.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleRunWpCheck}
            disabled={wpChecking}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5 disabled:opacity-50"
          >
            {wpChecking ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileCheck className="w-3.5 h-3.5" />
            )}
            <span>{wpChecking ? 'Evaluating Preconditions...' : 'Evaluate Work Package Against Memory'}</span>
          </button>
        </div>

        {/* Work Package Result Banner */}
        {wpResult && (
          <div className={`p-4 rounded-xl border animate-fade-in ${
            wpResult.status === 'PASS' 
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950' 
              : 'bg-red-50 border-red-300 text-red-950'
          }`}>
            <div className="flex items-center justify-between font-bold mb-1">
              <span className="text-xs uppercase tracking-wider flex items-center gap-1.5">
                {wpResult.status === 'PASS' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertOctagon className="w-4 h-4 text-red-600" />
                )}
                {wpResult.status === 'PASS' 
                  ? 'ALL REQUIRED CRITICAL SAFETY EVIDENCE SATISFIED' 
                  : wpResult.status === 'MISSING_EVIDENCE'
                  ? 'REQUIRED SAFETY EVIDENCE MISSING — HUMAN HSE REVIEW REQUIRED'
                  : `EVALUATION STATUS: ${wpResult.status}`}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/80 border font-bold">
                {wpResult.status}
              </span>
            </div>

            <p className="text-xs leading-snug mt-1">
              {wpResult.status === 'PASS'
                ? 'All historical preconditions from validated recurring patterns have been satisfied with appropriate evidence. Human HSE permit issuer can proceed.'
                : 'Work package cannot proceed automatically. Missing required critical safety evidence must be provided or verified on-site before permit issuance.'}
            </p>

            {/* Findings List */}
            {wpResult.findings && wpResult.findings.length > 0 && (
              <div className="mt-2.5 pt-2 border-t border-slate-200/80 text-xs">
                <span className="font-bold block mb-1 text-slate-800">Evaluated Precondition Findings:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-700 text-[11px]">
                  {wpResult.findings.map((finding, idx) => (
                    <li key={idx}>{finding}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Missing Evidence List */}
            {wpResult.missing_evidence && wpResult.missing_evidence.length > 0 && (
              <div className="mt-2 pt-2 border-t border-red-200 text-xs">
                <span className="font-bold text-red-900 block mb-1">Missing Evidence Items:</span>
                <ul className="list-disc list-inside space-y-0.5 text-red-800 text-[11px]">
                  {wpResult.missing_evidence.map((miss, idx) => (
                    <li key={idx}>
                      <strong>{miss}</strong> — Required by validated organizational learning
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
