import React, { useState, useEffect } from 'react';
import { 
  BrainCircuit, 
  Search, 
  Filter, 
  ShieldAlert, 
  CheckCircle2, 
  HelpCircle, 
  ArrowRight, 
  Sparkles,
  Play,
  RotateCcw,
  FileText,
  AlertTriangle
} from 'lucide-react';
import { analyzeRawText, fetchDatasetReports } from '../../services/api';
import EvidenceDetailDrawer from '../EvidenceDetailDrawer';

export default function SafetyIntelligenceView() {
  const [selectedReport, setSelectedReport] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sifFilter, setSifFilter] = useState('ALL');

  // Interactive Live NLP Assertion Lab
  const [customText, setCustomText] = useState('Worker entered lifting exclusion zone while 15T pipe load was suspended.');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  // Realistic OIL-style benchmark observations with full safety ontology
  const benchmarkReports = [
    {
      id: 'REP-OIL-2026-001',
      event_id: 'EVT-OIL-001',
      source: 'HUMAN_REPORT',
      location: 'Drilling Rig 04 - Drill Floor',
      activity: 'Mechanical Lifting Operations',
      hazard: 'Suspended 15T Drill Collar',
      exposure: 'Roustabout inside lifting radius',
      critical_barrier: 'Lifting Exclusion Zone & Segregation',
      barrier_condition: 'VIOLATED',
      sif_potential: 'HIGH',
      sif_level: 'HIGH',
      life_saving_rule: 'Line of Fire / Work Authorization',
      assertion_status: 'ASSERTED',
      temporal_status: 'CURRENT',
      knowledge_state: 'OBSERVED',
      validation_status: 'HSE_VALIDATED',
      narrative: 'Worker crossed red barricade tape into crane exclusion zone while drill collar was suspended 2m overhead.',
      potential_consequence: 'Fatal crush or severe blunt impact',
      evidence_spans: [
        { category: 'HAZARD', span_text: 'drill collar was suspended 2m overhead', start_char: 56, end_char: 96 },
        { category: 'EXPOSURE', span_text: 'Worker crossed red barricade tape into crane exclusion zone', start_char: 0, end_char: 59 },
        { category: 'BARRIER', span_text: 'red barricade tape into crane exclusion zone', start_char: 15, end_char: 59 }
      ]
    },
    {
      id: 'REP-OIL-2026-002',
      event_id: 'EVT-OIL-002',
      source: 'HUMAN_REPORT',
      location: 'Pipe Yard 02',
      activity: 'Tubular Pipe Handling',
      hazard: 'Moving Mobile Crane Boom',
      exposure: 'NEGATED (No entry)',
      critical_barrier: 'Physical Hard Barricading',
      barrier_condition: 'INTACT',
      sif_potential: 'NOT_SIF',
      sif_level: 'NOT_SIF',
      life_saving_rule: 'Work Authorization',
      assertion_status: 'NEGATED',
      temporal_status: 'CURRENT',
      knowledge_state: 'OBSERVED',
      validation_status: 'CANDIDATE',
      narrative: 'No worker entered the exclusion zone during pipe offloading operation. Perimeter remained clear.',
      potential_consequence: 'None - barrier held intact',
      evidence_spans: [
        { category: 'ASSERTION', span_text: 'No worker entered', start_char: 0, end_char: 17 },
        { category: 'BARRIER', span_text: 'exclusion zone', start_char: 22, end_char: 36 }
      ]
    },
    {
      id: 'REP-OIL-2026-003',
      event_id: 'EVT-OIL-003',
      source: 'HUMAN_REPORT',
      location: 'Wellhead 08 - Manifold Area',
      activity: 'Rigging and Crane Hoisting',
      hazard: 'Potential Dropped Object',
      exposure: 'Hypothetical Line-of-Fire',
      critical_barrier: 'Certified Webbing Sling',
      barrier_condition: 'HYPOTHETICAL_RISK',
      sif_potential: 'LOW',
      sif_level: 'LOW',
      life_saving_rule: 'Line of Fire',
      assertion_status: 'HYPOTHETICAL',
      temporal_status: 'HYPOTHETICAL',
      knowledge_state: 'INFERRED',
      validation_status: 'CANDIDATE',
      narrative: 'If the sling fails, the suspended load could fall into the active wellhead manifold area.',
      potential_consequence: 'Hypothetical equipment damage and high-pressure release',
      evidence_spans: [
        { category: 'ASSERTION', span_text: 'If the sling fails', start_char: 0, end_char: 18 },
        { category: 'CONSEQUENCE', span_text: 'suspended load could fall', start_char: 24, end_char: 49 }
      ]
    },
    {
      id: 'REP-OIL-2026-004',
      event_id: 'EVT-OIL-004',
      source: 'HUMAN_REPORT',
      location: 'Compressor Station 01',
      activity: 'High-Pressure Gas Line Maintenance',
      hazard: 'Flammable Pressurized Gas',
      exposure: 'Maintenance technician at valve flange',
      critical_barrier: 'LOTO / Positive Isolation Verification',
      barrier_condition: 'INEFFECTIVE',
      sif_potential: 'HIGH',
      sif_level: 'HIGH',
      life_saving_rule: 'Energy Isolation (LOTO)',
      assertion_status: 'ASSERTED',
      temporal_status: 'CURRENT',
      knowledge_state: 'OBSERVED',
      validation_status: 'HSE_VALIDATED',
      narrative: 'Maintenance commenced on discharge manifold without verified zero-energy bleed or physical isolation lock applied.',
      potential_consequence: 'High-pressure gas explosion or toxic release',
      evidence_spans: [
        { category: 'HAZARD', span_text: 'discharge manifold', start_char: 25, end_char: 43 },
        { category: 'BARRIER', span_text: 'without verified zero-energy bleed or physical isolation lock', start_char: 44, end_char: 105 }
      ]
    },
    {
      id: 'REP-OIL-2026-005',
      event_id: 'EVT-OIL-005',
      source: 'HUMAN_REPORT',
      location: 'Substation B - Switchgear Room',
      activity: 'Electrical Control Panel Overhaul',
      hazard: '415V Energized Busbars',
      exposure: 'Post-incident barrier installation',
      critical_barrier: 'Safety Lockout Hasps & Padlocks',
      barrier_condition: 'POST_EVENT_REMEDY',
      sif_potential: 'MEDIUM',
      sif_level: 'MEDIUM',
      life_saving_rule: 'Energy Isolation',
      assertion_status: 'POST_EVENT',
      temporal_status: 'POST_EVENT',
      knowledge_state: 'OBSERVED',
      validation_status: 'CANDIDATE',
      narrative: 'Danger barricade was installed after the incident occurred. Breaker was found unlocked during earlier shift inspection.',
      potential_consequence: 'Historical arc flash potential rectified retrospectively',
      evidence_spans: [
        { category: 'ASSERTION', span_text: 'installed after the incident occurred', start_char: 22, end_char: 59 },
        { category: 'BARRIER', span_text: 'Breaker was found unlocked', start_char: 61, end_char: 87 }
      ]
    },
    {
      id: 'REP-OIL-2026-006',
      event_id: 'EVT-CCTV-001',
      source: 'CCTV',
      location: 'Lifting Zone 03',
      activity: 'Mechanical Crane Hoisting',
      hazard: 'Suspended 10T Mud Motor',
      exposure: 'Personnel bottom-center inside exclusion polygon',
      critical_barrier: 'CCTV Defined Exclusion Zone',
      barrier_condition: 'VIOLATED',
      sif_potential: 'HIGH',
      sif_level: 'HIGH',
      life_saving_rule: 'Line of Fire',
      assertion_status: 'ASSERTED',
      temporal_status: 'CURRENT',
      knowledge_state: 'OBSERVED',
      validation_status: 'CANDIDATE',
      narrative: 'Machine-Generated Safety Observation: Worker detected inside restricted lifting exclusion zone for 5 consecutive frames.',
      potential_consequence: 'Fatal crush trauma under suspended industrial load',
      evidence_spans: [
        { category: 'EXPOSURE', span_text: 'Worker detected inside restricted lifting exclusion zone', start_char: 38, end_char: 94 },
        { category: 'BARRIER', span_text: 'restricted lifting exclusion zone', start_char: 61, end_char: 94 }
      ]
    }
  ];

  const handleRunAnalysis = async (textToAnalyze) => {
    const text = textToAnalyze || customText;
    if (!text.trim()) return;
    try {
      setIsAnalyzing(true);
      const res = await analyzeRawText(text);
      setAnalysisResult(res);
    } catch (err) {
      console.error('NLP Analysis failed:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const setPresetText = (preset) => {
    setCustomText(preset);
    handleRunAnalysis(preset);
  };

  const handleOpenDrawer = (rep) => {
    setSelectedReport(rep);
    setIsDrawerOpen(true);
  };

  const filteredReports = benchmarkReports.filter(rep => {
    const matchesSearch = !searchQuery || 
      rep.narrative.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rep.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rep.hazard.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSif = sifFilter === 'ALL' || rep.sif_potential === sifFilter;
    return matchesSearch && matchesSif;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-purple-100 text-purple-900 border border-purple-200">
              NLP SIF ENGINE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Context-Aware Event Understanding & Evidence Binding
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Safety Event Intelligence
          </h1>
        </div>

        <div className="text-xs text-slate-500 max-w-sm sm:text-right">
          Distinguishes <b className="text-slate-800">Observed Facts</b> from <b className="text-emerald-700">Negated</b>, <b className="text-blue-700">Hypothetical</b>, and <b className="text-purple-700">Post-Event</b> statements.
        </div>
      </div>

      {/* 2. Interactive NLP Assertion & Modality Lab (Demonstrates Deep Technical Depth) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Interactive SIF Modality & Negation Testing Lab
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="text-slate-400 font-bold">Quick Presets:</span>
            <button
              onClick={() => setPresetText('Worker entered lifting exclusion zone while 15T pipe was suspended.')}
              className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold transition-colors"
            >
              Direct Breach (SIF High)
            </button>
            <button
              onClick={() => setPresetText('No worker entered the exclusion zone during pipe handling.')}
              className="px-2 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-semibold border border-emerald-200 transition-colors"
            >
              Negated (NOT SIF)
            </button>
            <button
              onClick={() => setPresetText('If the sling fails, the suspended load could fall.')}
              className="px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 text-blue-800 font-semibold border border-blue-200 transition-colors"
            >
              Hypothetical
            </button>
            <button
              onClick={() => setPresetText('Barricade was installed after the incident occurred.')}
              className="px-2 py-1 rounded bg-purple-50 hover:bg-purple-100 text-purple-800 font-semibold border border-purple-200 transition-colors"
            >
              Post-Event
            </button>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-stretch">
          <input
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Type any safety observation narrative to test context-aware NLP parsing..."
            className="flex-1 px-3.5 py-2.5 rounded-lg border border-slate-300 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            onClick={() => handleRunAnalysis()}
            disabled={isAnalyzing}
            className="px-4 py-2.5 bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs rounded-lg shadow transition-colors flex items-center justify-center space-x-1.5"
          >
            {isAnalyzing ? (
              <span>Analyzing...</span>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span>Parse Safety Event</span>
              </>
            )}
          </button>
        </div>

        {/* Live Lab Results */}
        {analysisResult && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 animate-fade-in">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${
                  analysisResult.safety_event?.assertion_status === 'NEGATED'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : analysisResult.safety_event?.assertion_status === 'HYPOTHETICAL'
                    ? 'bg-blue-100 text-blue-800 border-blue-300'
                    : analysisResult.safety_event?.assertion_status === 'POST_EVENT'
                    ? 'bg-purple-100 text-purple-800 border-purple-300'
                    : 'bg-red-100 text-red-800 border-red-300'
                }`}>
                  MODALITY: {analysisResult.safety_event?.assertion_status || 'ASSERTED'}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-white">
                  SIF POTENTIAL: {analysisResult.safety_event?.sif_potential || (analysisResult.is_sif_precursor ? 'HIGH' : 'NOT SIF')}
                </span>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">
                LSR: <b className="text-slate-800">{analysisResult.life_saving_rule || 'Line of Fire'}</b>
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Hazard</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{analysisResult.safety_event?.hazard || 'Mechanical Lifting'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Exposure</span>
                <span className={`font-bold mt-0.5 block ${analysisResult.safety_event?.assertion_status === 'NEGATED' ? 'text-slate-400 line-through' : 'text-red-700'}`}>
                  {analysisResult.safety_event?.exposure || 'Personnel in Zone'}
                </span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Critical Barrier</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{analysisResult.safety_event?.critical_barrier || 'Exclusion Zone'}</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Barrier Condition</span>
                <span className="font-bold text-red-600 mt-0.5 block">{analysisResult.safety_event?.barrier_condition || 'VIOLATED'}</span>
              </div>
            </div>

            {analysisResult.safety_event?.evidence_spans && (
              <div className="text-[11px] text-slate-600 space-y-1">
                <span className="font-bold uppercase text-[10px] text-slate-500 block">Identified Ground-Truth Spans:</span>
                <div className="flex flex-wrap gap-1.5">
                  {analysisResult.safety_event.evidence_spans.map((sp, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px] text-slate-800">
                      [{sp.category}] "{sp.span_text}"
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 3. Safety Reports Table with Progressive Disclosure */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-3 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Historical & Live Safety Observations ({filteredReports.length})
            </h2>
            <span className="text-[11px] text-slate-500">
              Click any safety report to view character-level evidence spans and safety ontology drill-down.
            </span>
          </div>

          {/* Filters */}
          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search reports..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-500 w-48"
              />
            </div>

            <select
              value={sifFilter}
              onChange={(e) => setSifFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-800 bg-white"
            >
              <option value="ALL">All SIF Levels</option>
              <option value="HIGH">HIGH SIF</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
              <option value="NOT_SIF">NOT SIF</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Event ID</th>
                <th className="py-2.5 px-3">Source</th>
                <th className="py-2.5 px-3">Safety Narrative</th>
                <th className="py-2.5 px-3">Modality</th>
                <th className="py-2.5 px-3">SIF Potential</th>
                <th className="py-2.5 px-3">Life-Saving Rule</th>
                <th className="py-2.5 px-3 text-right">Drill-Down</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredReports.map((rep) => {
                const isHigh = rep.sif_potential === 'HIGH';
                const isNotSif = rep.sif_potential === 'NOT_SIF';
                return (
                  <tr 
                    key={rep.id}
                    onClick={() => handleOpenDrawer(rep)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-3 font-mono font-bold text-slate-700 whitespace-nowrap">
                      {rep.event_id}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                        rep.source === 'CCTV' 
                          ? 'bg-blue-50 text-blue-800 border-blue-200' 
                          : 'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {rep.source}
                      </span>
                    </td>
                    <td className="py-3 px-3 max-w-md">
                      <p className="font-semibold text-slate-900 line-clamp-1">
                        {rep.narrative}
                      </p>
                      <span className="text-[10px] text-slate-400">
                        {rep.location} • {rep.activity}
                      </span>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        rep.assertion_status === 'NEGATED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : rep.assertion_status === 'HYPOTHETICAL'
                          ? 'bg-blue-100 text-blue-800'
                          : rep.assertion_status === 'POST_EVENT'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}>
                        {rep.assertion_status}
                      </span>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                        isHigh 
                          ? 'bg-red-600 text-white' 
                          : isNotSif
                          ? 'bg-slate-200 text-slate-700'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {rep.sif_potential}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-medium text-slate-700 whitespace-nowrap">
                      {rep.life_saving_rule}
                    </td>
                    <td className="py-3 px-3 text-right whitespace-nowrap">
                      <span className="text-purple-600 font-bold group-hover:underline text-[11px] inline-flex items-center">
                        Evidence →
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Evidence Drill-Down Drawer */}
      <EvidenceDetailDrawer
        event={selectedReport}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />

    </div>
  );
}
