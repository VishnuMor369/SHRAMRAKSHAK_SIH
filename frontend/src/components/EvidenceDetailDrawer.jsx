import React from 'react';
import { X, ShieldAlert, CheckCircle2, AlertOctagon, HelpCircle, FileText, Video, Eye, Scale } from 'lucide-react';

export default function EvidenceDetailDrawer({ event, isOpen, onClose }) {
  if (!isOpen || !event) return null;

  const sifPotential = event.sif_potential || 'HIGH';
  const isHighSif = sifPotential === 'HIGH' || sifPotential === 'CRITICAL / HIGH';
  const assertion = event.assertion_status || 'ASSERTED';
  const isNegated = assertion === 'NEGATED';
  const isHypothetical = assertion === 'HYPOTHETICAL';
  const isPostEvent = assertion === 'POST_EVENT';

  const badgeBg = isNegated 
    ? 'bg-slate-100 text-slate-700 border-slate-300'
    : isHypothetical
    ? 'bg-blue-100 text-blue-800 border-blue-300'
    : isHighSif
    ? 'bg-red-100 text-red-800 border-red-300'
    : 'bg-amber-100 text-amber-800 border-amber-300';

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/50 backdrop-blur-sm animate-fade-in">
      <div 
        className="w-full max-w-xl bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-amber-400">
                  {event.event_id || event.id || 'EVT-SAFETY'}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${badgeBg}`}>
                  SIF: {sifPotential}
                </span>
              </div>
              <h2 className="text-sm font-bold text-slate-100">
                Safety Event Evidence Drill-Down
              </h2>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-slate-800 text-xs">
          
          {/* Assertion Status Banner (Critical for SIH Safety Correctness) */}
          <div className={`p-3.5 rounded-xl border ${
            isNegated 
              ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
              : isHypothetical
              ? 'bg-blue-50 border-blue-300 text-blue-950'
              : isPostEvent
              ? 'bg-purple-50 border-purple-300 text-purple-950'
              : 'bg-red-50 border-red-300 text-red-950'
          }`}>
            <div className="flex items-center justify-between font-bold mb-1">
              <span className="uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                {isNegated && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                {isHypothetical && <HelpCircle className="w-4 h-4 text-blue-600" />}
                {isPostEvent && <ClockIcon className="w-4 h-4 text-purple-600" />}
                {!isNegated && !isHypothetical && !isPostEvent && <ShieldAlert className="w-4 h-4 text-red-600" />}
                Assertion Modality: {assertion}
              </span>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-white/70 border">
                Confidence: {Math.round((event.confidence || 0.95) * 100)}%
              </span>
            </div>
            <p className="text-xs leading-relaxed">
              {isNegated && 'Negation detected in source observation. The dangerous exposure did NOT occur, correctly suppressing false-positive SIF precursor alarms.'}
              {isHypothetical && 'Hypothetical / conditional phrasing detected ("if/could"). Evaluated as hypothetical consequence rather than an observed failure.'}
              {isPostEvent && 'Post-event / temporal phrasing detected ("after incident"). Control barrier was implemented retrospectively, not during the original event.'}
              {!isNegated && !isHypothetical && !isPostEvent && 'Direct affirmative observation of an active workplace condition or behavior.'}
            </p>
          </div>

          {/* Original Observation Text & Evidence Highlights */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Source Narrative & Extracted Evidence Spans
            </span>
            <div className="p-3 bg-white rounded-lg border border-slate-200 text-slate-900 leading-relaxed font-serif text-sm">
              "{event.narrative || event.raw_text || event.title || event.observed_event || 'No raw narrative provided.'}"
            </div>

            {event.evidence_spans && event.evidence_spans.length > 0 && (
              <div className="space-y-1.5 pt-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  Ground-Truth Spans Bound to SIF Conclusions:
                </span>
                <div className="space-y-1">
                  {event.evidence_spans.map((span, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded bg-white border border-slate-200 text-[11px]">
                      <div className="flex items-center space-x-2">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-slate-100 text-slate-700 border">
                          {span.category || 'FACT'}
                        </span>
                        <span className="font-semibold text-slate-900">"{span.span_text}"</span>
                      </div>
                      <span className="text-slate-400 font-mono text-[10px]">
                        [{span.start_char}:{span.end_char}]
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Core Safety Ontology Attributes */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Hazard / Energy</span>
              <span className="text-xs font-bold text-slate-900 mt-1 block">
                {event.hazard || 'Mechanical / Gravitational Energy'}
              </span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Observable Exposure</span>
              <span className={`text-xs font-bold mt-1 block ${isNegated ? 'text-slate-500 line-through' : 'text-red-700'}`}>
                {event.exposure || 'Personnel inside line-of-fire zone'}
              </span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Critical Barrier</span>
              <span className="text-xs font-bold text-slate-900 mt-1 block">
                {event.critical_barrier || 'Exclusion Zone / Barricade'}
              </span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Barrier State</span>
              <span className={`text-xs font-bold mt-1 block ${isNegated ? 'text-emerald-700' : 'text-red-700'}`}>
                {event.barrier_condition || event.barrier_state || 'VIOLATED'}
              </span>
            </div>
          </div>

          {/* IOGP Life-Saving Rule & Consequence */}
          <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl space-y-1.5">
            <span className="text-[10px] font-bold text-amber-900 uppercase tracking-wider block">
              IOGP Life-Saving Rule (LSR) Mapping
            </span>
            <div className="text-xs font-bold text-slate-900">
              {event.life_saving_rule || 'Line of Fire / Safe Mechanical Lifting'}
            </div>
            <div className="text-[11px] text-slate-600">
              Potential Consequence: <span className="font-semibold text-slate-900">{event.potential_consequence || 'Crush trauma or severe pinch injury'}</span>
            </div>
          </div>

          {/* Governance & Evidence Provenance */}
          <div className="p-3 bg-slate-100 rounded-xl border border-slate-200 space-y-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Governance & Provenance Tracking
            </span>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-slate-500 block">Evidence Source:</span>
                <span className="font-bold text-slate-800">{event.source || event.evidence_source_type || 'HUMAN_REPORT'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Knowledge State:</span>
                <span className="font-bold text-blue-700">{event.knowledge_state || 'OBSERVED'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">HSE Validation:</span>
                <span className="font-bold text-amber-700">{event.validation_status || 'CANDIDATE'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Temporal Classification:</span>
                <span className="font-bold text-slate-800">{event.temporal_status || 'CURRENT'}</span>
              </div>
            </div>
          </div>

        </div>

        {/* Drawer Footer */}
        <div className="p-3.5 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button 
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow transition-colors"
          >
            Close Drill-Down
          </button>
        </div>
      </div>
    </div>
  );
}

function ClockIcon(props) {
  return (
    <svg 
      {...props} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}
