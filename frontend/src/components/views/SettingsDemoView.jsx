import React, { useState } from 'react';
import { 
  Play, 
  RotateCcw, 
  CheckCircle2, 
  ShieldAlert, 
  Database, 
  Video, 
  Smartphone, 
  FileCheck, 
  Layers, 
  AlertTriangle,
  Info,
  ExternalLink
} from 'lucide-react';
import { 
  executeDemoPhase, 
  resetEnterpriseDemo, 
  analyzeRawText,
  fetchDemoStatus,
  resetDemoWorkspace,
  loadDemoData,
  submitDemoHumanReport,
  triggerDemoCctvEvent,
  validateDemoPattern,
  assignDemoAction,
  completeDemoAction,
  verifyDemoAction
} from '../../services/api';

export default function SettingsDemoView({ onNavigate }) {
  const [currentPhase, setCurrentPhase] = useState(1);
  const [runningPhase, setRunningPhase] = useState(null);
  const [phaseResult, setPhaseResult] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [demoStatus, setDemoStatus] = useState(null);
  const [demoReportText, setDemoReportText] = useState('Worker entered the crane lifting exclusion zone while a suspended load was being moved.');
  const [demoStepLoading, setDemoStepLoading] = useState(false);

  const loadDemoSummary = () => {
    fetchDemoStatus()
      .then(data => setDemoStatus(data))
      .catch(err => console.error('Failed to load demo status:', err));
  };

  React.useEffect(() => {
    loadDemoSummary();
  }, []);

  const handleResetDemoSession = async () => {
    try {
      setResetting(true);
      const res = await resetDemoWorkspace();
      setDemoStatus(res.summary);
      setFeedback('Demo Workspace cleanly reset to 0 events, 0 patterns, 0 actions, 0 verifications.');
    } catch (err) {
      setFeedback(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  const handleLoadRepresentativeData = async () => {
    try {
      setDemoStepLoading(true);
      const res = await loadDemoData();
      setDemoStatus(res.summary);
      setFeedback('Representative demo data loaded (4 human reports + 1 CCTV event through canonical pipeline).');
    } catch (err) {
      setFeedback(`Load demo data failed: ${err.message}`);
    } finally {
      setDemoStepLoading(false);
    }
  };

  const handleSubmitHumanReport = async (text) => {
    const t = text || demoReportText;
    if (!t) return;
    try {
      setDemoStepLoading(true);
      const res = await submitDemoHumanReport(t);
      setDemoStatus(res.summary);
      setFeedback(`Added human report! Total events: ${res.summary.total_events}, patterns: ${res.summary.pattern_count}`);
    } catch (err) {
      setFeedback(`Human report failed: ${err.message}`);
    } finally {
      setDemoStepLoading(false);
    }
  };

  const handleTriggerCctv = async () => {
    try {
      setDemoStepLoading(true);
      const res = await triggerDemoCctvEvent('CAM-RIG-01', 'Temporary Lifting Exclusion Zone');
      setDemoStatus(res.summary);
      setFeedback(`Added CCTV machine observation! Linked to pattern. Total events: ${res.summary.total_events}`);
    } catch (err) {
      setFeedback(`CCTV trigger failed: ${err.message}`);
    } finally {
      setDemoStepLoading(false);
    }
  };

  const handleValidateTopPattern = async (action = 'CONFIRM') => {
    const topPat = demoStatus?.patterns?.[0];
    if (!topPat) {
      setFeedback('No candidate pattern to validate. Submit reports first.');
      return;
    }
    try {
      setDemoStepLoading(true);
      const res = await validateDemoPattern(topPat.pattern_id, action, 'HSE_MANAGER_OIL', 'Confirmed recurring failure of lifting exclusion zone boundary.');
      loadDemoSummary();
      setFeedback(`HSE ${action} recorded! Status is now: ${res.status}`);
    } catch (err) {
      setFeedback(`Validation failed: ${err.message}`);
    } finally {
      setDemoStepLoading(false);
    }
  };

  // Interactive Live NLP Assertion Lab (Phase 8)
  const [nlpText, setNlpText] = useState('Worker entered lifting exclusion zone while 15T pipe was suspended.');
  const [isNlpAnalyzing, setIsNlpAnalyzing] = useState(false);
  const [nlpResult, setNlpResult] = useState(null);

  const handleRunNlpAnalysis = async (textToAnalyze) => {
    const t = textToAnalyze || nlpText;
    if (!t.trim()) return;
    try {
      setIsNlpAnalyzing(true);
      const res = await analyzeRawText(t);
      setNlpResult(res);
    } catch (err) {
      console.error('NLP Analysis failed:', err);
    } finally {
      setIsNlpAnalyzing(false);
    }
  };

  const demoPhases = [
    {
      num: 1,
      title: 'Phase 1 — Historical Safety Intelligence',
      targetTab: 'SAFETY INTELLIGENCE',
      description: 'Ingest and parse historical OIL safety reports. NLP extracts SIF precursors, asserting facts and filtering negations.',
      narration: '“SHRAMRAKSHAK does not stop at reading a safety report. First, it understands what actually happened while distinguishing facts from hypothetical or negated statements.”'
    },
    {
      num: 2,
      title: 'Phase 2 — HSE Validation & Learning',
      targetTab: 'SAFETY MEMORY',
      description: 'Identify candidate recurring pattern (Lifting exclusion zone breach, 5 independent occurrences) and confirm with HSE governance.',
      narration: '“Then it remembers. Across multiple reports, it identifies independent occurrences of the same underlying safety-control failure. HSE validates that learning.”'
    },
    {
      num: 3,
      title: 'Phase 3 — Live CCTV Zone Breach',
      targetTab: 'LIVE SAFETY',
      description: 'Simulate or detect a person stepping into the defined lifting exclusion zone on Camera C-01 with 5-frame confirmation.',
      narration: '“Now we move to a live safety event. The camera observes a person entering a lifting exclusion zone.”'
    },
    {
      num: 4,
      title: 'Phase 4 — Machine-Generated Safety Observation',
      targetTab: 'LIVE SAFETY',
      description: 'Convert CCTV breach into a Machine-Generated Safety Observation (Camera C03, Lifting Zone 03) and route directly into SIF intelligence.',
      narration: '“Instead of treating CCTV as a separate computer-vision system, SHRAMRAKSHAK converts that event into a machine-generated safety observation.”'
    },
    {
      num: 5,
      title: 'Phase 5 — SIF Intelligence Analysis',
      targetTab: 'SAFETY INTELLIGENCE',
      description: 'Common SIF engine assesses the CCTV observation: SIF Potential HIGH, Barrier Violated, Line of Fire Life-Saving Rule.',
      narration: '“That observation enters the same SIF intelligence pipeline. The system identifies high SIF potential and the relevant safety controls.”'
    },
    {
      num: 6,
      title: 'Phase 6 — Operational Mobile Alert',
      targetTab: 'ACTIONS / VERIFICATION',
      description: 'Dispatch immediate clean 2-second alert to field supervisor mobile app: "Worker entered lifting exclusion zone. Action Now: Stop lifting."',
      narration: '“The supervisor receives the alert and takes action.”'
    },
    {
      num: 7,
      title: 'Phase 7 — Action Execution',
      targetTab: 'ACTIONS / VERIFICATION',
      description: 'Supervisor acknowledges and marks action taken on site. Backend transitions state to AWAITING VERIFICATION.',
      narration: '“The supervisor executes the corrective intervention on site. But action completion is not treated as proof.”'
    },
    {
      num: 8,
      title: 'Phase 8 — CCTV Verification & Re-Breach Check',
      targetTab: 'ACTIONS / VERIFICATION',
      description: 'CCTV checks physical condition: If zone is clear -> VERIFIED. If re-breach detected -> FAILED and action REOPENED.',
      narration: '“Where the condition is objectively observable, CCTV verifies whether the unsafe condition has actually been removed.”'
    },
    {
      num: 9,
      title: 'Phase 9 — Safety Memory Updated (Learning)',
      targetTab: 'SAFETY MEMORY',
      description: 'The verified event is committed to Safety Memory, updating occurrences from 5 to 6 independent events (duplicates filtered).',
      narration: '“The new event then becomes part of the organization’s safety memory. It learns from them, carries that learning forward, and checks whether the intervention actually worked.”'
    }
  ];

  const handleRunPhase = async (phaseNum, targetTab) => {
    try {
      setRunningPhase(phaseNum);
      const res = await executeDemoPhase(phaseNum);
      setCurrentPhase(phaseNum);
      setPhaseResult(res);
      setFeedback(`Phase ${phaseNum} executed successfully: ${res.message || res.title}`);
      if (targetTab) {
        setTimeout(() => onNavigate(targetTab), 600);
      }
    } catch (err) {
      setFeedback(`Error executing Phase ${phaseNum}: ${err.message}`);
    } finally {
      setRunningPhase(null);
    }
  };

  const handleReset = async () => {
    try {
      setResetting(true);
      await resetEnterpriseDemo();
      setCurrentPhase(1);
      setPhaseResult(null);
      setFeedback('Enterprise demo reset to clean baseline (5 independent occurrences, active alerts cleared).');
    } catch (err) {
      setFeedback(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              DEMO STORYBOARD
            </span>
            <span className="text-xs font-semibold text-slate-500">
              SIH 2026 Executive Presentation Orchestrator
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Demonstration Mode & Storyboard Controls
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleLoadRepresentativeData}
            disabled={demoStepLoading}
            className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold text-xs rounded-lg shadow-sm transition-all"
          >
            {demoStepLoading ? 'Loading...' : 'LOAD DEMO DATA'}
          </button>
          <button
            onClick={handleResetDemoSession}
            disabled={resetting}
            className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow-sm transition-all flex items-center space-x-1"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
            <span>RESET DEMO</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div className="p-3.5 rounded-xl bg-purple-50 border border-purple-300 text-purple-900 font-bold text-xs flex items-center justify-between animate-fade-in">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="text-purple-700 text-xs">✕</button>
        </div>
      )}

      {/* 2. Isolated Clean Demonstration Workspace Card (Sections 10–20) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500/20 text-amber-900 border border-amber-500/30">
                JUDGE EVALUATION WORKSPACE
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {demoStatus?.is_clean_start ? 'CLEAN START ACTIVE (0/0)' : 'LIVE DEMO SESSION'}
              </span>
            </div>
            <h2 className="text-sm font-black text-slate-900 tracking-tight mt-1">
              Live Judge Demonstration Flow (Human Reports → Pattern Discovery → CCTV Link → HSE Validation)
            </h2>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-800 font-bold">
              Events: <strong className="text-slate-950">{demoStatus?.total_events || 0}</strong>
            </span>
            <span className="px-2.5 py-1 rounded bg-red-50 text-red-700 font-bold border border-red-200">
              SIF: {demoStatus?.sif_potential_count || 0}
            </span>
            <span className="px-2.5 py-1 rounded bg-purple-50 text-purple-700 font-bold border border-purple-200">
              Patterns: {demoStatus?.pattern_count || 0}
            </span>
          </div>
        </div>

        {/* Narrative Input & Preset Buttons */}
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
            Step 1–4: Enter Differently Worded Human Reports to Discover Pattern:
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={demoReportText}
              onChange={(e) => setDemoReportText(e.target.value)}
              placeholder="Enter human safety report narrative..."
              className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-amber-500 outline-none font-sans"
            />
            <button
              onClick={() => handleSubmitHumanReport(demoReportText)}
              disabled={demoStepLoading}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-amber-400 font-extrabold text-xs rounded-lg shadow-sm whitespace-nowrap"
            >
              Submit Report
            </button>
          </div>

          {/* Quick presets from Section 13 */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
            <span className="text-slate-400 font-bold mr-1">4 Differently Worded Reports:</span>
            {[
              { id: 1, text: 'Worker entered the crane lifting exclusion zone while a suspended load was being moved.' },
              { id: 2, text: 'During lifting, a contractor crossed the barricaded area beneath the suspended load.' },
              { id: 3, text: 'Personnel were observed inside the drop zone during an active crane operation.' },
              { id: 4, text: 'A worker bypassed the temporary lifting barrier and entered the restricted area.' }
            ].map(p => (
              <button
                key={p.id}
                onClick={() => {
                  setDemoReportText(p.text);
                  handleSubmitHumanReport(p.text);
                }}
                disabled={demoStepLoading}
                className="px-2 py-1 rounded bg-slate-100 hover:bg-amber-100 hover:border-amber-300 border border-slate-200 text-slate-700 text-[10px] font-semibold transition-all"
              >
                + Report {p.id}
              </button>
            ))}
          </div>
        </div>

        {/* Subsequent Steps: CCTV & HSE Validation */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleTriggerCctv}
              disabled={demoStepLoading}
              className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-lg shadow-sm flex items-center space-x-1.5 transition-all"
            >
              <Video className="w-3.5 h-3.5" />
              <span>Step 5: + Add 1 CCTV Occurrence</span>
            </button>

            <button
              onClick={() => handleValidateTopPattern('CONFIRM')}
              disabled={demoStepLoading || (demoStatus?.pattern_count || 0) === 0}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg shadow-sm flex items-center space-x-1.5 transition-all disabled:opacity-40"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Step 6: HSE Validate Pattern</span>
            </button>

            <button
              onClick={() => onNavigate && onNavigate('SAFETY MEMORY')}
              className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-lg shadow-sm flex items-center space-x-1.5 transition-all"
            >
              <span>View In Safety Memory →</span>
            </button>
          </div>

          <div className="text-[11px] text-slate-500 italic">
            Representative demonstration observations — not actual OIL incident records.
          </div>
        </div>
      </div>

      {/* 3. Synthetic Dataset Notice */}
      <div className="p-4 bg-amber-50/80 border border-amber-300 rounded-xl text-xs space-y-1 text-amber-950">
        <div className="flex items-center space-x-2 font-bold uppercase tracking-wider text-[11px] text-amber-900">
          <Info className="w-4 h-4 text-amber-700" />
          <span>Notice on Demonstration Dataset & OIL India Alignment</span>
        </div>
        <p className="text-slate-700 leading-relaxed">
          Because real OIL operational safety records contain sensitive operational data, this system utilizes a <b>clearly marked realistic synthetic demonstration dataset</b> structured in accordance with OIL's Unsafe-Act / Unsafe-Condition guidelines, IOGP Life-Saving Rules, and industrial incident taxonomies.
        </p>
      </div>

      {/* 3. 9-Phase Sequential Storyboard */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
            9-Phase Evaluation Storyboard
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            Active Phase: Step {currentPhase} of 9
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {demoPhases.map((phase) => {
            const isCurrent = currentPhase === phase.num;
            const isDone = currentPhase > phase.num;

            return (
              <div 
                key={phase.num}
                className={`bg-white rounded-xl border p-4 shadow-sm space-y-3 flex flex-col justify-between transition-all ${
                  isCurrent 
                    ? 'border-purple-500 ring-2 ring-purple-200' 
                    : isDone
                    ? 'border-emerald-300 bg-slate-50/50'
                    : 'border-slate-200'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                      isCurrent 
                        ? 'bg-purple-600 text-white' 
                        : isDone
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      PHASE {phase.num}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      → {phase.targetTab}
                    </span>
                  </div>

                  <h3 className="text-xs font-black text-slate-900 leading-snug">
                    {phase.title}
                  </h3>

                  <p className="text-[11px] text-slate-600 leading-normal">
                    {phase.description}
                  </p>

                  <div className="p-2 bg-slate-50 rounded-lg border border-slate-100 text-[10px] text-slate-500 italic font-serif">
                    {phase.narration}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => handleRunPhase(phase.num, phase.targetTab)}
                    disabled={runningPhase === phase.num}
                    className={`w-full py-2 rounded-lg font-black text-xs transition-colors flex items-center justify-center space-x-1.5 ${
                      isCurrent
                        ? 'bg-purple-700 hover:bg-purple-800 text-white shadow'
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                    }`}
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>{runningPhase === phase.num ? 'Running...' : `Run Phase ${phase.num}`}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Interactive NLP Modality & Negation Testing Lab (Phase 8 Relocation) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600 font-bold">
              NLP
            </span>
            <div>
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Interactive SIF Modality & Negation Testing Lab
              </h2>
              <p className="text-[11px] text-slate-500">
                Test arbitrary narratives for Assertion, Negation, Hypothetical, Post-Event & Evidence Binding
              </p>
            </div>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          <span className="text-slate-400 font-bold mr-1">Presets:</span>
          {[
            { label: 'Negation', text: 'No worker entered the exclusion zone during pipe handling.' },
            { label: 'Hypothetical', text: 'If the sling fails, the load could fall into the manifold area.' },
            { label: 'Post-Event', text: 'The barricade was installed after the incident occurred.' },
            { label: 'Active SIF', text: 'Worker crossed the barricade into the crane exclusion zone while a drill collar was suspended overhead.' },
            { label: 'Aborted', text: 'Worker almost entered the zone but stopped before crossing.' },
            { label: 'Temporal', text: 'Worker entered the zone after lifting was completed.' },
            { label: 'Compromised Barrier', text: 'No worker entered the zone despite the barricade being removed.' }
          ].map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setNlpText(item.text);
                handleRunNlpAnalysis(item.text);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] transition-colors"
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          <textarea
            rows={2}
            value={nlpText}
            onChange={(e) => setNlpText(e.target.value)}
            className="w-full p-3 rounded-xl border border-slate-300 text-xs text-slate-900 font-sans focus:outline-none focus:ring-1 focus:ring-purple-500"
            placeholder="Type or paste any safety narrative here..."
          />
          <div className="flex justify-end">
            <button
              onClick={() => handleRunNlpAnalysis(nlpText)}
              disabled={isNlpAnalyzing}
              className="px-4 py-2 rounded-xl bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs shadow flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-white" />
              <span>{isNlpAnalyzing ? 'Analyzing Narrative...' : 'Run Modality Analysis'}</span>
            </button>
          </div>
        </div>

        {nlpResult && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3 animate-fade-in text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase">Result:</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                  nlpResult.sif_potential ? 'bg-red-600 text-white' : 'bg-slate-200 text-slate-800'
                }`}>
                  SIF: {nlpResult.sif_potential ? 'HIGH PRECURSOR' : 'NOT SIF'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  Modality: {nlpResult.assertion_status || 'ASSERTED'}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500">
                Score: {nlpResult.sif_score ?? 95}/100
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase font-bold">Hazard:</span>
                <span className="font-bold text-slate-800">{nlpResult.hazard || 'Mechanical Lifting'}</span>
              </div>
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase font-bold">Exposure:</span>
                <span className="font-bold text-slate-800">{nlpResult.exposure || 'Inside exclusion zone'}</span>
              </div>
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase font-bold">Barrier:</span>
                <span className="font-bold text-slate-800">{nlpResult.barrier || 'Exclusion Boundary'}</span>
              </div>
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase font-bold">LSR:</span>
                <span className="font-bold text-slate-800">{nlpResult.life_saving_rule || 'Line of Fire'}</span>
              </div>
            </div>

            {nlpResult.explanation && (
              <p className="text-[11px] text-slate-600 font-serif italic bg-white p-2.5 rounded-lg border border-slate-200">
                "{nlpResult.explanation}"
              </p>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
