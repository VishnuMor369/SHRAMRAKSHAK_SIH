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
  Search
} from 'lucide-react';
import { 
  fetchSafetyMemoryPatterns, 
  validateSafetyMemoryPattern, 
  checkWorkPackage, 
  fetchSafetyMemorySummary 
} from '../../services/api';

export default function SafetyMemoryView() {
  const [patterns, setPatterns] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validatingId, setValidatingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  // Interactive Work Package Precondition Check Form
  const [wpTaskType, setWpTaskType] = useState('Mechanical Lifting');
  const [wpLocation, setWpLocation] = useState('Drilling Rig 04 - Wellhead Area');
  const [wpEvidenceProvided, setWpEvidenceProvided] = useState(['lifting_plan']);
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
    } catch (err) {
      console.error('Failed to load safety memory:', err);
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
      const res = await validateSafetyMemoryPattern(patternId, decision, 'HSE-Lead-01', 'Validated during SIH Demonstration review');
      setFeedbackMsg(`Pattern ${decision === 'CONFIRM' ? 'confirmed as HSE Validated Safety Pattern' : 'rejected'}.`);
      loadData();
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (err) {
      console.error('Validation failed:', err);
    } finally {
      setValidatingId(null);
    }
  };

  const handleToggleEvidence = (key) => {
    setWpEvidenceProvided(prev => 
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const handleRunWpCheck = async () => {
    try {
      setWpChecking(true);
      const res = await checkWorkPackage({
        package_id: 'WP-OIL-2026-LIFT-09',
        task_type: wpTaskType,
        location: wpLocation,
        proposed_controls: ['standard_briefing'],
        evidence_provided: wpEvidenceProvided
      });
      setWpResult(res);
    } catch (err) {
      console.error('Work package check failed:', err);
    } finally {
      setWpChecking(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-purple-100 text-purple-900 border border-purple-200">
              SAFETY MEMORY ARCHITECTURE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Underlying Safety-Control Mechanisms & HSE Governance
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Safety Memory & Future-Work Learning
          </h1>
        </div>

        <div className="text-xs text-slate-500 max-w-sm sm:text-right">
          Tracks <b className="text-slate-800">Independent Occurrences</b> vs <b className="text-slate-500">Duplicates</b>. AI creates <b className="text-amber-700">Candidate Patterns</b>; only HSE confirms <b className="text-emerald-700">Validated Learning</b>.
        </div>
      </div>

      {feedbackMsg && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 font-bold text-xs flex items-center justify-between animate-fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{feedbackMsg}</span>
          </div>
          <button onClick={() => setFeedbackMsg(null)} className="text-emerald-700 hover:text-emerald-900 text-xs">✕</button>
        </div>
      )}

      {/* 2. Top Metric Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total Safety Observations</span>
          <span className="text-2xl font-black text-slate-900 mt-1 block">{summary?.total_events || 6}</span>
          <span className="text-[11px] text-slate-500 mt-1 block">Cross-report ingested</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Independent Occurrences</span>
          <span className="text-2xl font-black text-purple-700 mt-1 block">
            {patterns.reduce((acc, p) => acc + (p.independent_occurrences || 0), 0) || 5}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Distinct underlying events</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Duplicates Filtered</span>
          <span className="text-2xl font-black text-slate-700 mt-1 block">{summary?.duplicate_count ?? 2}</span>
          <span className="text-[11px] text-slate-500 mt-1 block">Does NOT inflate recurrence</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">HSE Validated Patterns</span>
          <span className="text-2xl font-black text-emerald-700 mt-1 block">
            {patterns.filter(p => p.validation_status === 'HSE_VALIDATED').length}
          </span>
          <span className="text-[11px] text-slate-500 mt-1 block">Active future-work controls</span>
        </div>
      </div>

      {/* 3. Recurring Safety-Control Patterns */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-purple-700" />
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900">
              Identified Recurring Control Patterns ({patterns.length})
            </h2>
          </div>
          <button 
            onClick={loadData}
            className="inline-flex items-center space-x-1 text-xs font-bold text-slate-500 hover:text-slate-800"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Memory</span>
          </button>
        </div>

        <div className="space-y-4">
          {patterns.map((p) => {
            const isValidated = p.validation_status === 'HSE_VALIDATED';
            return (
              <div 
                key={p.pattern_id}
                className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition-all ${
                  isValidated ? 'border-emerald-300 ring-1 ring-emerald-200' : 'border-slate-200'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border">
                        {p.pattern_id}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                        isValidated 
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                          : 'bg-amber-100 text-amber-800 border-amber-300'
                      }`}>
                        {isValidated ? '✓ HSE VALIDATED SAFETY PATTERN' : 'CANDIDATE RECURRING PATTERN'}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
                        {p.independent_occurrences} INDEPENDENT OCCURRENCES
                      </span>
                    </div>
                    <h3 className="text-sm font-black text-slate-900 mt-1">
                      {p.pattern_title}
                    </h3>
                  </div>

                  {/* HSE Governance Action Controls */}
                  <div className="flex items-center space-x-2">
                    {!isValidated ? (
                      <button
                        onClick={() => handleValidate(p.pattern_id, 'CONFIRM')}
                        disabled={validatingId === p.pattern_id}
                        className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow transition-colors flex items-center space-x-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>CONFIRM PATTERN</span>
                      </button>
                    ) : (
                      <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        Validated by {p.validated_by || 'HSE Lead'}
                      </span>
                    )}

                    <button
                      onClick={() => handleValidate(p.pattern_id, 'REJECT')}
                      disabled={validatingId === p.pattern_id}
                      className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition-colors"
                    >
                      Reject
                    </button>
                  </div>
                </div>

                {/* Underlying Control Mechanism Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Activity / Hazard</span>
                    <span className="font-bold text-slate-900 mt-1 block">
                      {p.activity} • {p.hazard}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Failed Critical Barrier</span>
                    <span className="font-bold text-red-700 mt-1 block">
                      {p.critical_barrier} ({p.barrier_condition || 'Exclusion zone breached'})
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Deduplication Integrity</span>
                    <span className="font-bold text-slate-800 mt-1 block">
                      {p.independent_occurrences} independent events
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {p.duplicate_count || 0} duplicate reports filtered
                    </span>
                  </div>
                </div>

                {/* Future Work Requirement Banner */}
                {p.future_work_requirements && p.future_work_requirements.length > 0 && (
                  <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-lg space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-amber-900 font-bold text-xs uppercase tracking-wider">
                      <FileCheck className="w-4 h-4 text-amber-700" />
                      <span>Future-Work Precondition Applied:</span>
                    </div>
                    {p.future_work_requirements.map((req, i) => (
                      <div key={i} className="text-xs text-slate-800 pl-5">
                        • <b>{req.title}</b>: {req.description} ({req.evidence_type})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Future Work Package Safety Verification (Section 8: "REQUIRED SAFETY EVIDENCE MISSING") */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <FileCheck className="w-4 h-4 text-blue-600" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Future-Work Safety Intelligence Check (Pre-Job Authorization)
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Test how validated Safety Memory automatically evaluates upcoming work packages for required observable safety evidence before permit authorization.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Work Package Task Type</label>
            <select
              value={wpTaskType}
              onChange={(e) => setWpTaskType(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-300 bg-white text-slate-900 font-semibold"
            >
              <option value="Mechanical Lifting">Mechanical Lifting Operations</option>
              <option value="Electrical Maintenance">Electrical Maintenance (LOTO)</option>
              <option value="Confined Space Entry">Confined Space Entry</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Target Location</label>
            <input
              type="text"
              value={wpLocation}
              onChange={(e) => setWpLocation(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-300 text-slate-900"
            />
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Available Safety Evidence</label>
            <div className="space-y-1.5 pt-1">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={wpEvidenceProvided.includes('lifting_plan')}
                  onChange={() => handleToggleEvidence('lifting_plan')}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <span className="text-slate-800">Approved Lifting Plan</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={wpEvidenceProvided.includes('physical_exclusion_zone_verified')}
                  onChange={() => handleToggleEvidence('physical_exclusion_zone_verified')}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <span className="text-slate-800">Physical Exclusion Zone Verified (CCTV/Visual)</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={wpEvidenceProvided.includes('rigger_competency_certificate')}
                  onChange={() => handleToggleEvidence('rigger_competency_certificate')}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <span className="text-slate-800">Rigger Competency Certification</span>
              </label>
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            onClick={handleRunWpCheck}
            disabled={wpChecking}
            className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs rounded-lg shadow transition-colors flex items-center space-x-1.5"
          >
            {wpChecking ? (
              <span>Evaluating Preconditions...</span>
            ) : (
              <>
                <FileCheck className="w-3.5 h-3.5" />
                <span>Evaluate Work Package Against Memory</span>
              </>
            )}
          </button>
        </div>

        {/* Work Package Result Banner */}
        {wpResult && (
          <div className={`p-4 rounded-xl border animate-fade-in ${
            wpResult.authorized 
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950' 
              : 'bg-red-50 border-red-300 text-red-950'
          }`}>
            <div className="flex items-center justify-between font-bold mb-1">
              <span className="text-xs uppercase tracking-wider flex items-center gap-1.5">
                {wpResult.authorized ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertOctagon className="w-4 h-4 text-red-600" />
                )}
                {wpResult.status === 'MISSING_EVIDENCE' 
                  ? 'REQUIRED SAFETY EVIDENCE MISSING' 
                  : 'ALL REQUIRED SAFETY PRECONDITIONS SATISFIED'}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/80 border">
                STATUS: {wpResult.status}
              </span>
            </div>

            <p className="text-xs leading-snug mt-1">
              {wpResult.authorized 
                ? 'All historical preconditions from validated recurring patterns have been satisfied with appropriate evidence.'
                : 'Work package cannot proceed automatically. Human authorization review and physical exclusion zone verification are required.'}
            </p>

            {wpResult.missing_requirements && wpResult.missing_requirements.length > 0 && (
              <div className="mt-2.5 pt-2 border-t border-red-200 text-xs">
                <span className="font-bold text-red-900 block mb-1">Missing Safety Preconditions:</span>
                <ul className="list-disc list-inside space-y-0.5 text-red-800">
                  {wpResult.missing_requirements.map((miss, idx) => (
                    <li key={idx}>
                      <b>{miss.requirement_title}</b>: {miss.evidence_type} ({miss.reason})
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
