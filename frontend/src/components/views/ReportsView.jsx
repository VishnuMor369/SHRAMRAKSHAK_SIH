import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  PlusCircle, 
  Search, 
  Filter, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Video, 
  User, 
  FileSpreadsheet, 
  ArrowRight, 
  Eye, 
  X, 
  Sparkles, 
  Check, 
  RefreshCw,
  Layers,
  ChevronRight
} from 'lucide-react';
import { fetchUnifiedEvents, submitHumanReport } from '../../services/api';
import EvidenceDetailDrawer from '../EvidenceDetailDrawer';
import { UnifiedModal } from '../common';

export default function ReportsView() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [sifFilter, setSifFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [analyzedEvent, setAnalyzedEvent] = useState(null);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('SUMMARY'); // SUMMARY | REASONING | EVIDENCE | DETAILS

  // Human Report Input State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [formNarrative, setFormNarrative] = useState('');
  const [formLocation, setFormLocation] = useState('Drilling Rig 04 - Drill Floor');
  const [formActivity, setFormActivity] = useState('Mechanical Lifting Operations');
  const [formReporter, setFormReporter] = useState('Field HSE Supervisor (OIL)');
  const [formDateTime, setFormDateTime] = useState('');
  const [formError, setFormError] = useState('');

  // Benchmark Test Presets for SIH Judge Demonstration
  const presets = [
    {
      title: 'Active SIF Precursor (Asserted)',
      narrative: 'Worker crossed the barricade into the crane exclusion zone while a drill collar was suspended overhead.',
      location: 'Drilling Rig 04 - Drill Floor',
      activity: 'Mechanical Lifting Operations',
      tag: 'SIF HIGH'
    },
    {
      title: 'Negation Handling',
      narrative: 'No worker entered the exclusion zone during pipe handling operations.',
      location: 'Pipe Yard 02',
      activity: 'Tubular Handling',
      tag: 'NOT SIF'
    },
    {
      title: 'Hypothetical Phrasing',
      narrative: 'If the sling fails, the load could fall into the manifold area.',
      location: 'Wellhead 08 - Manifold',
      activity: 'Rigging and Hoisting',
      tag: 'HYPOTHETICAL'
    },
    {
      title: 'Post-Event Condition',
      narrative: 'The barricade was installed after the incident occurred.',
      location: 'Compressor Station A',
      activity: 'Corrective Action Review',
      tag: 'POST-EVENT'
    },
    {
      title: 'Aborted Near-Miss Entry',
      narrative: 'Worker almost entered the zone but stopped before crossing the yellow boundary line.',
      location: 'Drill Floor Rig 02',
      activity: 'Casing Operations',
      tag: 'ABORTED'
    },
    {
      title: 'Temporal Post-Completion',
      narrative: 'Worker entered the zone after lifting was completed and the load was landed safely.',
      location: 'Lifting Area Bay 03',
      activity: 'Equipment Maintenance',
      tag: 'POST-LIFT'
    },
    {
      title: 'Compromised Barrier (Zero Exposure)',
      narrative: 'No worker entered the zone despite the barricade being removed during shift handover.',
      location: 'Subsea Assembly Yard',
      activity: 'Shift Handover',
      tag: 'BARRIER-FAIL'
    }
  ];

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await fetchUnifiedEvents();
      const list = Array.isArray(data) ? data : (data?.events || []);
      setEvents(list);
      if (!analyzedEvent && list.length > 0) {
        setAnalyzedEvent(list[0]);
      }
    } catch (err) {
      console.error('Failed to load unified safety events:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleApplyPreset = (p) => {
    setFormNarrative(p.narrative);
    setFormLocation(p.location);
    setFormActivity(p.activity);
    setFormError('');
  };

  const handleSubmitHumanReport = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!formNarrative.trim()) {
      setFormError('Please enter what happened in the safety narrative.');
      return;
    }
    setFormError('');
    setSubmitting(true);

    try {
      const payload = {
        narrative: formNarrative,
        location: formLocation,
        activity: formActivity,
        reporter: formReporter,
        timestamp: formDateTime || new Date().toISOString()
      };

      const result = await submitHumanReport(payload);
      setSubmitting(false);
      setSubmitSuccess(true);

      const newEvt = result.event || result;
      if (newEvt) {
        setAnalyzedEvent(newEvt);
        setEvents((prev) => [newEvt, ...prev.filter((e) => e.event_id !== newEvt.event_id)]);
      } else {
        await loadEvents();
      }

      setTimeout(() => {
        setSubmitSuccess(false);
      }, 2500);
    } catch (err) {
      setSubmitting(false);
      setFormError(err.message || 'Failed to submit report. Please retry.');
    }
  };

  // Filter events
  const filteredEvents = events.filter((ev) => {
    if (sourceFilter !== 'ALL' && ev.source !== sourceFilter) return false;
    if (sifFilter !== 'ALL') {
      const p = (ev.sif_potential || '').toUpperCase();
      if (sifFilter === 'HIGH' && !p.includes('HIGH') && !p.includes('CRITICAL')) return false;
      if (sifFilter === 'MEDIUM' && !p.includes('MEDIUM')) return false;
      if (sifFilter === 'LOW' && !p.includes('LOW')) return false;
      if (sifFilter === 'NOT_SIF' && !p.includes('NOT') && !p.includes('NO')) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = (ev.event_id || '').toLowerCase().includes(q);
      const matchNarrative = (ev.narrative || '').toLowerCase().includes(q);
      const matchLoc = (ev.location || '').toLowerCase().includes(q);
      const matchAct = (ev.activity || '').toLowerCase().includes(q);
      const matchHazard = (ev.hazard || '').toLowerCase().includes(q);
      if (!matchId && !matchNarrative && !matchLoc && !matchAct && !matchHazard) return false;
    }
    return true;
  });

  const getSourceBadge = (source) => {
    switch (source) {
      case 'HUMAN':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <User className="w-3 h-3" /> HUMAN
          </span>
        );
      case 'CCTV':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
            <Video className="w-3 h-3" /> CCTV
          </span>
        );
      case 'IMPORTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <FileSpreadsheet className="w-3 h-3" /> IMPORTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300">
            {source}
          </span>
        );
    }
  };

  const getSifBadge = (sif, assertion) => {
    const s = (sif || '').toUpperCase();
    if (assertion === 'NEGATED' || s.includes('NOT') || s.includes('NO_SIF') || s === 'NO') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-100 text-slate-600 border border-slate-300">
          NOT SIF
        </span>
      );
    }
    if (assertion === 'HYPOTHETICAL') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-blue-100 text-blue-800 border border-blue-300">
          HYPOTHETICAL
        </span>
      );
    }
    if (s.includes('HIGH') || s.includes('CRITICAL') || s.includes('SIF-POTENTIAL') || s.includes('SIF_POTENTIAL')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white shadow-sm">
          SIF HIGH
        </span>
      );
    }
    if (s.includes('MEDIUM') || s.includes('REVIEW')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500 text-slate-950 font-bold">
          SIF MEDIUM
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-200 text-slate-800">
        SIF LOW
      </span>
    );
  };

  const getLifecycleBadge = (state) => {
    const s = state || 'REPORTED';
    let color = 'bg-slate-100 text-slate-700 border-slate-300';
    if (s === 'ACTION_REQUIRED') color = 'bg-red-50 text-red-700 border-red-200';
    if (s === 'ACTION_IN_PROGRESS') color = 'bg-amber-50 text-amber-700 border-amber-200';
    if (s === 'AWAITING_VERIFICATION') color = 'bg-blue-50 text-blue-700 border-blue-200';
    if (s === 'VERIFIED' || s === 'RESOLVED') color = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider ${color}`}>
        {s.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              SAFETY REPORTS • WORKSPACE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Contextual NLP & Explainable SIF Precursor Intelligence
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-1">
            Report Analysis Workspace
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={loadEvents}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 text-xs font-bold transition-colors shadow-sm disabled:opacity-50"
            title="Refresh reports list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-amber-500' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 2. Interactive Report Analysis Workspace (Section 6) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <BrainCircuit className="w-4 h-4 text-amber-600" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Analyze Safety Observation / Near-Miss Narrative
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            OIL NLP SIF Engine
          </span>
        </div>

        {/* SIH Benchmark Presets Selector */}
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Judge Demonstration Benchmark Presets:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className="px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-amber-50 text-slate-700 hover:text-amber-900 border border-slate-200 hover:border-amber-300 text-[11px] font-semibold transition-all flex items-center gap-1.5"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                <span>{p.title}</span>
                <span className="text-[9px] font-mono font-bold text-slate-400">({p.tag})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Narrative Input Form */}
        <form onSubmit={handleSubmitHumanReport} className="space-y-3.5">
          <div>
            <textarea
              rows={3}
              value={formNarrative}
              onChange={(e) => setFormNarrative(e.target.value)}
              placeholder="Describe what occurred, who was involved, equipment in motion, barriers bypassed, or hazardous condition observed..."
              className="w-full p-3.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-xs font-medium text-slate-900 placeholder-slate-400 outline-none focus:border-amber-500 transition-all resize-y"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Location / Rig Area
              </label>
              <input 
                type="text"
                value={formLocation}
                onChange={(e) => setFormLocation(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white text-xs font-semibold text-slate-800 outline-none focus:border-amber-500 transition-all"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Work Activity
              </label>
              <input 
                type="text"
                value={formActivity}
                onChange={(e) => setFormActivity(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white text-xs font-semibold text-slate-800 outline-none focus:border-amber-500 transition-all"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Observer / Reporter
              </label>
              <input 
                type="text"
                value={formReporter}
                onChange={(e) => setFormReporter(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white text-xs font-semibold text-slate-800 outline-none focus:border-amber-500 transition-all"
              />
            </div>
          </div>

          {formError && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs font-bold text-red-700">
              {formError}
            </div>
          )}

          {submitSuccess && (
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Report analyzed and safely ingested into canonical safety event store!</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-500">
              Applies assertion detection, negation handling, hypothetical filtering, and IOGP Life-Saving Rules.
            </span>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs shadow-md transition-all flex items-center gap-2 disabled:opacity-60"
            >
              <Sparkles className={`w-4 h-4 ${submitting ? 'animate-spin' : ''}`} />
              <span>{submitting ? 'Analyzing Report...' : 'Analyze Report'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* 3. PROGRESSIVE DISCLOSURE ANALYSIS RESULT (Section 6) */}
      {analyzedEvent && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-0">
          
          {/* Top Banner of Analyzed Event */}
          <div className="p-5 bg-slate-900 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 shrink-0">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold text-amber-400">
                    {analyzedEvent.event_id || analyzedEvent.id || 'EVT-CURRENT'}
                  </span>
                  {getSourceBadge(analyzedEvent.source)}
                  {getSifBadge(analyzedEvent.sif_potential, analyzedEvent.assertion_status)}
                </div>
                <h3 className="text-sm font-extrabold text-slate-100 mt-0.5">
                  {analyzedEvent.title || analyzedEvent.observed_event || 'Analyzed Safety Observation'}
                </h3>
              </div>
            </div>

            <button
              onClick={() => {
                setSelectedEvent(analyzedEvent);
                setIsDrawerOpen(true);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition-colors self-start sm:self-auto flex items-center gap-1.5 border border-slate-700"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Open Side Drawer Drill-Down</span>
            </button>
          </div>

          {/* Progressive Disclosure Navigation Tabs */}
          <div className="flex border-b border-slate-200 bg-slate-50 px-5 text-xs font-bold">
            {[
              { id: 'SUMMARY', label: '1. SUMMARY' },
              { id: 'REASONING', label: '2. DETAILED REASONING' },
              { id: 'EVIDENCE', label: `3. NLP EVIDENCE SPANS (${analyzedEvent.evidence_spans?.length || 0})` },
              { id: 'DETAILS', label: '4. FULL EVENT DETAILS' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveAnalysisTab(tab.id)}
                className={`py-3 px-4 border-b-2 font-bold transition-all ${
                  activeAnalysisTab === tab.id
                    ? 'border-amber-500 text-amber-600 bg-white shadow-xs'
                    : 'border-transparent text-slate-500 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab 1: SUMMARY */}
          {activeAnalysisTab === 'SUMMARY' && (
            <div className="p-5 space-y-4">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 font-serif text-sm leading-relaxed">
                "{analyzedEvent.narrative || analyzedEvent.raw_text || 'No narrative text provided.'}"
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Exposure State</span>
                  <span className={`text-xs font-bold mt-1 block ${analyzedEvent.assertion_status === 'NEGATED' ? 'text-slate-500 line-through' : 'text-red-700'}`}>
                    {analyzedEvent.exposure || 'Personnel inside line-of-fire zone'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Hazard / Energy</span>
                  <span className="text-xs font-bold text-slate-900 mt-1 block">
                    {analyzedEvent.hazard || 'Mechanical / Gravitational Energy'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Critical Barrier</span>
                  <span className="text-xs font-bold text-slate-900 mt-1 block">
                    {analyzedEvent.critical_barrier || 'Exclusion Zone / Barricade'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">IOGP Life-Saving Rule</span>
                  <span className="text-xs font-bold text-blue-900 mt-1 block">
                    {analyzedEvent.life_saving_rule || 'Line of Fire / Safe Lifting'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: REASONING */}
          {activeAnalysisTab === 'REASONING' && (
            <div className="p-5 space-y-4 text-xs">
              <div className={`p-4 rounded-xl border ${
                analyzedEvent.assertion_status === 'NEGATED'
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                  : analyzedEvent.assertion_status === 'HYPOTHETICAL'
                  ? 'bg-blue-50 border-blue-300 text-blue-950'
                  : analyzedEvent.assertion_status === 'POST_EVENT'
                  ? 'bg-purple-50 border-purple-300 text-purple-950'
                  : 'bg-red-50 border-red-300 text-red-950'
              }`}>
                <div className="flex items-center justify-between font-bold mb-1">
                  <span className="uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    {analyzedEvent.assertion_status === 'NEGATED' && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                    {analyzedEvent.assertion_status === 'HYPOTHETICAL' && <HelpCircle className="w-4 h-4 text-blue-600" />}
                    {analyzedEvent.assertion_status === 'POST_EVENT' && <Clock className="w-4 h-4 text-purple-600" />}
                    {analyzedEvent.assertion_status !== 'NEGATED' && analyzedEvent.assertion_status !== 'HYPOTHETICAL' && analyzedEvent.assertion_status !== 'POST_EVENT' && <ShieldAlert className="w-4 h-4 text-red-600" />}
                    Assertion Status: {analyzedEvent.assertion_status || 'ASSERTED'}
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-white/70 border">
                    Confidence: {Math.round((analyzedEvent.confidence || 0.95) * 100)}%
                  </span>
                </div>
                <p className="text-xs leading-relaxed mt-1">
                  {analyzedEvent.assertion_status === 'NEGATED' && 'Negation detected in source observation. The dangerous exposure did NOT occur, correctly suppressing false-positive SIF precursor alarms.'}
                  {analyzedEvent.assertion_status === 'HYPOTHETICAL' && 'Hypothetical / conditional phrasing detected ("if/could"). Evaluated as hypothetical consequence rather than an observed failure.'}
                  {analyzedEvent.assertion_status === 'POST_EVENT' && 'Post-event / temporal phrasing detected ("after incident"). Control barrier was implemented retrospectively, not during the original event.'}
                  {analyzedEvent.assertion_status !== 'NEGATED' && analyzedEvent.assertion_status !== 'HYPOTHETICAL' && analyzedEvent.assertion_status !== 'POST_EVENT' && 'Direct affirmative observation of an active workplace condition or behavior.'}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <span className="font-bold text-slate-800 uppercase tracking-wider text-[10px] block">
                  SIF Potential Reasoning & Consequence Derivation
                </span>
                <p className="text-slate-700 leading-relaxed">
                  {analyzedEvent.potential_consequence 
                    ? `Potential Consequence: ${analyzedEvent.potential_consequence}. In the absence of an effective critical barrier (${analyzedEvent.critical_barrier || 'Exclusion Zone'}), release of hazardous energy would result in a fatal or permanent disabling injury.`
                    : 'Evaluated against IOGP Life-Saving Rules and high-energy hazard criteria.'}
                </p>
              </div>
            </div>
          )}

          {/* Tab 3: EVIDENCE SPANS */}
          {activeAnalysisTab === 'EVIDENCE' && (
            <div className="p-5 space-y-3 text-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Ground-Truth Extracted Spans Bound to SIF Conclusions:
              </span>
              {analyzedEvent.evidence_spans && analyzedEvent.evidence_spans.length > 0 ? (
                <div className="space-y-2">
                  {analyzedEvent.evidence_spans.map((span, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center space-x-2.5">
                        <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase bg-slate-200 text-slate-800 border border-slate-300">
                          {span.category || 'FACT'}
                        </span>
                        <span className="font-semibold text-slate-900 text-xs">
                          "{span.span_text}"
                        </span>
                      </div>
                      <span className="text-slate-400 font-mono text-[10px]">
                        [{span.start_char}:{span.end_char}]
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-slate-400 bg-slate-50 rounded-xl border border-slate-200">
                  <span>No explicit textual spans extracted for this event.</span>
                </div>
              )}
            </div>
          )}

          {/* Tab 4: FULL EVENT DETAILS */}
          {activeAnalysisTab === 'DETAILS' && (
            <div className="p-5 space-y-3 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 block uppercase">Source</span>
                  <span className="font-bold text-slate-800 block mt-0.5">{analyzedEvent.source}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 block uppercase">Timestamp</span>
                  <span className="font-mono text-slate-800 block mt-0.5">{analyzedEvent.timestamp ? new Date(analyzedEvent.timestamp).toLocaleString() : 'N/A'}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 block uppercase">Location</span>
                  <span className="font-bold text-slate-800 block mt-0.5">{analyzedEvent.location || 'N/A'}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 block uppercase">Knowledge State</span>
                  <span className="font-bold text-blue-700 block mt-0.5">{analyzedEvent.knowledge_state || 'OBSERVED'}</span>
                </div>
              </div>

              <div className="p-3 bg-slate-900 rounded-xl text-slate-300 font-mono text-[11px] overflow-x-auto max-h-48">
                <pre>{JSON.stringify(analyzedEvent, null, 2)}</pre>
              </div>
            </div>
          )}

        </div>
      )}

      {/* 2. Filters & Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        
        {/* Source Filter Tabs */}
        <div className="flex items-center gap-1.5 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">Source:</span>
          {['ALL', 'HUMAN', 'IMPORTED', 'CCTV'].map((src) => (
            <button
              key={src}
              onClick={() => setSourceFilter(src)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                sourceFilter === src
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              {src === 'ALL' && 'ALL'}
              {src === 'HUMAN' && '👤 HUMAN'}
              {src === 'IMPORTED' && '📄 IMPORTED'}
              {src === 'CCTV' && '📹 CCTV'}
            </button>
          ))}
        </div>

        {/* SIF Potential Filter & Search Input */}
        <div className="flex items-center gap-2.5 w-full md:w-auto">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SIF:</span>
            <select
              value={sifFilter}
              onChange={(e) => setSifFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white font-semibold text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="ALL">All Levels</option>
              <option value="HIGH">SIF High</option>
              <option value="MEDIUM">SIF Medium</option>
              <option value="LOW">SIF Low</option>
              <option value="NOT_SIF">Not SIF</option>
            </select>
          </div>

          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search narrative, ID, location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
          </div>
        </div>
      </div>

      {/* 3. Reports List */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center space-y-3">
          <RefreshCw className="w-6 h-6 text-amber-500 animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-500">Loading canonical safety events...</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center space-y-3">
          <FileText className="w-8 h-8 text-slate-300 mx-auto" />
          <p className="text-sm font-bold text-slate-700">No matching safety events found</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your source or SIF filters, or submit a new safety report using the button above.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvents.map((ev) => {
            const isHighSif = (ev.sif_potential || '').includes('HIGH') && ev.assertion_status !== 'NEGATED';
            return (
              <div
                key={ev.event_id}
                className={`bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-all ${
                  isHighSif ? 'border-l-4 border-l-red-500 border-slate-200' : 'border-slate-200'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2.5 border-b border-slate-100">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-extrabold text-slate-900">
                      {ev.event_id}
                    </span>
                    {getSourceBadge(ev.source)}
                    {getSifBadge(ev.sif_potential, ev.assertion_status)}
                    {getLifecycleBadge(ev.lifecycle_state)}
                  </div>

                  <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'Just now'}
                    </span>
                    <span className="font-semibold text-slate-700">
                      {ev.location || 'OIL Field Location'}
                    </span>
                  </div>
                </div>

                <div className="py-2.5">
                  <p className="text-xs text-slate-900 leading-relaxed font-serif">
                    "{ev.narrative || 'No description provided.'}"
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-[11px]">
                  <div className="flex flex-wrap items-center gap-2">
                    {ev.hazard && (
                      <span className="px-2 py-0.5 rounded bg-slate-50 text-slate-700 border border-slate-200 font-mono text-[10px]">
                        Hazard: <strong className="text-slate-900">{ev.hazard}</strong>
                      </span>
                    )}
                    {ev.critical_barrier && (
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-mono text-[10px]">
                        Barrier: <strong className="text-amber-950">{ev.critical_barrier}</strong> ({ev.barrier_condition || 'MONITORED'})
                      </span>
                    )}
                    {ev.lsr && (
                      <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-900 border border-purple-200 font-mono text-[10px]">
                        LSR: <strong className="text-purple-950">{ev.lsr}</strong>
                      </span>
                    )}
                    {ev.corroboration_status && ev.corroboration_status !== 'UNVERIFIED' && (
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold text-[10px]">
                        ✓ {ev.corroboration_status}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setSelectedEvent(ev);
                      setIsDrawerOpen(true);
                    }}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5 text-amber-400" />
                    <span>VIEW EVIDENCE</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {/* 4. Evidence Drill-Down Drawer */}

      {/* 5. Evidence Drill-Down Drawer */}
      <EvidenceDetailDrawer
        event={selectedEvent}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedEvent(null);
        }}
      />
    </div>
  );
}
