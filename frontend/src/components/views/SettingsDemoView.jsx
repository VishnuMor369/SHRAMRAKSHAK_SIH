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
import { executeDemoPhase, resetEnterpriseDemo } from '../../services/api';

export default function SettingsDemoView({ onNavigate }) {
  const [currentPhase, setCurrentPhase] = useState(1);
  const [runningPhase, setRunningPhase] = useState(null);
  const [phaseResult, setPhaseResult] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [feedback, setFeedback] = useState(null);

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
            onClick={handleReset}
            disabled={resetting}
            className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg border border-slate-300 transition-colors flex items-center space-x-1"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
            <span>RESET DEMO TO BASELINE</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div className="p-3.5 rounded-xl bg-purple-50 border border-purple-300 text-purple-900 font-bold text-xs flex items-center justify-between animate-fade-in">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="text-purple-700 text-xs">✕</button>
        </div>
      )}

      {/* 2. Synthetic Dataset Notice (Section 17 Compliance) */}
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

    </div>
  );
}
