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

  // New Human Report Modal State
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
  };

  const handleSubmitHumanReport = async (e) => {
    e.preventDefault();
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

      // Prepend newly created event immediately in real-time
      if (result.event) {
        setEvents((prev) => [result.event, ...prev.filter((e) => e.event_id !== result.event.event_id)]);
      } else {
        await loadEvents();
      }

      setTimeout(() => {
        setIsModalOpen(false);
        setSubmitSuccess(false);
        setFormNarrative('');
      }, 1200);
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
      
      {/* 1. Header Bar with Action Button */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              UNIFIED SAFETY PIPELINE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Canonical Safety Events across Human, Import & Vision
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            Safety Reports & Observations
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
              {filteredEvents.length} records
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadEvents}
            disabled={loading}
            className="p-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-sm"
            title="Refresh Reports"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => {
              setFormError('');
              setIsModalOpen(true);
            }}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-extrabold text-xs shadow-md transition-all transform active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ NEW SAFETY REPORT</span>
          </button>
        </div>
      </div>

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

      {/* 4. MODAL: + NEW SAFETY REPORT (Real Pipeline Execution) */}
      <UnifiedModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        maxWidthClass="max-w-2xl"
      >
            {/* Modal Header */}
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                  <PlusCircle className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-extrabold text-white">
                    Submit New Safety Observation / Incident Report
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Source = HUMAN • Automatically ingested into NLP & SIF Precursor Pipeline
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmitHumanReport} className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
              
              {/* Presets Bar for SIH Testing */}
              <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-3 space-y-2">
                <span className="text-[10px] font-black uppercase text-amber-900 tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                  Quick Benchmarks (SIH Problem Testing Scenarios):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {presets.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleApplyPreset(p)}
                      className="px-2 py-1 rounded bg-white hover:bg-amber-100 border border-amber-300 text-amber-950 font-semibold text-[11px] transition-colors"
                    >
                      {p.title}
                    </button>
                  ))}
                </div>
              </div>

              {/* Form Field: What Happened (Narrative) */}
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-800 uppercase tracking-wider">
                  What Happened? (Observation / Incident Narrative) *
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="e.g., Worker crossed the barricade into the crane exclusion zone while a drill collar was suspended overhead."
                  value={formNarrative}
                  onChange={(e) => setFormNarrative(e.target.value)}
                  className="w-full p-3 rounded-xl border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500 leading-relaxed font-sans"
                />
              </div>

              {/* Form Fields Grid: Location, Activity, Reporter */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                    Location
                  </label>
                  <input
                    type="text"
                    value={formLocation}
                    onChange={(e) => setFormLocation(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                    Activity
                  </label>
                  <input
                    type="text"
                    value={formActivity}
                    onChange={(e) => setFormActivity(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                    Reporter / Role
                  </label>
                  <input
                    type="text"
                    value={formReporter}
                    onChange={(e) => setFormReporter(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                    Timestamp (optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={formDateTime}
                    onChange={(e) => setFormDateTime(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                </div>
              </div>

              {/* Error state */}
              {formError && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Success state */}
              {submitSuccess && (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 font-bold animate-fade-in">
                  <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <span>Report analyzed & saved to Unified Event Store successfully! Updating records...</span>
                </div>
              )}

              {/* Modal Footer */}
              <div className="pt-3 border-t border-slate-200 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-bold text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || submitSuccess}
                  className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-amber-400 font-extrabold text-xs shadow-md flex items-center gap-2 transition-all transform active:scale-95 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                      <span>ANALYZING & PERSISTING...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <span>ANALYZE & SUBMIT</span>
                    </>
                  )}
                </button>
              </div>
            </form>
      </UnifiedModal>

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
