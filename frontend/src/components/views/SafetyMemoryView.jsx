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
  ChevronRight,
  Eye,
  Video,
  Send,
  Archive,
  AlertCircle,
  FileText,
  Camera,
  Activity,
  User,
  MapPin
} from 'lucide-react';
import { 
  fetchSafetyMemoryPatterns, 
  validateSafetyMemoryPattern, 
  checkWorkPackage, 
  fetchSafetyMemorySummary,
  fetchPatternDetails,
  assignPatternAction,
  closeSafetyPattern,
  verifyCctvCondition
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
  const [feedbackType, setFeedbackType] = useState('success');
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL | CANDIDATE | ACTION_REQUIRED | AWAITING_VERIFICATION | VERIFIED | CLOSED_HISTORY | REJECTED

  // View Details Modal State
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [selectedDetails, setSelectedDetails] = useState(null);

  // Assign Corrective Action Modal State
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assigningPattern, setAssigningPattern] = useState(null);
  const [assignForm, setAssignForm] = useState({
    supervisor_id: 'SUP-01',
    supervisor_name: 'Rajesh Kumar (Field Lead)',
    required_action: 'Clear unauthorized personnel and secure the restricted/lifting zone.',
    location: 'Lifting Zone 03',
    priority: 'HIGH',
    verification_method: 'CCTV_VERIFIABLE',
    notes: ''
  });
  const [assignSubmitting, setAssignSubmitting] = useState(false);

  // HSE Close Pattern Modal State
  const [closeModalOpen, setCloseModalOpen] = useState(false);
  const [closingPattern, setClosingPattern] = useState(null);
  const [closureNotes, setClosureNotes] = useState('Observable condition restored and verified via CCTV stream. Pattern closed into historical memory.');
  const [closeSubmitting, setCloseSubmitting] = useState(false);

  // CCTV In-Situ Verification State
  const [verifyingId, setVerifyingId] = useState(null);
  const [cctvStreamKey, setCctvStreamKey] = useState(Date.now());

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
      showFeedback('Failed to refresh Safety Memory from server', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const showFeedback = (msg, type = 'success') => {
    setFeedbackMsg(msg);
    setFeedbackType(type);
    setTimeout(() => setFeedbackMsg(null), 6000);
  };

  const handleValidate = async (patternId, decision) => {
    try {
      setValidatingId(patternId);
      await validateSafetyMemoryPattern(patternId, decision, 'HSE-Lead-01', 'Reviewed in SIH Demonstration workflow');
      showFeedback(`Pattern ${patternId} successfully ${decision === 'CONFIRM' ? 'confirmed by HSE — Corrective Action can now be assigned' : 'marked as REJECTED'}.`);
      await loadData();
    } catch (err) {
      console.error('Validation failed:', err);
      showFeedback(`Failed to validate pattern: ${err.message}`, 'error');
    } finally {
      setValidatingId(null);
    }
  };

  const handleOpenDetails = async (pattern) => {
    try {
      setDetailsModalOpen(true);
      setDetailsLoading(true);
      const res = await fetchPatternDetails(pattern.pattern_id);
      setSelectedDetails(res?.pattern_details || null);
    } catch (err) {
      console.error('Failed to load pattern details:', err);
      showFeedback(`Could not fetch details: ${err.message}`, 'error');
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleOpenAssignModal = (pattern) => {
    setAssigningPattern(pattern);
    const loc = pattern.location || 'Lifting Zone 03';
    let defaultAction = 'Clear unauthorized personnel and secure the restricted/lifting zone.';
    if (pattern.activity && pattern.activity.toLowerCase().includes('electrical')) {
      defaultAction = 'Verify zero-energy state, apply certified LOTO padlocks, and clear perimeter.';
    } else if (pattern.activity && pattern.activity.toLowerCase().includes('confined')) {
      defaultAction = 'Perform calibrated 4-gas test, post standby rescue sentinel, and verify ventilation.';
    }
    setAssignForm({
      supervisor_id: 'SUP-01',
      supervisor_name: 'Rajesh Kumar (Field Lead)',
      required_action: defaultAction,
      location: loc,
      priority: pattern.sif_potential === 'HIGH' ? 'CRITICAL' : 'HIGH',
      verification_method: 'CCTV_VERIFIABLE',
      notes: `HSE Corrective Action assigned for recurring pattern ${pattern.pattern_id}`
    });
    setAssignModalOpen(true);
  };

  const handleSubmitAssignAction = async (e) => {
    e.preventDefault();
    if (!assigningPattern) return;
    try {
      setAssignSubmitting(true);
      await assignPatternAction(assigningPattern.pattern_id, assignForm);
      showFeedback(`Corrective Action successfully assigned to ${assignForm.supervisor_name}. Notification dispatched.`);
      setAssignModalOpen(false);
      await loadData();
    } catch (err) {
      console.error('Failed to assign corrective action:', err);
      showFeedback(`Failed to assign action: ${err.message}`, 'error');
    } finally {
      setAssignSubmitting(false);
    }
  };

  const handleOpenCloseModal = (pattern) => {
    setClosingPattern(pattern);
    setClosureNotes(`Observable condition restored and verified clear via CCTV stream. Pattern ${pattern.pattern_id} formally closed by HSE Lead into historical learning.`);
    setCloseModalOpen(true);
  };

  const handleSubmitClosePattern = async (e) => {
    e.preventDefault();
    if (!closingPattern) return;
    try {
      setCloseSubmitting(true);
      await closeSafetyPattern(closingPattern.pattern_id, 'HSE Lead (Oil India)', closureNotes);
      showFeedback(`Pattern ${closingPattern.pattern_id} successfully closed by HSE and preserved in Historical Safety Memory.`);
      setCloseModalOpen(false);
      await loadData();
    } catch (err) {
      console.error('Failed to close pattern:', err);
      showFeedback(`Failed to close pattern: ${err.message}`, 'error');
    } finally {
      setCloseSubmitting(false);
    }
  };

  const handleCctvVerify = async (patternId, simulateRebreach) => {
    try {
      setVerifyingId(patternId);
      const res = await verifyCctvCondition(patternId, simulateRebreach, 'SUP-01');
      if (res.verified) {
        showFeedback(`✓ VERIFIED: Observable condition confirmed clear by CCTV stream. Pattern is ready for HSE closure.`);
      } else {
        showFeedback(`✕ VERIFICATION FAILED — RE-BREACH DETECTED: Personnel observed inside zone. Action reopened and evidence recorded into Safety Memory.`, 'error');
      }
      setCctvStreamKey(Date.now());
      await loadData();
    } catch (err) {
      console.error('CCTV verification failed:', err);
      showFeedback(`Verification failed: ${err.message}`, 'error');
    } finally {
      setVerifyingId(null);
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
      showFeedback('Work package check failed. Review server connection.', 'error');
    } finally {
      setWpChecking(false);
    }
  };

  const filteredPatterns = patterns.filter(p => {
    const op = p.operational_status || 'NONE';
    const val = p.validation_status;
    if (statusFilter === 'ALL') return true;
    if (statusFilter === 'CANDIDATE') return val === 'CANDIDATE' || !p.is_validated;
    if (statusFilter === 'ACTION_REQUIRED') return op === 'ACTION_REQUIRED' || op === 'REOPENED';
    if (statusFilter === 'AWAITING_VERIFICATION') return op === 'AWAITING_VERIFICATION';
    if (statusFilter === 'VERIFIED') return op === 'VERIFIED';
    if (statusFilter === 'CLOSED_HISTORY') return op === 'CLOSED_HISTORY';
    if (statusFilter === 'REJECTED') return val === 'REJECTED';
    return true;
  });

  const candidateCount = patterns.filter(p => p.validation_status === 'CANDIDATE').length;
  const actionRequiredCount = patterns.filter(p => p.operational_status === 'ACTION_REQUIRED' || p.operational_status === 'REOPENED').length;
  const awaitingVerifCount = patterns.filter(p => p.operational_status === 'AWAITING_VERIFICATION').length;
  const verifiedCount = patterns.filter(p => p.operational_status === 'VERIFIED').length;
  const closedHistoryCount = patterns.filter(p => p.operational_status === 'CLOSED_HISTORY').length;
  const rejectedCount = patterns.filter(p => p.validation_status === 'REJECTED').length;
  const validatedCount = patterns.filter(p => p.validation_status === 'HSE_VALIDATED' || p.is_validated).length;

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
              Underlying Control Breaches • HSE Human-in-Loop • Closed-Loop Corrective Action
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            Safety Memory & Recurring Pattern Governance
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
        <div className={`p-3.5 rounded-xl border font-bold text-xs flex items-center justify-between animate-fade-in shadow-sm ${
          feedbackType === 'error' 
            ? 'bg-red-50 border-red-300 text-red-950' 
            : 'bg-purple-50 border-purple-300 text-purple-950'
        }`}>
          <div className="flex items-center space-x-2">
            {feedbackType === 'error' ? (
              <AlertOctagon className="w-4 h-4 text-red-700 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-purple-700 flex-shrink-0" />
            )}
            <span>{feedbackMsg}</span>
          </div>
          <button onClick={() => setFeedbackMsg(null)} className="hover:opacity-70 text-xs font-bold">✕</button>
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
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Pattern Actions</span>
          <span className="text-2xl font-black text-amber-600 mt-1 block">
            {actionRequiredCount + awaitingVerifCount}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">{actionRequiredCount} assigned • {awaitingVerifCount} awaiting verification</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Closed / Historical Memory</span>
          <span className="text-2xl font-black text-emerald-700 mt-1 block">
            {closedHistoryCount}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Verified & preserved in history</span>
        </div>
      </div>

      {/* 3. Operational Filter Navigation Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-2 gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
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
            onClick={() => setStatusFilter('ACTION_REQUIRED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'ACTION_REQUIRED'
                ? 'bg-orange-600 text-white shadow-sm'
                : 'bg-orange-50 text-orange-800 hover:bg-orange-100 border border-orange-200'
            }`}
          >
            Action Required ({actionRequiredCount})
          </button>
          <button
            onClick={() => setStatusFilter('AWAITING_VERIFICATION')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'AWAITING_VERIFICATION'
                ? 'bg-yellow-600 text-white shadow-sm'
                : 'bg-yellow-50 text-yellow-800 hover:bg-yellow-100 border border-yellow-200'
            }`}
          >
            Awaiting Verification ({awaitingVerifCount})
          </button>
          <button
            onClick={() => setStatusFilter('VERIFIED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'VERIFIED'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-emerald-50 text-emerald-800 hover:bg-emerald-100 border border-emerald-200'
            }`}
          >
            Verified / Ready to Close ({verifiedCount})
          </button>
          <button
            onClick={() => setStatusFilter('CLOSED_HISTORY')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'CLOSED_HISTORY'
                ? 'bg-slate-700 text-white shadow-sm'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
            }`}
          >
            Closed / History ({closedHistoryCount})
          </button>
          <button
            onClick={() => setStatusFilter('REJECTED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              statusFilter === 'REJECTED'
                ? 'bg-rose-700 text-white shadow-sm'
                : 'bg-rose-50 text-rose-800 hover:bg-rose-100 border border-rose-200'
            }`}
          >
            Rejected ({rejectedCount})
          </button>
        </div>

        <span className="text-xs text-slate-500 hidden md:inline">
          Showing <strong className="text-slate-800">{filteredPatterns.length}</strong> patterns
        </span>
      </div>

      {/* 4. Pattern Cards Display */}
      <div className="space-y-4">
        {filteredPatterns.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 space-y-2">
            <Layers className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-xs font-bold text-slate-700">No recurring control patterns in this category.</p>
            <p className="text-[11px] text-slate-400">Patterns are discovered by two-stage recurrence analysis and managed through the HSE lifecycle.</p>
          </div>
        ) : (
          filteredPatterns.map((p) => {
            const isValidated = p.validation_status === 'HSE_VALIDATED' || p.is_validated;
            const isRejected = p.validation_status === 'REJECTED';
            const isCandidate = !isValidated && !isRejected;

            const opStatus = p.operational_status || 'NONE';
            const isActionRequired = opStatus === 'ACTION_REQUIRED';
            const isAwaitingVerification = opStatus === 'AWAITING_VERIFICATION';
            const isVerified = opStatus === 'VERIFIED';
            const isClosedHistory = opStatus === 'CLOSED_HISTORY';
            const isReopened = opStatus === 'REOPENED';

            const sourceBreakdown = p.source_breakdown || { Human: 0, CCTV: 0, Imported: 0 };

            return (
              <div 
                key={p.pattern_id}
                className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition-all ${
                  isClosedHistory
                    ? 'border-slate-300 bg-slate-50/50'
                    : isVerified
                    ? 'border-emerald-300 ring-1 ring-emerald-200 bg-emerald-50/15'
                    : isAwaitingVerification
                    ? 'border-yellow-400 ring-1 ring-yellow-200 bg-yellow-50/20'
                    : isReopened
                    ? 'border-rose-400 ring-1 ring-rose-200 bg-rose-50/20'
                    : isActionRequired
                    ? 'border-orange-300 ring-1 ring-orange-200 bg-orange-50/15'
                    : isValidated 
                    ? 'border-emerald-300 ring-1 ring-emerald-200 bg-emerald-50/10' 
                    : isRejected
                    ? 'border-slate-300 bg-slate-50/60 opacity-80'
                    : 'border-amber-200 ring-1 ring-amber-100'
                }`}
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border">
                        {p.pattern_id}
                      </span>

                      {/* HSE Validation State Badge */}
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                        isValidated 
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                          : isRejected
                          ? 'bg-slate-200 text-slate-700 border-slate-300'
                          : 'bg-amber-100 text-amber-800 border-amber-300'
                      }`}>
                        {isValidated 
                          ? '✓ HSE VALIDATED' 
                          : isRejected
                          ? '✕ REJECTED BY HSE'
                          : '⚡ CANDIDATE PATTERN'}
                      </span>

                      {/* Operational Lifecycle Badge */}
                      {opStatus !== 'NONE' && (
                        <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border flex items-center gap-1 ${
                          isClosedHistory
                            ? 'bg-slate-200 text-slate-800 border-slate-300'
                            : isVerified
                            ? 'bg-emerald-100 text-emerald-900 border-emerald-400'
                            : isAwaitingVerification
                            ? 'bg-yellow-100 text-yellow-900 border-yellow-400 animate-pulse'
                            : isReopened
                            ? 'bg-rose-100 text-rose-900 border-rose-400 font-extrabold'
                            : isActionRequired
                            ? 'bg-orange-100 text-orange-900 border-orange-400'
                            : 'bg-slate-100 text-slate-800 border-slate-200'
                        }`}>
                          {isClosedHistory && '⚪ CLOSED / HISTORY'}
                          {isVerified && '🟢 VERIFIED (READY TO CLOSE)'}
                          {isAwaitingVerification && '🟡 AWAITING VERIFICATION'}
                          {isReopened && '🔴 REOPENED (RE-BREACH)'}
                          {isActionRequired && '🟠 ACTION ASSIGNED'}
                        </span>
                      )}

                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
                        {p.independent_occurrences || p.occurrence_count || 1} INDEPENDENT OCCURRENCES
                      </span>

                      {p.sif_potential && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                          SIF: {p.sif_potential}
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-black text-slate-900 mt-1">
                      {p.pattern_title || p.title}
                    </h3>
                  </div>

                  {/* Operational Action Controls */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* View Details Button - Always Available */}
                    <button
                      onClick={() => handleOpenDetails(p)}
                      className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                    >
                      <Eye className="w-3.5 h-3.5 text-slate-500" />
                      <span>VIEW DETAILS</span>
                    </button>

                    {/* Candidate Actions */}
                    {isCandidate && (
                      <>
                        <button
                          onClick={() => handleValidate(p.pattern_id, 'CONFIRM')}
                          disabled={validatingId === p.pattern_id}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>CONFIRM PATTERN</span>
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

                    {/* Validated & Ready for Action */}
                    {isValidated && (opStatus === 'NONE' || opStatus === 'ACTIVE' || !p.operational_status) && (
                      <button
                        onClick={() => handleOpenAssignModal(p)}
                        className="px-3 py-1.5 bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>ASSIGN CORRECTIVE ACTION</span>
                      </button>
                    )}

                    {/* Reopened: allow re-assigning if needed */}
                    {isReopened && (
                      <button
                        onClick={() => handleOpenAssignModal(p)}
                        className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>RE-ASSIGN ACTION</span>
                      </button>
                    )}

                    {/* Verified & Ready for Final HSE Closure */}
                    {isVerified && (
                      <button
                        onClick={() => handleOpenCloseModal(p)}
                        className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white font-black text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                      >
                        <Archive className="w-3.5 h-3.5" />
                        <span>HSE CLOSE PATTERN</span>
                      </button>
                    )}

                    {/* Closed pattern note */}
                    {isClosedHistory && (
                      <span className="text-[11px] font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 flex items-center gap-1">
                        <History className="w-3.5 h-3.5 text-slate-500" />
                        Preserved in History
                      </span>
                    )}
                  </div>
                </div>

                {/* Underlying Control Mechanism Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Activity • Location</span>
                    <span className="font-bold text-slate-900 mt-1 block">
                      {p.activity}
                    </span>
                    <span className="text-[11px] text-slate-600 flex items-center gap-1 mt-0.5">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      {p.location || 'Lifting Zone 03'}
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Failed Critical Control</span>
                    <span className="font-bold text-red-700 mt-1 block">
                      {p.barrier || p.critical_barrier}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {p.barrier_condition || 'Control Breached'} • {p.energy || 'Kinetic / Mechanical'}
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Recurrence Verification</span>
                    <span className="font-bold text-slate-800 mt-1 block">
                      {p.independent_occurrences || p.occurrence_count || 1} independent failures
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {p.duplicate_count || 0} duplicate reports filtered
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Evidence Source Breakdown</span>
                    <div className="mt-1 flex items-center space-x-1.5 text-[11px] font-bold">
                      <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                        Human: {sourceBreakdown.Human || 0}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                        CCTV: {sourceBreakdown.CCTV || 0}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-800">
                        Import: {sourceBreakdown.Imported || 0}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Assigned Action / Verification Progress Banner */}
                {(isActionRequired || isAwaitingVerification || isVerified || isReopened) && (
                  <div className={`p-3.5 rounded-lg border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                    isReopened
                      ? 'bg-rose-50 border-rose-300 text-rose-950'
                      : isAwaitingVerification
                      ? 'bg-yellow-50 border-yellow-300 text-yellow-950'
                      : isVerified
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                      : 'bg-orange-50 border-orange-300 text-orange-950'
                  }`}>
                    <div className="space-y-1">
                      <div className="flex items-center space-x-1.5 font-bold uppercase tracking-wider text-[11px]">
                        {isReopened ? (
                          <AlertTriangle className="w-4 h-4 text-rose-700" />
                        ) : isAwaitingVerification ? (
                          <Clock className="w-4 h-4 text-yellow-700 animate-spin" />
                        ) : isVerified ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                        ) : (
                          <Send className="w-4 h-4 text-orange-700" />
                        )}
                        <span>
                          {isReopened && 'Action Reopened: Person re-entered restricted zone during verification'}
                          {isAwaitingVerification && 'Supervisor Reported Completion — Awaiting CCTV Verification'}
                          {isVerified && 'CCTV Objective Verification Passed: Observable Condition Clear'}
                          {isActionRequired && `Corrective Action Dispatched to Supervisor (${p.assigned_supervisor || 'Rajesh Kumar'})`}
                        </span>
                      </div>
                      <p className="text-xs text-slate-800">
                        <strong>Required Action:</strong> {p.assigned_action || 'Clear unauthorized personnel and secure restricted zone.'}
                      </p>
                    </div>

                    {/* Quick Verification Trigger Controls for Demo/Operator */}
                    {isAwaitingVerification && (
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <button
                          onClick={() => handleCctvVerify(p.pattern_id, false)}
                          disabled={verifyingId === p.pattern_id}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
                          title="Simulate CCTV verifying area is clear"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Condition Clear (Verify)</span>
                        </button>
                        <button
                          onClick={() => handleCctvVerify(p.pattern_id, true)}
                          disabled={verifyingId === p.pattern_id}
                          className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
                          title="Simulate CCTV detecting person still in zone (re-breach)"
                        >
                          <AlertOctagon className="w-3.5 h-3.5" />
                          <span>Re-Breach (Fail)</span>
                        </button>
                      </div>
                    )}

                    {isReopened && (
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        <button
                          onClick={() => handleCctvVerify(p.pattern_id, false)}
                          disabled={verifyingId === p.pattern_id}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Re-Verify CCTV Clear</span>
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Embedded CCTV Preview (If awaiting verification or reopened) */}
                {(isAwaitingVerification || isReopened) && (
                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-700 text-white space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-2 font-mono font-bold">
                        <Camera className="w-4 h-4 text-emerald-400" />
                        <span>EMBEDDED CCTV VERIFICATION FEED • {p.location || 'Lifting Zone 03'}</span>
                        <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-[10px]">LIVE</span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Camera: C-01 (Rig Crane Exclusion Perimeter)
                      </span>
                    </div>

                    <div className="relative aspect-video max-h-52 rounded overflow-hidden bg-black flex items-center justify-center border border-slate-800">
                      <img 
                        src={`/video_feed?camera=C-01&t=${cctvStreamKey}`} 
                        alt="CCTV Verification Stream"
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none">
                        <span className="bg-black/80 text-[10px] font-mono px-2 py-0.5 rounded text-amber-300 border border-white/10">
                          {isAwaitingVerification ? '🟡 AWAITING OBSERVABLE CLEARANCE' : '🔴 RE-BREACH DETECTED'}
                        </span>
                        <span className="bg-black/80 text-[10px] font-mono px-2 py-0.5 rounded text-slate-300 border border-white/10">
                          AI ONNX Vision Monitor
                        </span>
                      </div>
                    </div>
                  </div>
                )}

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

      {/* ============================================================ */}
      {/* MODAL 1: VIEW DETAILS (Full 18-Point Evidence Explanation)   */}
      {/* ============================================================ */}
      {detailsModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-6 space-y-6">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-800 border">
                    {selectedDetails?.pattern_id || 'PAT-DETAILS'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-purple-100 text-purple-900">
                    Evidence-Grounded Explanation
                  </span>
                </div>
                <h2 className="text-lg font-black text-slate-900 mt-1">
                  {selectedDetails?.pattern_name || 'Safety Pattern Details'}
                </h2>
              </div>
              <button 
                onClick={() => setDetailsModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {detailsLoading ? (
              <div className="p-12 text-center text-slate-500 space-y-2">
                <RefreshCw className="w-8 h-8 animate-spin text-purple-600 mx-auto" />
                <p className="text-xs font-bold">Retrieving evidence-grounded pattern details from SQLite...</p>
              </div>
            ) : selectedDetails ? (
              <div className="space-y-5 text-xs">
                
                {/* 18-Point Evidence Breakdown Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">1. Activity & Location</span>
                    <p className="font-bold text-slate-900">{selectedDetails.activity || 'Mechanical Lifting'}</p>
                    <p className="text-slate-600 flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-400" />
                      {selectedDetails.location || 'Lifting Zone 03'}
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">2. Occurrences & Sources</span>
                    <p className="font-bold text-purple-900">
                      {selectedDetails.independent_occurrences} Independent Occurrences
                    </p>
                    <div className="flex gap-1.5 text-[10px] font-bold mt-0.5">
                      <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded">
                        Human: {selectedDetails.source_breakdown?.Human || 0}
                      </span>
                      <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded">
                        CCTV: {selectedDetails.source_breakdown?.CCTV || 0}
                      </span>
                      <span className="px-1.5 py-0.5 bg-slate-200 text-slate-800 rounded">
                        Import: {selectedDetails.source_breakdown?.Imported || 0}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">3. SIF Potential & LSR</span>
                    <p className="font-bold text-rose-700">
                      SIF: {selectedDetails.sif_potential || 'HIGH'}
                    </p>
                    <p className="text-slate-700 font-semibold">
                      Rule: {selectedDetails.iogp_life_saving_rule || 'Line of Fire'}
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">4. Failed Critical Barrier</span>
                    <p className="font-bold text-red-700">{selectedDetails.failed_barrier || 'Exclusion Zone Perimeter'}</p>
                    <p className="text-slate-500 text-[11px]">{selectedDetails.hazard_energy || 'Kinetic / Gravitational Energy'}</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">5. Human Exposure</span>
                    <p className="font-semibold text-slate-800">{selectedDetails.human_exposure || 'Personnel inside active zone under suspended load'}</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">6. HSE Validation State</span>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-100 text-emerald-800 border border-emerald-300">
                      {selectedDetails.hse_validation_state || 'HSE_VALIDATED'}
                    </span>
                    <p className="text-slate-500 text-[10px]">Reviewed by Oil India HSE Lead</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">7. Operational Action State</span>
                    <p className="font-bold text-orange-900">{selectedDetails.action_state || 'ACTION_REQUIRED'}</p>
                    <p className="text-slate-600 text-[11px]">Supervisor: {selectedDetails.assigned_supervisor || 'SUP-01 (Rajesh Kumar)'}</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">8. Verification Status</span>
                    <p className="font-bold text-slate-900">{selectedDetails.verification_state || 'PENDING'}</p>
                    <p className="text-slate-500 text-[10px]">Method: Observable CCTV Stream</p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">9. Lifecycle Stage</span>
                    <p className="font-bold text-purple-900">{selectedDetails.operational_status || 'ACTIVE'}</p>
                    <p className="text-slate-500 text-[10px]">Audit trail logged to SQLite</p>
                  </div>
                </div>

                {/* Real Supporting Safety Events (Point 5) */}
                <div className="space-y-2 pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-purple-600" />
                      <span>Supporting Safety Events ({selectedDetails.supporting_safety_events?.length || 0})</span>
                    </h3>
                    <span className="text-[10px] text-slate-400">Ground-truth SQLite records</span>
                  </div>

                  <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                    {(selectedDetails.supporting_safety_events || []).map((ev, idx) => (
                      <div key={idx} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-[10px] text-slate-800">{ev.event_id}</span>
                          <span className="text-[10px] text-slate-400">{ev.timestamp}</span>
                        </div>
                        <p className="text-slate-700 text-[11px] font-medium leading-relaxed">{ev.narrative}</p>
                        <div className="flex items-center gap-2 text-[10px] text-slate-500">
                          <span>Source: <strong>{ev.source}</strong></span>
                          <span>•</span>
                          <span>Location: <strong>{ev.location}</strong></span>
                          <span>•</span>
                          <span>Barrier: <strong className="text-red-700">{ev.barrier} ({ev.barrier_condition})</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Evidence Snippets (Point 12) */}
                {selectedDetails.evidence_snippets && selectedDetails.evidence_snippets.length > 0 && (
                  <div className="space-y-2 pt-2 border-t">
                    <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <span>Evidence Text Snippets from Reports</span>
                    </h3>
                    <div className="space-y-1.5">
                      {selectedDetails.evidence_snippets.map((snip, sIdx) => (
                        <div key={sIdx} className="p-2 rounded bg-blue-50/60 border border-blue-200 font-mono text-[11px] text-blue-950">
                          "{snip}"
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Verification & Re-Breach History (Point 18) */}
                <div className="space-y-2 pt-2 border-t">
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                    <History className="w-4 h-4 text-slate-600" />
                    <span>Previous Verification & Re-Breach History</span>
                  </h3>
                  {selectedDetails.verification_history && selectedDetails.verification_history.length > 0 ? (
                    <div className="space-y-1.5">
                      {selectedDetails.verification_history.map((vh, vIdx) => (
                        <div key={vIdx} className={`p-2 rounded border text-[11px] flex items-center justify-between ${
                          vh.status === 'VERIFIED' ? 'bg-emerald-50 border-emerald-200 text-emerald-950' : 'bg-red-50 border-red-200 text-red-950'
                        }`}>
                          <div className="space-y-0.5">
                            <span className="font-bold uppercase tracking-wider">{vh.status}</span>
                            <p className="text-[10px]">{vh.details?.message || vh.details?.notes || 'Verification event logged'}</p>
                          </div>
                          <span className="text-[10px] font-mono opacity-75">{vh.timestamp}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 italic text-[11px]">No previous verification attempts recorded for this pattern.</p>
                  )}
                </div>

              </div>
            ) : null}

            {/* Footer */}
            <div className="flex justify-end pt-3 border-t">
              <button
                onClick={() => setDetailsModalOpen(false)}
                className="px-4 py-2 bg-slate-900 hover:bg-black text-white text-xs font-bold rounded-lg transition-colors"
              >
                Close Details
              </button>
            </div>

          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL 2: ASSIGN CORRECTIVE ACTION                           */}
      {/* ============================================================ */}
      {assignModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-orange-100 text-orange-900">
                  HSE Governance Action
                </span>
                <h2 className="text-base font-black text-slate-900 mt-1">
                  Assign Corrective Action
                </h2>
              </div>
              <button 
                onClick={() => setAssignModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitAssignAction} className="space-y-3.5 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Target Pattern</label>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-medium text-slate-800">
                  <span className="font-mono font-bold">{assigningPattern?.pattern_id}</span> — {assigningPattern?.pattern_title || assigningPattern?.title}
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Responsible Supervisor</label>
                <select
                  value={assignForm.supervisor_id}
                  onChange={(e) => {
                    const sid = e.target.value;
                    let sname = 'Rajesh Kumar (Field Lead)';
                    if (sid === 'SUP-ELEC-02') sname = 'Amit Verma (Electrical Lead)';
                    if (sid === 'SUP-CIVIL-03') sname = 'Pooja Sharma (Site Safety Supervisor)';
                    setAssignForm(prev => ({ ...prev, supervisor_id: sid, supervisor_name: sname }));
                  }}
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-semibold bg-white text-slate-900"
                >
                  <option value="SUP-01">Rajesh Kumar (Field Lead - Rig Operations)</option>
                  <option value="SUP-ELEC-02">Amit Verma (Electrical Maintenance Lead)</option>
                  <option value="SUP-CIVIL-03">Pooja Sharma (Site Safety Supervisor)</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Affected Location / Zone</label>
                <input
                  type="text"
                  value={assignForm.location}
                  onChange={(e) => setAssignForm(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-semibold text-slate-900"
                  required
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Required Corrective Action</label>
                <textarea
                  rows={2}
                  value={assignForm.required_action}
                  onChange={(e) => setAssignForm(prev => ({ ...prev, required_action: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-medium text-slate-900"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Priority</label>
                  <select
                    value={assignForm.priority}
                    onChange={(e) => setAssignForm(prev => ({ ...prev, priority: e.target.value }))}
                    className="w-full p-2 rounded-lg border border-slate-300 font-semibold bg-white"
                  >
                    <option value="CRITICAL">🔴 CRITICAL (Immediate)</option>
                    <option value="HIGH">🟠 HIGH (Within Shift)</option>
                    <option value="MEDIUM">🟡 MEDIUM</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Verification Method</label>
                  <select
                    value={assignForm.verification_method}
                    onChange={(e) => setAssignForm(prev => ({ ...prev, verification_method: e.target.value }))}
                    className="w-full p-2 rounded-lg border border-slate-300 font-semibold bg-white"
                  >
                    <option value="CCTV_VERIFIABLE">CCTV Observable Zone</option>
                    <option value="ON_SITE_SIGN_OFF">On-Site Physical Check</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setAssignModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-bold rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assignSubmitting}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {assignSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>{assignSubmitting ? 'Dispatching...' : 'Dispatch to Supervisor'}</span>
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL 3: HSE CLOSE PATTERN (Preserve in History)             */}
      {/* ============================================================ */}
      {closeModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-900">
                  HSE Final Closure Authority
                </span>
                <h2 className="text-base font-black text-slate-900 mt-1">
                  Close Safety Pattern
                </h2>
              </div>
              <button 
                onClick={() => setCloseModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitClosePattern} className="space-y-3.5 text-xs">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-950 space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                  <span>Observable Condition Successfully Restored</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  CCTV vision stream confirmed the restricted area is clear. Machine verification alone does not close the pattern; HSE holds final authority for closure.
                </p>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Pattern</label>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 font-medium text-slate-800">
                  <span className="font-mono font-bold">{closingPattern?.pattern_id}</span> — {closingPattern?.pattern_title || closingPattern?.title}
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">HSE Closure Sign-Off Notes</label>
                <textarea
                  rows={3}
                  value={closureNotes}
                  onChange={(e) => setClosureNotes(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-medium text-slate-900"
                  required
                />
              </div>

              <div className="p-2.5 rounded-lg bg-slate-100 border text-slate-600 text-[11px]">
                ℹ️ <strong>Historical Integrity Note:</strong> Closing this pattern moves it to <strong>CLOSED / HISTORY</strong>. It will remain fully searchable and accessible in Safety Memory records.
              </div>

              <div className="pt-3 border-t flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setCloseModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-bold rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={closeSubmitting}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-black rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {closeSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Archive className="w-3.5 h-3.5" />}
                  <span>{closeSubmitting ? 'Closing...' : 'Confirm Closure & Move to History'}</span>
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}
