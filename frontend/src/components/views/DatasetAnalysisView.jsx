import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, 
  Download, 
  AlertTriangle, 
  CheckCircle2, 
  Layers, 
  BrainCircuit, 
  ShieldAlert, 
  Search, 
  Filter, 
  ArrowRight, 
  Database, 
  FileText, 
  RefreshCw,
  Eye,
  Info
} from 'lucide-react';
import { 
  fetchAnalysisRuns, 
  fetchAnalysisRunById, 
  getAnalysisRunPdfUrl 
} from '../../services/api';

export default function DatasetAnalysisView({ activeRunId, onNavigate }) {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(activeRunId || null);
  const [runData, setRunData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTab, setActiveTab] = useState('OVERVIEW'); // OVERVIEW, SIF, IOGP, PATTERNS, EXPLORER
  const [searchQuery, setSearchQuery] = useState('');
  const [sifFilter, setSifFilter] = useState('ALL');
  const [selectedRule, setSelectedRule] = useState(null);

  // Load list of available analysis runs
  useEffect(() => {
    fetchAnalysisRuns()
      .then(res => {
        const list = res.runs || [];
        setRuns(list);
        if (!selectedRunId && list.length > 0) {
          setSelectedRunId(list[0].run_id);
        }
      })
      .catch(err => {
        console.error('Failed to load analysis runs:', err);
        setErrorMsg('Failed to load analysis run history.');
      });
  }, []);

  // Load detailed data for selected run
  useEffect(() => {
    if (!selectedRunId) return;
    setLoading(true);
    setErrorMsg('');
    fetchAnalysisRunById(selectedRunId)
      .then(data => {
        setRunData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load run details:', err);
        setErrorMsg(`Failed to load details for run ${selectedRunId}`);
        setLoading(false);
      });
  }, [selectedRunId]);

  const handleDownloadPdf = () => {
    if (!selectedRunId) return;
    window.open(getAnalysisRunPdfUrl(selectedRunId), '_blank');
  };

  const reports = runData?.reports || [];
  const filteredReports = reports.filter(r => {
    const matchesSearch = !searchQuery || 
      (r.original_text && r.original_text.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.activity && r.activity.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.barrier && r.barrier.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesSif = sifFilter === 'ALL' || r.sif_potential === sifFilter;
    const matchesRule = !selectedRule || (r.lsr && r.lsr.includes(selectedRule));
    return matchesSearch && matchesSif && matchesRule;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Top Control Bar: Run Selector & Download PDF */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              DATASET INTELLIGENCE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Isolated Analysis Run Workspace
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center space-x-3">
            <span>Dataset Analysis:</span>
            {runs.length > 0 ? (
              <select
                value={selectedRunId || ''}
                onChange={(e) => setSelectedRunId(e.target.value)}
                className="bg-white border border-slate-300 text-slate-800 text-sm font-bold rounded-lg px-3 py-1 focus:ring-2 focus:ring-amber-500 outline-none"
              >
                {runs.map(r => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} — {r.filename} ({r.records_analyzed} records)
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-slate-400 text-sm font-normal">No runs loaded</span>
            )}
          </h1>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onNavigate && onNavigate('IMPORT DATA')}
            className="px-3.5 py-2 text-xs font-bold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 shadow-sm transition-all"
          >
            + Upload New Dataset
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={!runData}
            className="flex items-center space-x-2 px-4 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-xl shadow-md transition-all disabled:opacity-50"
          >
            <Download className="w-4 h-4 text-amber-400" />
            <span>DOWNLOAD PDF REPORT</span>
          </button>
        </div>
      </div>

      {/* 2. Metadata / Provenance Card */}
      {runData && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-3">
              <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2.5 py-1 rounded">
                Run ID: {runData.run_id}
              </span>
              <span className="text-slate-600 font-semibold">
                File: <span className="font-mono text-slate-900">{runData.filename}</span>
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
                {runData.file_type || 'CSV'}
              </span>
            </div>
            <div className="text-slate-500 text-[11px] font-mono">
              Upload Timestamp: {new Date(runData.upload_time).toLocaleString()}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center space-x-4">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-bold">Records Detected</span>
                <span className="font-extrabold text-slate-900 text-sm">{runData.records_detected}</span>
              </div>
              <div className="border-l border-slate-200 pl-4">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">Records Analyzed</span>
                <span className="font-extrabold text-emerald-700 text-sm">{runData.records_analyzed}</span>
              </div>
              <div className="border-l border-slate-200 pl-4">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">Review Required</span>
                <span className="font-extrabold text-amber-600 text-sm">{runData.review_count || 0}</span>
              </div>
              <div className="border-l border-slate-200 pl-4">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">Failed Rows</span>
                <span className="font-extrabold text-slate-600 text-sm">{runData.failed_count || 0}</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 flex items-center space-x-2">
              <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>Provenance: <strong className="text-slate-700">{runData.provenance || 'Uploaded Dataset'}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Section Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-xs font-bold">
        {[
          { id: 'OVERVIEW', label: '1. Overview' },
          { id: 'SIF', label: `2. SIF Analysis (${runData?.sif_count ?? 0})` },
          { id: 'IOGP', label: '3. IOGP Life-Saving Rules' },
          { id: 'PATTERNS', label: `4. Recurring Patterns (${runData?.candidate_patterns?.length ?? 0})` },
          { id: 'EXPLORER', label: `5. Report Explorer (${reports.length})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`pb-3 border-b-2 transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'border-amber-500 text-slate-900 font-extrabold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 4. Tab Contents */}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'OVERVIEW' && runData && (
        <div className="space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                SIF Precursors Detected
              </span>
              <div className="text-2xl font-black text-red-600">{runData.sif_count}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                {runData.sif_percentage}% of analyzed dataset
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Non-SIF Controls
              </span>
              <div className="text-2xl font-black text-emerald-600">{runData.non_sif_count}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                Low energy / effective barrier
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Candidate Patterns
              </span>
              <div className="text-2xl font-black text-purple-600">{runData.candidate_patterns?.length || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                Recurring mechanism clusters
              </div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Review Required
              </span>
              <div className="text-2xl font-black text-amber-600">{runData.review_count || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                Ambiguous / uncertain narrative
              </div>
            </div>
          </div>

          {/* Breakdown Distributions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Energy & Hazard Sources */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Top Energy & Hazard Categories
              </h3>
              <div className="space-y-2">
                {Object.entries(runData.hazard_distribution || {}).slice(0, 6).map(([haz, count]) => {
                  const pct = Math.round((count / Math.max(runData.records_analyzed, 1)) * 100);
                  return (
                    <div key={haz} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-semibold text-slate-700">{haz}</span>
                        <span className="font-mono text-slate-500">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div className="bg-amber-500 h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top Activities */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Operational Activities Breakdown
              </h3>
              <div className="space-y-2">
                {Object.entries(runData.activity_distribution || {}).slice(0, 6).map(([act, count]) => {
                  const pct = Math.round((count / Math.max(runData.records_analyzed, 1)) * 100);
                  return (
                    <div key={act} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-semibold text-slate-700">{act}</span>
                        <span className="font-mono text-slate-500">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div className="bg-blue-600 h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SIF ANALYSIS */}
      {activeTab === 'SIF' && runData && (
        <div className="space-y-6">
          <div className="bg-red-50/50 border border-red-200 p-4 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center space-x-3">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0" />
              <div>
                <span className="font-bold text-red-900 block">
                  SIF Precursor Analysis for {runData.filename}
                </span>
                <span className="text-red-700 text-[11px]">
                  Evaluates high-energy hazards, exposure geometry, and critical barrier compromise. A report can be SIF-potential even when nobody was injured.
                </span>
              </div>
            </div>
            <div className="text-right shrink-0">
              <span className="text-xl font-black text-red-700 block font-mono">{runData.sif_count} / {runData.records_analyzed}</span>
              <span className="text-[10px] uppercase font-bold text-red-600">{runData.sif_percentage}% SIF Rate</span>
            </div>
          </div>

          {/* High Potential Evidence Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                High-Potential SIF Cases ({runData.high_potential_cases?.length || 0})
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                Evidence-Grounded Extraction
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {(runData.high_potential_cases || []).map((c, idx) => (
                <div key={idx} className="p-4 hover:bg-slate-50/60 transition-colors space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                        {c.report_id}
                      </span>
                      <span className="font-bold text-slate-700">{c.activity}</span>
                      <span className="text-slate-400">•</span>
                      <span className="text-slate-500 font-mono text-[11px]">{c.location || 'Site Operational Zone'}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-red-100 text-red-800 border border-red-200">
                      SIF POTENTIAL
                    </span>
                  </div>

                  <p className="text-xs text-slate-800 italic bg-amber-50/30 p-2.5 rounded border border-amber-200/60">
                    "{c.original_text}"
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Energy Source</span>
                      <span className="font-bold text-slate-700">{c.hazard}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Critical Barrier</span>
                      <span className="font-bold text-slate-700">{c.barrier}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Barrier State</span>
                      <span className="font-bold text-red-600">{c.barrier_state}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Life-Saving Rule</span>
                      <span className="font-bold text-blue-700">{c.lsr || 'Line of Fire'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: IOGP LIFE-SAVING RULES */}
      {activeTab === 'IOGP' && runData && (
        <div className="space-y-6">
          <div className="bg-blue-50/50 border border-blue-200 p-4 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center space-x-3">
              <BrainCircuit className="w-5 h-5 text-blue-600 shrink-0" />
              <div>
                <span className="font-bold text-blue-900 block">
                  IOGP Life-Saving Rules Mapping (Normalized from Analyzed Records)
                </span>
                <span className="text-blue-700 text-[11px]">
                  Counts and distributions reflect actual contextual NLP assertions. Click any rule to filter underlying incident records.
                </span>
              </div>
            </div>
            {selectedRule && (
              <button
                onClick={() => setSelectedRule(null)}
                className="px-2.5 py-1 text-[11px] font-bold text-blue-700 bg-white border border-blue-300 rounded hover:bg-blue-50 shadow-sm"
              >
                Clear Filter: {selectedRule}
              </button>
            )}
          </div>

          {/* Life-Saving Rules Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(runData.iogp_distribution || {}).map(([rule, count]) => {
              const isSelected = selectedRule === rule;
              const pct = Math.round((count / Math.max(runData.records_analyzed, 1)) * 100);
              return (
                <div
                  key={rule}
                  onClick={() => setSelectedRule(isSelected ? null : rule)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer shadow-sm ${
                    isSelected 
                      ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-500/20' 
                      : 'bg-white border-slate-200 hover:border-blue-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-bold text-slate-800 text-xs">{rule}</span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-blue-100 text-blue-800">
                      {count}
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-2">
                    <div className="bg-blue-600 h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%` }}></div>
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-slate-500 mt-2">
                    <span>{pct}% of dataset</span>
                    <span className="text-blue-600 font-bold hover:underline">
                      {isSelected ? 'Showing matching' : 'Click to filter'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Matching Reports for Selected Rule */}
          {selectedRule && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Reports mapped to "{selectedRule}" ({filteredReports.length})
              </h4>
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {filteredReports.map((r, i) => (
                  <div key={i} className="py-2.5 text-xs space-y-1">
                    <div className="flex justify-between font-mono text-[11px]">
                      <span className="font-bold text-slate-900">{r.report_id}</span>
                      <span className={r.sif_potential === 'HIGH' ? 'text-red-600 font-bold' : 'text-slate-500'}>
                        {r.sif_potential}
                      </span>
                    </div>
                    <p className="text-slate-700 italic">"{r.original_text}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: RECURRING PATTERNS */}
      {activeTab === 'PATTERNS' && runData && (
        <div className="space-y-4">
          <div className="bg-purple-50/50 border border-purple-200 p-4 rounded-xl text-xs flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Database className="w-5 h-5 text-purple-600 shrink-0" />
              <div>
                <span className="font-bold text-purple-900 block">
                  Dataset Recurring Candidate Patterns
                </span>
                <span className="text-purple-700 text-[11px]">
                  Groups records sharing the same operational activity and critical barrier failure mechanism. Labeled CANDIDATE PATTERN until official HSE validation.
                </span>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-800 font-mono font-bold text-xs">
              {runData.candidate_patterns?.length || 0} Patterns Found
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(runData.candidate_patterns || []).map((pat, idx) => (
              <div key={idx} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-purple-100 text-purple-800 border border-purple-200">
                    {pat.pattern_id}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-amber-50 text-amber-700 border border-amber-200">
                    CANDIDATE PATTERN
                  </span>
                </div>

                <h4 className="font-bold text-slate-900 text-sm">{pat.title}</h4>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Activity</span>
                    <span className="font-bold text-slate-700">{pat.activity}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Critical Barrier</span>
                    <span className="font-bold text-slate-700">{pat.barrier}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Occurrences</span>
                    <span className="font-extrabold text-purple-700 font-mono">{pat.occurrence_count} independent</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">SIF Potential</span>
                    <span className="font-extrabold text-red-600 font-mono">{pat.sif_potential}</span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 font-mono">
                  Linked Reports: {pat.source_reports?.slice(0, 4).join(', ')} {pat.source_reports?.length > 4 ? `+${pat.source_reports.length - 4} more` : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 5: REPORT EXPLORER */}
      {activeTab === 'EXPLORER' && runData && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search narratives, barriers, activities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-amber-500 outline-none"
              />
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto justify-end">
              <span className="text-slate-500 font-semibold">SIF Filter:</span>
              <select
                value={sifFilter}
                onChange={(e) => setSifFilter(e.target.value)}
                className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-bold text-slate-700 bg-white"
              >
                <option value="ALL">All Reports</option>
                <option value="HIGH">High SIF Potential</option>
                <option value="NON_SIF">Non-SIF</option>
                <option value="REVIEW_REQUIRED">Review Required</option>
              </select>
            </div>
          </div>

          {/* Paginated Reports Inspector Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="divide-y divide-slate-100">
              {filteredReports.slice(0, 50).map((r, idx) => (
                <div key={idx} className="p-4 hover:bg-slate-50/70 transition-colors space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                        {r.report_id}
                      </span>
                      <span className="font-bold text-slate-800">{r.activity}</span>
                      <span className="text-slate-400">•</span>
                      <span className="text-slate-500">{r.location || 'Site Perimeter'}</span>
                    </div>

                    <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase border ${
                      r.sif_potential === 'HIGH'
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : r.sif_potential === 'REVIEW_REQUIRED'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}>
                      {r.sif_potential}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 italic bg-slate-50 p-2.5 rounded border border-slate-200">
                    "{r.original_text}"
                  </p>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Hazard / Energy</span>
                      <span className="font-bold text-slate-700">{r.hazard}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Critical Barrier</span>
                      <span className="font-bold text-slate-700">{r.barrier}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Barrier State</span>
                      <span className="font-bold text-slate-700">{r.barrier_state}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[9px] uppercase font-bold">Life-Saving Rule</span>
                      <span className="font-bold text-blue-700">{r.lsr}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {filteredReports.length === 0 && (
              <div className="p-8 text-center text-xs text-slate-500">
                No reports matched the specified filters.
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
