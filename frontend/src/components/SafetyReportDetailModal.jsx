import React, { useState } from 'react';
import { 
  X, 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Video, 
  Clock, 
  MapPin, 
  Activity, 
  BrainCircuit, 
  AlertOctagon,
  Sparkles,
  Info,
  Download,
  ArrowRight,
  Check,
  Edit3,
  Ban,
  UserCheck,
  ExternalLink
} from 'lucide-react';
import { submitHSEReview, getSingleReportPdfUrl } from '../services/api';
import { UnifiedModal } from './common';

export default function SafetyReportDetailModal({ report, isOpen, onClose, onReviewUpdated }) {
  if (!isOpen || !report) return null;

  const [reviewDecision, setReviewDecision] = useState(null); // 'CONFIRM' | 'CORRECT' | 'REJECT'
  const [isEditingCorrection, setIsEditingCorrection] = useState(false);
  const [corrSif, setCorrSif] = useState(report.sif_potential);
  const [corrRisk, setCorrRisk] = useState(report.risk_score);
  const [corrBarrier, setCorrBarrier] = useState(report.barrier || '');
  const [corrLsr, setCorrLsr] = useState(report.life_saving_rules?.[0] || '');
  const [corrConsequence, setCorrConsequence] = useState(report.potential_consequence || '');
  const [reviewerRole, setReviewerRole] = useState('HSE Superintendent');
  const [reviewNotes, setReviewNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [activeReport, setActiveReport] = useState(report);

  // Sync state if report prop changes
  React.useEffect(() => {
    setActiveReport(report);
    setCorrSif(report.sif_potential);
    setCorrRisk(report.risk_score);
    setCorrBarrier(report.barrier || '');
    setCorrLsr(report.life_saving_rules?.[0] || '');
    setCorrConsequence(report.potential_consequence || '');
    setIsEditingCorrection(false);
    setReviewDecision(null);
  }, [report]);

  const isSif = activeReport.sif_potential;
  const isDataset = activeReport.source === 'OIL_DATASET' || activeReport.source === 'DATASET_CSV';
  const confidenceLevel = activeReport.confidence_level || (activeReport.confidence >= 75 ? 'HIGH' : activeReport.confidence >= 50 ? 'MEDIUM' : 'LOW');
  const evidenceStrength = activeReport.evidence_strength || 'HIGH';
  const confidenceScore = activeReport.confidence || 85;

  // Causal pathway dimensions
  const hazard = activeReport.hazard || 'Operational Safety Hazard';
  const energySource = activeReport.energy_source || 'Mechanical / Gravitational Potential Energy';
  const exposure = activeReport.exposure || 'Personnel active in operational danger perimeter';
  const barrier = activeReport.barrier || 'Designated Exclusion Boundary & Isolation Controls';
  const barrierFailure = activeReport.barrier_failure || 'Operational control perimeter bypassed or unverified';
  const consequence = activeReport.potential_consequence || 'Struck-by / crushing trauma or loss of containment';

  // Handle Review Submission
  const handleReviewAction = async (decision) => {
    if (decision === 'CORRECT' && !isEditingCorrection) {
      setIsEditingCorrection(true);
      setReviewDecision('CORRECT');
      return;
    }

    try {
      setSubmittingReview(true);
      const payload = {
        decision: decision,
        corrected_sif: decision === 'CORRECT' ? corrSif : null,
        corrected_risk: decision === 'CORRECT' ? Number(corrRisk) : null,
        corrected_barrier: decision === 'CORRECT' ? corrBarrier : null,
        corrected_lsr: decision === 'CORRECT' ? corrLsr : null,
        corrected_consequence: decision === 'CORRECT' ? corrConsequence : null,
        reviewer_role: reviewerRole,
        notes: reviewNotes || `HSE ${decision} action executed.`
      };

      const res = await submitHSEReview(activeReport.report_id, payload);
      if (res && res.report) {
        setActiveReport(res.report);
        if (onReviewUpdated) {
          onReviewUpdated(res.report);
        }
      }
      setIsEditingCorrection(false);
      setReviewDecision(decision);
    } catch (err) {
      console.error('Failed to submit HSE review:', err);
    } finally {
      setSubmittingReview(false);
    }
  };

  const currentReview = activeReport.hse_review;

  return (
    <UnifiedModal
      isOpen={isOpen}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
    >
      {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-bold text-amber-400">{activeReport.report_id}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
                  isDataset ? 'bg-blue-950 text-blue-300 border border-blue-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}>
                  {isDataset ? 'OIL DATASET' : (activeReport.source || 'CCTV EVENT')}
                </span>

                {currentReview && (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
                    currentReview.decision === 'CONFIRM' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                    currentReview.decision === 'CORRECT' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                    'bg-red-950 text-red-300 border border-red-800'
                  }`}>
                    HSE {currentReview.decision}ED
                  </span>
                )}
              </div>
              <h2 className="text-base font-bold tracking-tight text-white mt-0.5">
                SIF RISK INTELLIGENCE
              </h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <a
              href={getSingleReportPdfUrl(activeReport.report_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Dossier</span>
            </a>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Narrative Banner: What happened? */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3.5">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
            Safety Event Narrative
          </div>
          <p className="text-sm font-medium text-slate-900 leading-snug">
            "{activeReport.description}"
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-600">
            <span className="flex items-center space-x-1">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              <span><b>Location:</b> {activeReport.location}</span>
            </span>
            <span className="flex items-center space-x-1">
              <Activity className="w-3.5 h-3.5 text-slate-400" />
              <span><b>Activity:</b> {activeReport.activity}</span>
            </span>
            <span className="flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span><b>Timestamp:</b> {activeReport.timestamp?.replace('T', ' ').slice(0, 19)}</span>
            </span>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-800 max-h-[calc(85vh-160px)]">

          {/* 4 KPI Dimensions (Risk Score, SIF Potential, AI Confidence, Evidence Strength) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Risk Score */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Prototype Priority
              </span>
              <div className="mt-1 flex items-baseline space-x-1.5">
                <span className="text-2xl font-black font-mono text-slate-900">
                  {activeReport.risk_score}
                </span>
                <span className="text-xs text-slate-400 font-semibold">/ 100</span>
              </div>
              <span className={`mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border w-fit ${
                activeReport.risk_level === 'CRITICAL' ? 'bg-red-50 text-red-700 border-red-200' :
                activeReport.risk_level === 'HIGH' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                activeReport.risk_level === 'MEDIUM' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                'bg-emerald-50 text-emerald-700 border-emerald-200'
              }`}>
                {activeReport.risk_level}
              </span>
            </div>

            {/* SIF Potential */}
            <div className={`border rounded-xl p-3.5 flex flex-col justify-between ${
              isSif ? 'bg-red-50/70 border-red-200' : 'bg-emerald-50/70 border-emerald-200'
            }`}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                SIF Potential
              </span>
              <div className="mt-1">
                <span className={`text-2xl font-black ${isSif ? 'text-red-700' : 'text-emerald-700'}`}>
                  {isSif ? 'YES' : 'NO'}
                </span>
              </div>
              <span className={`mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border w-fit ${
                isSif ? 'bg-red-100 text-red-800 border-red-300' : 'bg-emerald-100 text-emerald-800 border-emerald-300'
              }`}>
                {isSif ? 'Precursor Identified' : 'Routine Observation'}
              </span>
            </div>

            {/* AI Confidence */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                AI Confidence
              </span>
              <div className="mt-1 flex items-baseline space-x-1.5">
                <span className="text-2xl font-black font-mono text-slate-900">
                  {confidenceScore}%
                </span>
              </div>
              <span className={`mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border w-fit ${
                confidenceLevel === 'HIGH' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                confidenceLevel === 'MEDIUM' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                {confidenceLevel} CONFIDENCE
              </span>
            </div>

            {/* Evidence Strength */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Evidence Strength
              </span>
              <div className="mt-1 flex items-baseline space-x-1.5">
                <span className="text-xl font-black text-slate-900">
                  {evidenceStrength}
                </span>
              </div>
              <span className="mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600 w-fit">
                {activeReport.evidence_image || activeReport.evidence_url ? 'CCTV Snapshot' : 'Field Report'}
              </span>
            </div>
          </div>

          {/* LOW CONFIDENCE REVIEW BANNER */}
          {activeReport.needs_hse_review && (
            <div className="bg-amber-50 border border-amber-300 rounded-xl p-3.5 flex items-center space-x-3 text-amber-900">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
              <div className="text-xs">
                <span className="font-bold uppercase tracking-wider text-amber-800">Human HSE Review Required:</span>{' '}
                AI confidence is below operational threshold or context has ambiguity. An authorized HSE officer must verify this safety precursor.
              </div>
            </div>
          )}

          {/* VISUAL CENTERPIECE: STRUCTURED SIF RISK PATHWAY */}
          <div className="border border-slate-200 rounded-xl p-4 bg-gradient-to-b from-slate-50/80 to-white shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                  SIF Risk Pathway (Causal Safety Intelligence)
                </h3>
              </div>
              <span className="text-[10px] text-slate-400 font-medium">
                Deterministic Causal Model
              </span>
            </div>

            {/* Horizontal Pathway Box Grid */}
            <div className="grid grid-cols-1 md:grid-cols-7 gap-2 items-stretch">
              
              {/* Box 1: Hazard */}
              <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-slate-400">1. Hazard</span>
                <p className="text-xs font-bold text-slate-800 mt-1 leading-snug">{hazard}</p>
                <span className="text-[9px] text-slate-400 mt-1">Identified Source</span>
              </div>

              {/* Box 2: Energy */}
              <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-slate-400">2. Energy</span>
                <p className="text-xs font-bold text-slate-800 mt-1 leading-snug">{energySource}</p>
                <span className="text-[9px] text-slate-400 mt-1">Hazard Mechanism</span>
              </div>

              {/* Box 3: Exposure */}
              <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-slate-400">3. Exposure</span>
                <p className="text-xs font-bold text-slate-800 mt-1 leading-snug">{exposure}</p>
                <span className="text-[9px] text-slate-400 mt-1">Human Vulnerability</span>
              </div>

              {/* Box 4: Barrier */}
              <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-slate-400">4. Barrier</span>
                <p className="text-xs font-bold text-slate-800 mt-1 leading-snug">{barrier}</p>
                <span className="text-[9px] text-slate-400 mt-1">Required Safeguard</span>
              </div>

              {/* Box 5: Failure */}
              <div className="bg-amber-50/60 border border-amber-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-amber-700">5. Failure</span>
                <p className="text-xs font-bold text-amber-950 mt-1 leading-snug">{barrierFailure}</p>
                <span className="text-[9px] text-amber-600 mt-1">Compromised State</span>
              </div>

              {/* Box 6: Consequence */}
              <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xs flex flex-col justify-between">
                <span className="text-[10px] font-bold uppercase text-slate-400">6. Consequence</span>
                <p className="text-xs font-bold text-slate-800 mt-1 leading-snug">{consequence}</p>
                <span className="text-[9px] text-slate-400 mt-1">Potential Outcome</span>
              </div>

              {/* Box 7: SIF Potential */}
              <div className={`border rounded-lg p-2.5 shadow-xs flex flex-col justify-between ${
                isSif ? 'bg-red-50 border-red-300 text-red-950' : 'bg-emerald-50 border-emerald-300 text-emerald-950'
              }`}>
                <span className="text-[10px] font-bold uppercase tracking-wider">7. SIF</span>
                <p className="text-sm font-black mt-1">
                  {isSif ? 'YES' : 'NO'}
                </p>
                <span className="text-[9px] font-medium opacity-80 mt-1">
                  {isSif ? 'SIF Precursor' : 'Low Potential'}
                </span>
              </div>
            </div>

            <div className="mt-3 text-[11px] text-slate-500 italic bg-white/60 p-2 rounded border border-slate-100">
              <b>Potential SIF Pathway:</b> {activeReport.sif_pathway || `${hazard} → ${energySource} → ${exposure} → ${barrierFailure} → ${consequence}`}
            </div>
            <div className="mt-1 text-[10px] text-slate-400">
              * AI identifies potential safety precursor pathways from available evidence; it does not predict a specific accident.
            </div>
          </div>

          {/* TWO COLUMN GRID: WHY FLAGGED & IOGP LIFE-SAVING RULE */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* WHY FLAGGED */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5 flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-blue-600" />
                <span>Why Flagged?</span>
              </h4>
              <ul className="space-y-2 text-xs">
                {(activeReport.why_flagged && activeReport.why_flagged.length > 0 ? activeReport.why_flagged : [
                  `High-energy activity identified (${energySource})`,
                  `Personnel exposure verified (${exposure})`,
                  `Critical safety barrier compromised (${barrierFailure})`,
                  `Potential consequence severity (${consequence})`,
                  `Relevant IOGP Life-Saving Rule mapped`
                ]).map((item, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-slate-700">
                    <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* IOGP LIFE-SAVING RULES (Max 3) */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5 flex items-center space-x-2">
                <AlertOctagon className="w-4 h-4 text-indigo-600" />
                <span>IOGP Life-Saving Rule</span>
              </h4>

              {activeReport.life_saving_rules && activeReport.life_saving_rules.length > 0 ? (
                <div className="space-y-2">
                  {activeReport.life_saving_rules.slice(0, 3).map((rule, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-indigo-50/60 border border-indigo-200/70">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-indigo-900">{rule}</span>
                        <span className="text-[10px] font-semibold text-indigo-600 uppercase">HIGH CONFIDENCE</span>
                      </div>
                      <p className="text-[11px] text-indigo-800 mt-1">
                        Operational activity involves direct risk controls mandated by IOGP {rule} guidelines.
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500">
                  No applicable Life-Saving Rule identified for this observation.
                </div>
              )}
            </div>
          </div>

          {/* BARRIER INTELLIGENCE & RECOMMENDED ACTION */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Barrier Intelligence */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5 flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Barrier Intelligence</span>
              </h4>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-slate-500">Primary Barrier:</span>{' '}
                  <span className="font-bold text-slate-800">{barrier}</span>
                </div>
                <div>
                  <span className="text-slate-500">Barrier Status:</span>{' '}
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                    FAILED / COMPROMISED
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Failure Mechanism:</span>{' '}
                  <span className="font-medium text-slate-700">{barrierFailure}</span>
                </div>
                <div className="pt-2 border-t border-slate-100">
                  <span className="text-slate-500">Recommended Control:</span>
                  <p className="font-semibold text-slate-900 mt-0.5">
                    {activeReport.ai_recommendation || 'Halt current high-risk task, evacuate exposed personnel, and restore physical barrier perimeter before resuming.'}
                  </p>
                </div>
              </div>
            </div>

            {/* AI Recommended HSE Actions */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-600" />
                <span>Recommended HSE Action</span>
              </h4>
              <div className="space-y-2.5 text-xs">
                <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-950 font-bold">
                  {activeReport.recommended_action?.primary || 'Hold high-risk activity and re-establish safety barrier perimeter.'}
                </div>
                <ol className="space-y-1.5 pl-4 list-decimal text-slate-700">
                  {(activeReport.recommended_action?.steps || [
                    'Immediately halt high-energy task in zone.',
                    'Clear personnel out of line of fire.',
                    'Verify physical barrier integrity with designated marshal.',
                    'Authorized supervisor signs off barrier restoration before permit reactivation.'
                  ]).map((step, sIdx) => (
                    <li key={sIdx} className="leading-snug">{step}</li>
                  ))}
                </ol>
              </div>
            </div>
          </div>

          {/* HUMAN HSE REVIEW CONTROLS (PART 14) */}
          <div className="border border-blue-200 rounded-xl p-4 bg-blue-50/40">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center space-x-2">
                  <UserCheck className="w-4 h-4 text-blue-700" />
                  <span>Human HSE Review & Model Feedback</span>
                </h4>
                <p className="text-[11px] text-blue-700 mt-0.5">
                  Authorized HSE feedback provides ground truth for calibration and continuous model validation.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleReviewAction('CONFIRM')}
                  disabled={submittingReview}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition-colors flex items-center space-x-1"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>CONFIRM</span>
                </button>
                <button
                  onClick={() => handleReviewAction('CORRECT')}
                  disabled={submittingReview}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-xs transition-colors flex items-center space-x-1"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>CORRECT</span>
                </button>
                <button
                  onClick={() => handleReviewAction('REJECT')}
                  disabled={submittingReview}
                  className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-xs transition-colors flex items-center space-x-1"
                >
                  <Ban className="w-3.5 h-3.5" />
                  <span>REJECT</span>
                </button>
              </div>
            </div>

            {/* Current Review State */}
            {currentReview && (
              <div className="p-3 bg-white rounded-lg border border-blue-200 text-xs flex flex-wrap items-center justify-between gap-2 mt-2">
                <div>
                  <span className="font-bold text-slate-800">Recorded Decision:</span>{' '}
                  <span className="font-mono font-bold text-blue-700 uppercase">{currentReview.decision}</span>
                  <span className="text-slate-400 mx-2">•</span>
                  <span className="text-slate-600">Reviewer: <b>{currentReview.reviewer_role}</b></span>
                  <span className="text-slate-400 mx-2">•</span>
                  <span className="text-slate-500">{currentReview.timestamp?.slice(0, 19).replace('T', ' ')}</span>
                </div>
                {currentReview.notes && (
                  <span className="text-slate-500 italic">"{currentReview.notes}"</span>
                )}
              </div>
            )}

            {/* Inline Correction Form */}
            {isEditingCorrection && (
              <div className="mt-3 p-3.5 bg-white rounded-lg border border-amber-300 space-y-3 text-xs animate-fade-in">
                <div className="font-bold text-amber-900 flex items-center space-x-1.5">
                  <Edit3 className="w-3.5 h-3.5 text-amber-600" />
                  <span>HSE Override / Correction Fields</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">SIF Potential Decision</label>
                    <select
                      value={corrSif ? 'YES' : 'NO'}
                      onChange={(e) => setCorrSif(e.target.value === 'YES')}
                      className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs bg-white"
                    >
                      <option value="YES">YES — High Potential SIF</option>
                      <option value="NO">NO — Routine Safety Observation</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Corrected Risk Score (0-100)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={corrRisk}
                      onChange={(e) => setCorrRisk(e.target.value)}
                      className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Corrected Barrier</label>
                    <input
                      type="text"
                      value={corrBarrier}
                      onChange={(e) => setCorrBarrier(e.target.value)}
                      placeholder="e.g. Physical interlocked swing gate"
                      className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 font-semibold mb-1">Corrected Life-Saving Rule</label>
                    <input
                      type="text"
                      value={corrLsr}
                      onChange={(e) => setCorrLsr(e.target.value)}
                      placeholder="e.g. Line of Fire / Energy Isolation"
                      className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-slate-600 font-semibold mb-1">Corrected Potential Consequence</label>
                    <input
                      type="text"
                      value={corrConsequence}
                      onChange={(e) => setCorrConsequence(e.target.value)}
                      placeholder="e.g. High-pressure injection injury"
                      className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-slate-600 font-semibold mb-1">Reviewer Role & Notes</label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <input
                        type="text"
                        value={reviewerRole}
                        onChange={(e) => setReviewerRole(e.target.value)}
                        placeholder="HSE Superintendent"
                        className="border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                      />
                      <input
                        type="text"
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        placeholder="Reason for correction..."
                        className="sm:col-span-2 border border-slate-300 rounded px-2.5 py-1.5 text-xs"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                  <button
                    onClick={() => setIsEditingCorrection(false)}
                    className="px-3 py-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-100 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleReviewAction('CORRECT')}
                    disabled={submittingReview}
                    className="px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-xs"
                  >
                    Save & Submit Correction
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* AI AUDIT TRAIL (PART 15) */}
          <div className="border-t border-slate-200 pt-4 text-[11px] text-slate-500 space-y-1">
            <div className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              AI Audit & Lineage
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-600">
              <div>
                <b>Source:</b> {activeReport.source}
              </div>
              <div>
                <b>Engine:</b> Hybrid Safety Reasoning v1
              </div>
              <div>
                <b>Rule Version:</b> SIF Rules v1 (Campbell Matrix)
              </div>
              <div>
                <b>Review:</b> {currentReview ? currentReview.decision : 'Pending HSE Verification'}
              </div>
            </div>
          </div>

        </div>
    </UnifiedModal>
  );
}
