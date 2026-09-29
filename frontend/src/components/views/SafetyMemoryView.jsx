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
  MapPin,
  Sparkles,
  Zap,
  SlidersHorizontal,
  ExternalLink
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
    { key: 'PHYSICAL_PERIMETER_DEMARCATION', label: 'Physical Perimeter Demarcation (Barricades / Barrier Tape)' },
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

export const getPatternSourceCounts = (p) => {
  if (!p) return { human: 0, cctv: 0, imported: 0 };
  const sb = p.source_breakdown || {};
  let human = sb.Human ?? sb.HUMAN ?? sb.human ?? 0;
  let cctv = sb.CCTV ?? sb.cctv ?? 0;
  let imported = sb.Imported ?? sb.IMPORTED ?? sb.import ?? 0;

  const evts = p.supporting_events || p.supporting_safety_events || [];
  if (human === 0 && cctv === 0 && evts.length > 0) {
    human = evts.filter((e) => (e.source || '').toUpperCase() === 'HUMAN').length;
    cctv = evts.filter((e) => (e.source || '').toUpperCase() === 'CCTV').length;
    imported = evts.filter((e) => (e.source || '').toUpperCase().includes('IMPORT')).length;
  }

  if (human === 0 && cctv === 0 && (p.occurrences || p.occurrence_count)) {
    human = p.occurrences || p.occurrence_count;
  }

  return { human, cctv, imported };
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
  const [detailsTab, setDetailsTab] = useState('breakdown'); // breakdown | events | snippets | history

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
      setDetailsTab('breakdown');
      // Set initial details from clicked pattern so modal displays instantly
      setSelectedDetails(pattern);
      const res = await fetchPatternDetails(pattern.pattern_id);
      const details = res?.pattern_details || res || pattern;
      setSelectedDetails(details);
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

  const candidateCount = patterns.filter(p => p.validation_status === 'CANDIDATE' || (!p.is_validated && p.validation_status !== 'REJECTED')).length;
  const actionRequiredCount = patterns.filter(p => p.operational_status === 'ACTION_REQUIRED' || p.operational_status === 'REOPENED').length;
  const awaitingVerifCount = patterns.filter(p => p.operational_status === 'AWAITING_VERIFICATION').length;
  const verifiedCount = patterns.filter(p => p.operational_status === 'VERIFIED').length;
  const closedHistoryCount = patterns.filter(p => p.operational_status === 'CLOSED_HISTORY').length;
  const rejectedCount = patterns.filter(p => p.validation_status === 'REJECTED').length;
  const validatedCount = patterns.filter(p => p.validation_status === 'HSE_VALIDATED' || p.is_validated).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header Bar — Primary Question: "What keeps recurring again?" */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-purple-100 text-purple-900 border border-purple-200 flex items-center gap-1">
              <Database className="w-3 h-3 text-purple-700" />
              Organizational Safety Memory
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs font-semibold text-slate-500">
              Two-Stage Vector Recurrence Clustering
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Safety Memory & Recurring Patterns
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Surfaces underlying control failures across human reports & computer vision • Human HSE validation required before action dispatch
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastRefreshed && (
            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
              Updated: {lastRefreshed}
            </span>
          )}
          <button 
            onClick={loadData}
            disabled={loading}
            className="px-3 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-sm flex items-center gap-1.5 text-xs font-bold disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-purple-600' : 'text-slate-500'}`} />
            <span>{loading ? 'Refreshing...' : 'Refresh Memory'}</span>
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedbackMsg && (
        <div className={`p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between shadow-sm animate-fade-in ${
          feedbackType === 'error' 
            ? 'bg-rose-50 border-rose-200 text-rose-900' 
            : 'bg-purple-50 border-purple-200 text-purple-900'
        }`}>
          <div className="flex items-center space-x-2.5">
            {feedbackType === 'error' ? (
              <AlertOctagon className="w-4 h-4 text-rose-600 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-purple-600 flex-shrink-0" />
            )}
            <span>{feedbackMsg}</span>
          </div>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-slate-700 font-bold ml-2">✕</button>
        </div>
      )}

      {/* 2. Top Metric Telemetry Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Candidate Patterns</span>
            <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold text-xs">
              ⚡
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2">{candidateCount}</div>
          <p className="text-[11px] text-amber-700 mt-1 font-medium">Awaiting HSE human validation</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">HSE Validated</span>
            <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center font-bold text-xs">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-purple-700 mt-2">{validatedCount}</div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">Active in organizational memory</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Active Actions</span>
            <div className="w-7 h-7 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center font-bold text-xs">
              <Send className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-orange-600 mt-2">{actionRequiredCount + awaitingVerifCount}</div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">
            {actionRequiredCount} assigned • {awaitingVerifCount} awaiting verification
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Historical Memory</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-xs">
              <Archive className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-700 mt-2">{closedHistoryCount}</div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">Verified & closed into learning</p>
        </div>
      </div>

      {/* 3. Operational Filter Navigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-2 rounded-xl border border-slate-200">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'ALL'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            <span>All Patterns</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'ALL' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-600'}`}>
              {patterns.length}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('CANDIDATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'CANDIDATE'
                ? 'bg-amber-600 text-white shadow-sm'
                : 'bg-white text-amber-800 hover:bg-amber-50 border border-amber-200'
            }`}
          >
            <span>Candidates</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'CANDIDATE' ? 'bg-amber-700 text-white' : 'bg-amber-100 text-amber-800'}`}>
              {candidateCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('ACTION_REQUIRED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'ACTION_REQUIRED'
                ? 'bg-orange-600 text-white shadow-sm'
                : 'bg-white text-orange-800 hover:bg-orange-50 border border-orange-200'
            }`}
          >
            <span>Action Required</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'ACTION_REQUIRED' ? 'bg-orange-700 text-white' : 'bg-orange-100 text-orange-800'}`}>
              {actionRequiredCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('AWAITING_VERIFICATION')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'AWAITING_VERIFICATION'
                ? 'bg-yellow-600 text-white shadow-sm'
                : 'bg-white text-yellow-800 hover:bg-yellow-50 border border-yellow-200'
            }`}
          >
            <span>Awaiting Verification</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'AWAITING_VERIFICATION' ? 'bg-yellow-700 text-white' : 'bg-yellow-100 text-yellow-800'}`}>
              {awaitingVerifCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('VERIFIED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'VERIFIED'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-white text-emerald-800 hover:bg-emerald-50 border border-emerald-200'
            }`}
          >
            <span>Verified (Ready to Close)</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'VERIFIED' ? 'bg-emerald-700 text-white' : 'bg-emerald-100 text-emerald-800'}`}>
              {verifiedCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('CLOSED_HISTORY')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
              statusFilter === 'CLOSED_HISTORY'
                ? 'bg-slate-700 text-white shadow-sm'
                : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'
            }`}
          >
            <span>Closed History</span>
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'CLOSED_HISTORY' ? 'bg-slate-600 text-white' : 'bg-slate-100 text-slate-700'}`}>
              {closedHistoryCount}
            </span>
          </button>

          {rejectedCount > 0 && (
            <button
              onClick={() => setStatusFilter('REJECTED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                statusFilter === 'REJECTED'
                  ? 'bg-rose-700 text-white shadow-sm'
                  : 'bg-white text-rose-800 hover:bg-rose-50 border border-rose-200'
              }`}
            >
              <span>Rejected</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${statusFilter === 'REJECTED' ? 'bg-rose-800 text-white' : 'bg-rose-100 text-rose-800'}`}>
                {rejectedCount}
              </span>
            </button>
          )}
        </div>

        <span className="text-xs text-slate-500 font-medium px-2">
          Showing <strong className="text-slate-800">{filteredPatterns.length}</strong> patterns
        </span>
      </div>

      {/* 4. Pattern Cards Display */}
      <div className="space-y-4">
        {filteredPatterns.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-3">
            <Layers className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="text-sm font-bold text-slate-700">No recurring control patterns in this view</p>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Candidate patterns are automatically formulated by vector recurrence clustering when multiple independent reports violate identical critical safety barriers.
            </p>
          </div>
        ) : (
          filteredPatterns.map((p) => {
            const isValidated = p.validation_status === 'HSE_VALIDATED' || p.is_validated;
            const isRejected = p.validation_status === 'REJECTED';
            const isCandidate = !isValidated && !isRejected;

            const opStatus = p.operational_status || 'NONE';
            const isActionRequired = opStatus === 'ACTION_REQUIRED' || opStatus === 'DISPATCHED';
            const isActionInProgress = opStatus === 'ACTION_IN_PROGRESS';
            const isAwaitingVerification = opStatus === 'AWAITING_VERIFICATION';
            const isVerified = opStatus === 'VERIFIED';
            const isClosedHistory = opStatus === 'CLOSED_HISTORY';
            const isReopened = opStatus === 'REOPENED';

            const sourceBreakdown = getPatternSourceCounts(p);
            const totalOccurrences = p.independent_occurrences || (sourceBreakdown.human + sourceBreakdown.cctv + sourceBreakdown.imported) || p.occurrence_count || 1;

            return (
              <div 
                key={p.pattern_id}
                className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition-all ${
                  isClosedHistory
                    ? 'border-slate-200 bg-slate-50/40 opacity-90'
                    : isVerified
                    ? 'border-emerald-300 ring-1 ring-emerald-100 bg-emerald-50/10'
                    : isAwaitingVerification
                    ? 'border-yellow-300 ring-1 ring-yellow-100 bg-yellow-50/15'
                    : isReopened
                    ? 'border-rose-300 ring-1 ring-rose-100 bg-rose-50/15'
                    : isActionRequired
                    ? 'border-orange-300 ring-1 ring-orange-100 bg-orange-50/10'
                    : isValidated 
                    ? 'border-purple-200 ring-1 ring-purple-100' 
                    : isRejected
                    ? 'border-slate-200 bg-slate-50/60 opacity-75'
                    : 'border-amber-200 ring-1 ring-amber-100'
                }`}
              >
                {/* Header Row */}
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                        {p.pattern_id}
                      </span>

                      {/* HSE Validation State Badge */}
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${
                        isValidated 
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300' 
                          : isRejected
                          ? 'bg-slate-100 text-slate-700 border-slate-300'
                          : 'bg-amber-50 text-amber-800 border-amber-300'
                      }`}>
                        {isValidated 
                          ? '✓ HSE VALIDATED' 
                          : isRejected
                          ? '✕ REJECTED BY HSE'
                          : '⚡ CANDIDATE PATTERN'}
                      </span>

                      {/* Operational Lifecycle Badge */}
                      {opStatus !== 'NONE' && (
                        <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border flex items-center gap-1 ${
                          isClosedHistory
                            ? 'bg-slate-100 text-slate-700 border-slate-300'
                            : isVerified
                            ? 'bg-emerald-100 text-emerald-900 border-emerald-400'
                            : isAwaitingVerification
                            ? 'bg-yellow-100 text-yellow-900 border-yellow-400 animate-pulse'
                            : isReopened
                            ? 'bg-rose-100 text-rose-900 border-rose-400 font-extrabold'
                            : isActionInProgress
                            ? 'bg-blue-100 text-blue-900 border-blue-400 animate-pulse'
                            : isActionRequired
                            ? 'bg-orange-100 text-orange-900 border-orange-400'
                            : 'bg-slate-100 text-slate-800 border-slate-200'
                        }`}>
                          {isClosedHistory && '⚪ CLOSED / HISTORY'}
                          {isVerified && '🟢 VERIFIED (READY TO CLOSE)'}
                          {isAwaitingVerification && '🟡 AWAITING VERIFICATION'}
                          {isReopened && '🔴 REOPENED (RE-BREACH)'}
                          {isActionInProgress && '🔵 ACTION IN PROGRESS'}
                          {isActionRequired && '🟠 ACTION DISPATCHED'}
                        </span>
                      )}

                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-800 border border-purple-200">
                        {totalOccurrences} INDEPENDENT OCCURRENCES
                      </span>

                      {p.sif_potential && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-800 border border-rose-200">
                          SIF: {p.sif_potential}
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-black text-slate-900 tracking-tight mt-1">
                      {p.pattern_title || p.title}
                    </h3>
                  </div>

                  {/* Primary Action Controls */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* View Details Button */}
                    <button
                      onClick={() => handleOpenDetails(p)}
                      className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                    >
                      <Eye className="w-3.5 h-3.5 text-slate-500" />
                      <span>VIEW EVIDENCE</span>
                    </button>

                    {/* Candidate Actions */}
                    {isCandidate && (
                      <>
                        <button
                          onClick={() => handleValidate(p.pattern_id, 'CONFIRM')}
                          disabled={validatingId === p.pattern_id}
                          className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1 disabled:opacity-50"
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
                    {isValidated && !p.assigned_action && (
                      <button
                        id={`btn-assign-supervisor-${p.pattern_id}`}
                        onClick={() => handleOpenAssignModal(p)}
                        className="px-3.5 py-1.5 bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>ASSIGN SUPERVISOR / DISPATCH</span>
                      </button>
                    )}

                    {/* Reopened: allow re-assigning if needed */}
                    {isReopened && (
                      <button
                        onClick={() => handleOpenAssignModal(p)}
                        className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>RE-ASSIGN ACTION</span>
                      </button>
                    )}

                    {/* Verified & Ready for Final HSE Closure */}
                    {isVerified && (
                      <button
                        id={`btn-close-${p.pattern_id}`}
                        onClick={() => handleOpenCloseModal(p)}
                        className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white font-black text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-1"
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
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200/80">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">Activity • Location</span>
                    <span className="font-bold text-slate-900 mt-1 block truncate">
                      {p.activity}
                    </span>
                    <span className="text-[11px] text-slate-600 flex items-center gap-1 mt-0.5">
                      <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                      <span className="truncate">{p.location || 'Lifting Zone 03'}</span>
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200/80">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">Failed Critical Control</span>
                    <span className="font-bold text-rose-700 mt-1 block truncate">
                      {p.barrier || p.critical_barrier}
                    </span>
                    <span className="text-[10px] text-slate-500 block truncate">
                      {p.barrier_condition || 'Control Breached'} • {p.energy || 'Kinetic Energy'}
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200/80">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">Recurrence Verification</span>
                    <span className="font-bold text-slate-800 mt-1 block">
                      {totalOccurrences} independent failures
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {p.duplicate_count || 0} duplicates filtered out
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50/70 rounded-lg border border-slate-200/80">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">Evidence Source Breakdown</span>
                    <div className="mt-1 flex items-center space-x-1.5 text-[10px] font-bold">
                      <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                        Human: {sourceBreakdown.human}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
                        CCTV: {sourceBreakdown.cctv}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                        Import: {sourceBreakdown.imported}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Assigned Action / Verification Progress Banner */}
                {(isActionRequired || isActionInProgress || isAwaitingVerification || isVerified || isReopened) && (
                  <div className={`p-4 rounded-xl border text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                    isReopened
                      ? 'bg-rose-50 border-rose-200 text-rose-950'
                      : isAwaitingVerification
                      ? 'bg-yellow-50 border-yellow-200 text-yellow-950'
                      : isVerified
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                      : isActionInProgress
                      ? 'bg-blue-50 border-blue-200 text-blue-950'
                      : 'bg-orange-50 border-orange-200 text-orange-950'
                  }`}>
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2 font-bold uppercase tracking-wider text-[11px]">
                        {isReopened ? (
                          <AlertTriangle className="w-4 h-4 text-rose-700 flex-shrink-0" />
                        ) : isAwaitingVerification ? (
                          <Clock className="w-4 h-4 text-yellow-700 animate-spin flex-shrink-0" />
                        ) : isVerified ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                        ) : isActionInProgress ? (
                          <RefreshCw className="w-4 h-4 text-blue-700 animate-spin flex-shrink-0" />
                        ) : (
                          <Send className="w-4 h-4 text-orange-700 flex-shrink-0" />
                        )}
                        <span>
                          {isReopened && 'Action Reopened: Person re-entered restricted zone during verification'}
                          {isAwaitingVerification && 'Supervisor Reported Completion — Awaiting CCTV Verification'}
                          {isVerified && 'CCTV Objective Verification Passed: Observable Condition Clear'}
                          {isActionInProgress && `Intervention In Progress by Supervisor (${p.assigned_supervisor || (typeof p.assigned_action === 'object' ? p.assigned_action?.supervisor_name : null) || 'Rajesh Kumar'})`}
                          {isActionRequired && `Corrective Action Dispatched to Supervisor (${p.assigned_supervisor || (typeof p.assigned_action === 'object' ? p.assigned_action?.supervisor_name : null) || 'Rajesh Kumar'})`}
                        </span>
                      </div>
                      <p className="text-xs text-slate-800">
                        <strong>Required Action:</strong> {(typeof p.assigned_action === 'object' ? p.assigned_action?.required_action : p.assigned_action) || 'Clear unauthorized personnel and secure restricted zone.'}
                      </p>
                      {typeof p.assigned_action === 'object' && p.assigned_action && (
                        <div className="flex flex-wrap gap-3 text-[11px] text-slate-600 pt-0.5">
                          {p.assigned_action.location && <span><strong>Location:</strong> {p.assigned_action.location}</span>}
                          {p.assigned_action.priority && <span><strong>Priority:</strong> {p.assigned_action.priority}</span>}
                          {p.assigned_action.verification_method && <span><strong>Verification:</strong> {p.assigned_action.verification_method}</span>}
                        </div>
                      )}
                    </div>

                    {/* Quick Verification Trigger Controls for Demo/Operator */}
                    {isAwaitingVerification && (
                      <div className="flex items-center space-x-2 flex-shrink-0 pt-2 md:pt-0">
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
                      <div className="flex items-center space-x-2 flex-shrink-0 pt-2 md:pt-0">
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
                  <div className="p-3.5 bg-slate-900 rounded-xl border border-slate-800 text-white space-y-2.5">
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

                    <div className="relative aspect-video max-h-56 rounded-lg overflow-hidden bg-black flex items-center justify-center border border-slate-800">
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

                {/* Future Safety Preconditions Banner */}
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
      <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm space-y-5">
        <div className="border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs">
              <FileCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-black uppercase tracking-wider text-slate-900">
                Future-Work Safety Evidence Check (Pre-Job Authorization)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Simulates how validated Safety Memory checks upcoming permits against required observable evidence before authorization.
                SHRAMRAKSHAK flags missing critical safety evidence for human HSE review.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-xs">
          <div>
            <label className="font-bold text-slate-700 block mb-1.5">Work Package Task Type</label>
            <select
              value={wpTaskType}
              onChange={(e) => handleTaskTypeChange(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 font-semibold focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="Mechanical Lifting">Mechanical Lifting Operations</option>
              <option value="Electrical Maintenance (LOTO)">Electrical Maintenance (LOTO)</option>
              <option value="Confined Space Entry">Confined Space Entry</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1.5">Target Location</label>
            <input
              type="text"
              value={wpLocation}
              onChange={(e) => setWpLocation(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-slate-300 text-slate-900 font-semibold focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1.5">Submitted Safety Evidence</label>
            <div className="space-y-2 pt-0.5">
              {(TASK_EVIDENCE_MAP[wpTaskType] || []).map((evItem) => (
                <label key={evItem.key} className="flex items-start space-x-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={wpEvidenceProvided.includes(evItem.key)}
                    onChange={() => handleToggleEvidence(evItem.key)}
                    className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-slate-800 text-[11px] font-medium leading-tight">{evItem.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleRunWpCheck}
            disabled={wpChecking}
            className="px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center space-x-2 disabled:opacity-50"
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
              : 'bg-rose-50 border-rose-300 text-rose-950'
          }`}>
            <div className="flex items-center justify-between font-bold mb-1">
              <span className="text-xs uppercase tracking-wider flex items-center gap-1.5">
                {wpResult.status === 'PASS' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertOctagon className="w-4 h-4 text-rose-600" />
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
              <div className="mt-3 pt-2.5 border-t border-slate-200/80 text-xs">
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
              <div className="mt-2.5 pt-2.5 border-t border-rose-200 text-xs">
                <span className="font-bold text-rose-900 block mb-1">Missing Evidence Items:</span>
                <ul className="list-disc list-inside space-y-0.5 text-rose-800 text-[11px]">
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
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            
            {/* Header */}
            <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50/50">
              <div className="min-w-0 pr-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-200">
                    {selectedDetails?.pattern_id || 'PAT-DETAILS'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-purple-100 text-purple-900 border border-purple-200">
                    Evidence-Grounded Explanation
                  </span>
                </div>
                <h2 className="text-base sm:text-lg font-black text-slate-900 mt-1 truncate">
                  {selectedDetails?.pattern_name || selectedDetails?.pattern_title || selectedDetails?.title || 'Safety Pattern Details'}
                </h2>
              </div>
              <button 
                onClick={() => setDetailsModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 text-sm font-bold transition-colors shrink-0"
              >
                ✕
              </button>
            </div>

            {/* Modal Navigation Tabs */}
            {(() => {
              const evts = selectedDetails?.supporting_events || selectedDetails?.supporting_safety_events || [];
              const rawSnippets = selectedDetails?.evidence_snippets || [];
              const evidenceCount = evts.length > 0 ? evts.length : rawSnippets.length;
              const historyList = selectedDetails?.verification_history || [];

              return (
                <div className="flex border-b border-slate-200 px-4 sm:px-5 gap-3 sm:gap-6 text-xs font-bold shrink-0 overflow-x-auto whitespace-nowrap bg-white">
                  <button
                    onClick={() => setDetailsTab('breakdown')}
                    className={`pb-2.5 pt-2 border-b-2 transition-colors flex items-center gap-1.5 shrink-0 ${
                      detailsTab === 'breakdown'
                        ? 'border-purple-600 text-purple-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <span>Control Breakdown</span>
                  </button>
                  <button
                    onClick={() => setDetailsTab('events')}
                    className={`pb-2.5 pt-2 border-b-2 transition-colors flex items-center gap-1.5 shrink-0 ${
                      detailsTab === 'events'
                        ? 'border-purple-600 text-purple-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <span>Supporting Events</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-600 font-bold">
                      {evts.length}
                    </span>
                  </button>
                  <button
                    onClick={() => setDetailsTab('snippets')}
                    className={`pb-2.5 pt-2 border-b-2 transition-colors flex items-center gap-1.5 shrink-0 ${
                      detailsTab === 'snippets'
                        ? 'border-purple-600 text-purple-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <span>Evidence</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-600 font-bold">
                      {evidenceCount}
                    </span>
                  </button>
                  <button
                    onClick={() => setDetailsTab('history')}
                    className={`pb-2.5 pt-2 border-b-2 transition-colors flex items-center gap-1.5 shrink-0 ${
                      detailsTab === 'history'
                        ? 'border-purple-600 text-purple-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <span>Verification History</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-600 font-bold">
                      {historyList.length}
                    </span>
                  </button>
                </div>
              );
            })()}

            {detailsLoading ? (
              <div className="p-12 text-center text-slate-500 space-y-2 flex-1">
                <RefreshCw className="w-8 h-8 animate-spin text-purple-600 mx-auto" />
                <p className="text-xs font-bold">Retrieving evidence-grounded pattern details from SQLite...</p>
              </div>
            ) : selectedDetails ? (
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 text-xs">
                
                {/* 1. CONTROL BREAKDOWN TAB */}
                {detailsTab === 'breakdown' && (() => {
                  const counts = getPatternSourceCounts(selectedDetails);
                  const totalOccurrences = selectedDetails.independent_occurrences || (counts.human + counts.cctv + counts.imported) || 1;

                  return (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {/* Card 1: Control & Barrier */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">1. Critical Control / Exclusion Zone</span>
                        <p className="font-bold text-slate-900 text-xs mt-0.5">
                          Exclusion Zone ({selectedDetails.failed_barrier || selectedDetails.barrier || selectedDetails.critical_barrier || 'EXCLUSION_ZONE'})
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Exclusion Zone perimeter — primary personnel segregation barrier
                        </p>
                      </div>

                      {/* Card 2: Failure Mechanism */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">2. Failure Mechanism</span>
                        <p className="font-bold text-rose-700 text-xs mt-0.5">
                          {selectedDetails.barrier_condition || selectedDetails.failure_mechanism || 'Restricted-zone barrier breached during active lifting'}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Restricted-zone barrier breached during active lifting (Status: BYPASSED)
                        </p>
                      </div>

                      {/* Card 3: Observed Exposure */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">3. Observed Exposure</span>
                        <p className="font-semibold text-slate-900 text-xs mt-0.5">
                          Person inside lifting exclusion zone
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Observed Exposure: {selectedDetails.human_exposure || selectedDetails.exposure || 'Person inside lifting exclusion zone'}
                        </p>
                      </div>

                      {/* Card 4: Hazard & Energy */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">4. Hazard / Energy</span>
                        <p className="font-bold text-slate-900 text-xs mt-0.5">
                          Gravitational / Kinetic Energy (Suspended Load)
                        </p>
                        <p className="text-[11px] text-slate-500">
                          Hazard / Energy: {selectedDetails.hazard_energy || selectedDetails.hazard || selectedDetails.energy || 'Gravitational / Kinetic Energy'}
                        </p>
                      </div>

                      {/* Card 5: Occurrences & Sources */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">5. Occurrences & Sources</span>
                        <p className="font-bold text-purple-900 text-xs mt-0.5">
                          {totalOccurrences} Independent Occurrences
                        </p>
                        <div className="flex flex-wrap gap-1.5 text-[10px] font-bold mt-1">
                          <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded border border-blue-200">
                            Human: {counts.human}
                          </span>
                          <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded border border-purple-200">
                            CCTV: {counts.cctv}
                          </span>
                          <span className="px-1.5 py-0.5 bg-slate-200 text-slate-800 rounded border border-slate-300">
                            Import: {counts.imported}
                          </span>
                        </div>
                      </div>

                      {/* Card 6: SIF Potential & LSR */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">6. SIF Potential & LSR</span>
                        <p className="font-bold text-rose-700 text-xs mt-0.5">
                          SIF: {selectedDetails.sif_potential || 'HIGH'}
                        </p>
                        <p className="text-slate-700 font-semibold text-[11px]">
                          Rule: {selectedDetails.iogp_life_saving_rule || selectedDetails.life_saving_rule || selectedDetails.primary_lsr || 'Safe Mechanical Lifting'}
                        </p>
                      </div>

                      {/* Card 7: Activity & Location */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">7. Activity & Location</span>
                        <p className="font-bold text-slate-900 text-xs mt-0.5">{selectedDetails.activity || 'Mechanical Lifting Operations'}</p>
                        <p className="text-slate-600 flex items-center gap-1 text-[11px]">
                          <MapPin className="w-3 h-3 text-slate-400" />
                          {selectedDetails.location || 'Lifting Zone 03'}
                        </p>
                      </div>

                      {/* Card 8: HSE Validation State */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">8. HSE Validation State</span>
                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-100 text-emerald-800 border border-emerald-300 mt-0.5">
                          {selectedDetails.validation_status || selectedDetails.hse_validation_state || 'HSE_VALIDATED'}
                        </span>
                        <p className="text-slate-500 text-[10px]">Confirmed by Oil India HSE Lead</p>
                      </div>

                      {/* Card 9: Operational Lifecycle */}
                      <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                        <span className="text-[10px] font-bold text-slate-500 tracking-wider block">9. Operational Action Stage</span>
                        <p className="font-bold text-orange-900 text-xs mt-0.5">
                          {selectedDetails.operational_status || selectedDetails.action_state || (typeof selectedDetails.assigned_action === 'object' ? selectedDetails.assigned_action?.operational_status : null) || 'ACTIVE'}
                        </p>
                        <p className="text-slate-600 text-[11px] truncate">
                          Supervisor: {selectedDetails.assigned_supervisor || (typeof selectedDetails.assigned_action === 'object' ? selectedDetails.assigned_action?.supervisor_name : null) || 'SUP-01 (Rajesh Kumar)'}
                        </p>
                      </div>
                    </div>
                  );
                })()}

                {/* 2. SUPPORTING EVENTS TAB */}
                {detailsTab === 'events' && (() => {
                  const evts = selectedDetails?.supporting_events || selectedDetails?.supporting_safety_events || [];

                  return (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                          <Layers className="w-4 h-4 text-purple-600" />
                          <span>Supporting Safety Events ({evts.length})</span>
                        </h3>
                        <span className="text-[10px] text-slate-400">Ground-truth canonical SQLite records</span>
                      </div>

                      {evts.length > 0 ? (
                        <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
                          {evts.map((ev, idx) => (
                            <div key={idx} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 shadow-2xs">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-xs text-slate-900">{ev.event_id || `EVT-${idx + 1}`}</span>
                                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                                    (ev.source || '').toUpperCase() === 'HUMAN' ? 'bg-blue-100 text-blue-800 border border-blue-200' :
                                    (ev.source || '').toUpperCase() === 'CCTV' ? 'bg-purple-100 text-purple-800 border border-purple-200' :
                                    'bg-slate-200 text-slate-800 border border-slate-300'
                                  }`}>
                                    {ev.source || 'HUMAN'}
                                  </span>
                                </div>
                                <span className="text-[10px] text-slate-500 font-mono">
                                  {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'Recent'}
                                </span>
                              </div>
                              <p className="text-slate-800 text-xs font-medium leading-relaxed font-serif">
                                "{ev.narrative || ev.raw_narrative || ev.observed_event || 'No narrative description provided'}"
                              </p>
                              <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-500 pt-1 border-t border-slate-200">
                                <span>Location: <strong className="text-slate-700">{ev.location || 'Lifting Zone 03'}</strong></span>
                                <span>•</span>
                                <span>Hazard: <strong className="text-slate-700">{ev.hazard || ev.energy || 'Gravitational / Kinetic'}</strong></span>
                                <span>•</span>
                                <span>Barrier: <strong className="text-rose-700">{ev.barrier || ev.critical_barrier || 'Exclusion Zone'} ({ev.barrier_condition || ev.barrier_state || 'BYPASSED'})</strong></span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                          <Layers className="w-8 h-8 text-slate-300 mx-auto" />
                          <p className="text-xs font-bold text-slate-700 uppercase">No Supporting Events Linked</p>
                          <p className="text-[11px] text-slate-400">No canonical events are currently linked to this pattern.</p>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* 3. EVIDENCE SNIPPETS / GROUND-TRUTH TAB */}
                {detailsTab === 'snippets' && (() => {
                  const evts = selectedDetails?.supporting_events || selectedDetails?.supporting_safety_events || [];
                  const rawSnippets = selectedDetails?.evidence_snippets || [];
                  const totalEvidence = evts.length > 0 ? evts.length : rawSnippets.length;

                  return (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                          <FileText className="w-4 h-4 text-blue-600" />
                          <span>Grounded Evidence Records ({totalEvidence})</span>
                        </h3>
                        <span className="text-[10px] text-slate-400">Extracted from Human & CCTV Observations</span>
                      </div>

                      {evts.length > 0 ? (
                        <div className="max-h-80 overflow-y-auto space-y-2.5 pr-1">
                          {evts.map((ev, idx) => {
                            const isCctv = (ev.source || '').toUpperCase() === 'CCTV';
                            const spans = (ev.evidence_spans || ev.evidence || []).map(s => (s.text || s.span_text || s.value || '').trim()).filter(Boolean);
                            const evidenceFragment = spans.length > 0 
                              ? spans.join(' • ') 
                              : (ev.barrier_condition || ev.barrier_state ? `${ev.barrier_condition || ev.barrier_state} barrier in ${ev.location || 'restricted zone'}` : 'entered the lifting exclusion zone');

                            return (
                              <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2 shadow-2xs">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono font-bold text-xs text-slate-900">
                                      {ev.event_id || `EVT-${idx + 1}`}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      isCctv ? 'bg-purple-100 text-purple-800 border border-purple-200' : 'bg-blue-100 text-blue-800 border border-blue-200'
                                    }`}>
                                      {isCctv ? 'CCTV' : 'HUMAN'}
                                    </span>
                                  </div>
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Verified'}
                                  </span>
                                </div>

                                <div className="space-y-0.5">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                                    {isCctv ? 'OBSERVATION' : 'NARRATIVE'}
                                  </span>
                                  <p className="text-xs text-slate-900 font-serif leading-relaxed italic bg-white p-2.5 rounded-lg border border-slate-200">
                                    "{ev.narrative || ev.raw_narrative || ev.observed_event || 'Observation recorded during operations'}"
                                  </p>
                                </div>

                                <div className="space-y-0.5">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                                    EVIDENCE
                                  </span>
                                  <div className="p-2 rounded-lg bg-blue-50/70 border border-blue-200 font-mono text-[11px] text-blue-950 font-bold">
                                    "{evidenceFragment}"
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 pt-1 border-t border-slate-200 text-[10px]">
                                  <span className="text-slate-400 font-bold uppercase">SUPPORTS:</span>
                                  <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-bold">
                                    {isCctv ? 'Exposure / Barrier verification' : 'Exposure / Critical Barrier'}
                                  </span>
                                  <span className="text-slate-400">•</span>
                                  <span className="text-slate-600 font-medium truncate">
                                    {ev.barrier || ev.critical_barrier || 'Exclusion Zone'} ({ev.barrier_condition || ev.barrier_state || 'BYPASSED'})
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : rawSnippets.length > 0 ? (
                        <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
                          {rawSnippets.map((snip, sIdx) => (
                            <div key={sIdx} className="p-3 rounded-lg bg-blue-50/60 border border-blue-200 font-mono text-xs text-blue-950">
                              "{snip}"
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                          <FileText className="w-8 h-8 text-slate-300 mx-auto" />
                          <p className="text-xs font-bold text-slate-700 uppercase">NO EVIDENCE AVAILABLE</p>
                          <p className="text-[11px] text-slate-400">No evidence snippets are currently linked to this pattern.</p>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* 4. VERIFICATION HISTORY TIMELINE TAB */}
                {detailsTab === 'history' && (() => {
                  const historyList = selectedDetails?.verification_history || [];

                  return (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                          <History className="w-4 h-4 text-slate-600" />
                          <span>Chronological Verification History ({historyList.length})</span>
                        </h3>
                        <span className="text-[10px] text-slate-400">Audit Trail of Lifecycle Actions</span>
                      </div>

                      {historyList.length > 0 ? (
                        <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
                          {historyList.map((vh, vIdx) => {
                            const status = (vh.status || vh.stage || '').toUpperCase();
                            const isVerified = status.includes('VERIFIED');
                            const isRebreach = status.includes('REBREACH') || status.includes('RE-BREACH') || status.includes('REOPEN') || status.includes('FAILED');
                            const isDispatched = status.includes('DISPATCH');
                            const isInProgress = status.includes('PROGRESS');
                            const isAwaiting = status.includes('AWAIT');
                            const isClose = status.includes('CLOSE');
                            const isValidated = status.includes('VALIDATE');

                            const badgeStyle = isVerified 
                              ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                              : isRebreach
                              ? 'bg-rose-100 text-rose-900 border-rose-300'
                              : isDispatched
                              ? 'bg-orange-100 text-orange-900 border-orange-300'
                              : isInProgress
                              ? 'bg-blue-100 text-blue-900 border-blue-300'
                              : isAwaiting
                              ? 'bg-yellow-100 text-yellow-900 border-yellow-300'
                              : isClose
                              ? 'bg-slate-200 text-slate-800 border-slate-300'
                              : isValidated
                              ? 'bg-purple-100 text-purple-900 border-purple-300'
                              : 'bg-slate-100 text-slate-700 border-slate-300';

                            const detailsText = typeof vh.details === 'object' && vh.details !== null
                              ? (vh.details.message || vh.details.notes || JSON.stringify(vh.details))
                              : (vh.details || vh.title || 'Operational lifecycle event logged');

                            let formattedTime = 'Recent';
                            if (vh.timestamp) {
                              try {
                                const d = new Date(vh.timestamp);
                                formattedTime = !isNaN(d.getTime())
                                  ? `${d.toLocaleDateString([], { day: '2-digit', month: 'short' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                                  : vh.timestamp;
                              } catch {
                                formattedTime = vh.timestamp;
                              }
                            }

                            return (
                              <div key={vIdx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${badgeStyle}`}>
                                      {vh.stage || vh.status || 'EVENT'}
                                    </span>
                                    {vh.actor && (
                                      <span className="text-[11px] font-semibold text-slate-600">
                                        • {vh.actor}
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-[10px] font-mono font-bold text-slate-500">
                                    {formattedTime}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-800 font-medium pl-2 border-l-2 border-slate-300">
                                  {detailsText}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                          <History className="w-8 h-8 text-slate-300 mx-auto" />
                          <p className="text-xs font-bold text-slate-700 uppercase">NO VERIFICATION HISTORY</p>
                          <p className="text-[11px] text-slate-400">No previous verification attempts recorded for this pattern.</p>
                        </div>
                      )}
                    </div>
                  );
                })()}

              </div>
            ) : null}

            {/* Footer */}
            <div className="flex justify-end p-4 border-t border-slate-200 bg-slate-50/50 shrink-0">
              <button
                onClick={() => setDetailsModalOpen(false)}
                className="px-4 py-2 bg-slate-900 hover:bg-black text-white text-xs font-bold rounded-lg transition-colors shadow-sm"
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
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-semibold bg-white text-slate-900 focus:ring-2 focus:ring-orange-500 focus:outline-none"
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
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-semibold text-slate-900 focus:ring-2 focus:ring-orange-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Required Corrective Action</label>
                <textarea
                  rows={2}
                  value={assignForm.required_action}
                  onChange={(e) => setAssignForm(prev => ({ ...prev, required_action: e.target.value }))}
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-medium text-slate-900 focus:ring-2 focus:ring-orange-500 focus:outline-none"
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
                  id="btn-submit-assignment"
                  disabled={assignSubmitting}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {assignSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>{assignSubmitting ? 'Dispatching...' : 'Confirm & Dispatch / DISPATCH TO SUPERVISOR'}</span>
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
                  className="w-full p-2.5 rounded-lg border border-slate-300 font-medium text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
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
                  id="btn-confirm-close-pattern"
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
