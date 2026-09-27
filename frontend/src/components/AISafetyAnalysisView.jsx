import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  BrainCircuit, 
  ArrowLeft, 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Activity, 
  RefreshCw, 
  MapPin, 
  Download, 
  ChevronRight,
  Upload,
  Database,
  BarChart3,
  TrendingUp,
  Layers,
  Target,
  FileSpreadsheet,
  Zap,
  CheckCircle2,
  Check,
  Search,
  FileText,
  AlertOctagon,
  Sparkles,
  PieChart
} from 'lucide-react';
import { 
  getExportPdfUrl,
  downloadExportPdf,
  uploadDatasetCsv,
  startDatasetProcessing,
  fetchDatasetStatus,
  fetchDatasetSummary,
  fetchDatasetReports,
  loadSampleDataset
} from '../services/api';
import SafetyReportDetailModal from './SafetyReportDetailModal';

export default function AISafetyAnalysisView({ status, onClose }) {
  // Active Tab inside Dataset Analysis: 'OVERVIEW' | 'PRECURSORS' | 'SIF_LSR' | 'FULL_REPORT'
  const [activeTab, setActiveTab] = useState('OVERVIEW');

  // Real Dataset Pipeline State
  const [datasetQuality, setDatasetQuality] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState(null);
  const [datasetSummary, setDatasetSummary] = useState(null);
  const [datasetReports, setDatasetReports] = useState([]);
  const [datasetTotal, setDatasetTotal] = useState(0);
  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetTotalPages, setDatasetTotalPages] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [datasetError, setDatasetError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDownloadPdf = async () => {
    try {
      setExportingPdf(true);
      setDatasetError(null);
      await downloadExportPdf();
    } catch (err) {
      setDatasetError(err.message || 'PDF Download failed');
    } finally {
      setExportingPdf(false);
    }
  };


  // Drill-down filter state
  const [drillDownFilter, setDrillDownFilter] = useState({
    status_filter: 'ALL',
    lsr_filter: '',
    precursor_filter: '',
    site_filter: '',
    activity_filter: '',
    search: ''
  });

  // Modal State
  const [selectedReport, setSelectedReport] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Poll dataset processing status
  useEffect(() => {
    let interval = null;
    if (processing || (pipelineStatus && pipelineStatus.status === 'PROCESSING')) {
      interval = setInterval(async () => {
        try {
          const st = await fetchDatasetStatus();
          setPipelineStatus(st);
          if (st.status === 'COMPLETED') {
            setProcessing(false);
            const sum = await fetchDatasetSummary();
            setDatasetSummary(sum);
            loadDatasetReportsPage(1, drillDownFilter);
          } else if (st.status === 'FAILED') {
            setProcessing(false);
            setDatasetError(st.error || 'Dataset processing failed');
          }
        } catch (e) {
          console.warn('Dataset status poll failed:', e);
        }
      }, 1000);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [processing, pipelineStatus, drillDownFilter]);

  // Load Dataset Reports page
  const loadDatasetReportsPage = async (pageNum = 1, filters = drillDownFilter) => {
    try {
      const res = await fetchDatasetReports({
        ...filters,
        page: pageNum,
        page_size: 15
      });
      setDatasetReports(res.reports || []);
      setDatasetTotal(res.total || 0);
      setDatasetPage(res.page || 1);
      setDatasetTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load dataset reports:', err);
    }
  };

  // Check initial dataset status on load
  useEffect(() => {
    async function initDataset() {
      try {
        const st = await fetchDatasetStatus();
        setPipelineStatus(st);
        if (st.dataset_info) {
          setDatasetQuality(st.dataset_info);
        }
        if (st.status === 'COMPLETED') {
          const sum = await fetchDatasetSummary();
          setDatasetSummary(sum);
          loadDatasetReportsPage(1, drillDownFilter);
        }
      } catch (err) {
        console.warn('Initial dataset fetch fallback:', err);
      }
    }
    initDataset();
  }, []);

  // Handle CSV File Upload
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      setDatasetError(null);
      const res = await uploadDatasetCsv(file);
      setDatasetQuality(res.quality_report);
      setPipelineStatus({ status: 'VALIDATED', progress: 0.1, dataset_info: res.quality_report });
      setDatasetSummary(null);
      setDatasetReports([]);
    } catch (err) {
      setDatasetError(err.message || 'CSV Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Handle Preset Dataset Load
  const handleLoadPresetSample = async () => {
    try {
      setUploading(true);
      setDatasetError(null);
      const res = await loadSampleDataset(2000);
      setDatasetQuality(res.quality_report);
      setProcessing(true);
    } catch (err) {
      setDatasetError(err.message || 'Failed to load preset sample dataset');
    } finally {
      setUploading(false);
    }
  };

  // Trigger SIF Analysis Pipeline
  const handleRunAnalysis = async () => {
    try {
      setProcessing(true);
      setDatasetError(null);
      await startDatasetProcessing(2000);
      const st = await fetchDatasetStatus();
      setPipelineStatus(st);
    } catch (err) {
      setProcessing(false);
      setDatasetError(err.message || 'Failed to start SIF Analysis');
    }
  };

  // Filter Handlers
  const handleApplyDrillDown = (key, value) => {
    const updated = { ...drillDownFilter, [key]: value };
    setDrillDownFilter(updated);
    loadDatasetReportsPage(1, updated);
  };

  const handleClearDrillDown = () => {
    const resetFilters = {
      status_filter: 'ALL',
      lsr_filter: '',
      precursor_filter: '',
      site_filter: '',
      activity_filter: '',
      search: ''
    };
    setDrillDownFilter(resetFilters);
    loadDatasetReportsPage(1, resetFilters);
  };

  // Handle Report Row Click
  const handleSelectReport = (report) => {
    setSelectedReport(report);
    setIsDetailModalOpen(true);
  };

  const pipelineStages = [
    { title: 'Dataset validation', done: (pipelineStatus?.progress || 0) >= 0.1 },
    { title: 'NLP preprocessing', done: (pipelineStatus?.progress || 0) >= 0.25 },
    { title: 'SIF classification', done: (pipelineStatus?.progress || 0) >= 0.4 },
    { title: 'Safety entity extraction', done: (pipelineStatus?.progress || 0) >= 0.55 },
    { title: 'Life-Saving Rule mapping', done: (pipelineStatus?.progress || 0) >= 0.7 },
    { title: 'Precursor detection', done: (pipelineStatus?.progress || 0) >= 0.8 },
    { title: 'SIF precursor density', done: (pipelineStatus?.progress || 0) >= 0.9 },
    { title: 'Site/activity prioritization', done: (pipelineStatus?.progress || 0) >= 0.95 },
    { title: 'HSE report generation', done: (pipelineStatus?.progress || 0) >= 1.0 },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      
      {/* Top Header */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-4 sm:px-8 py-3.5 shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 transition-colors"
              title="Return to Main Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base font-bold text-slate-900 tracking-tight">
                  SAFETY REPORT ANALYTICS
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 uppercase">
                  SIH PS 26165 • OIL INDIA
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in Safety & Near-Miss Reports
              </p>
            </div>
          </div>

          {datasetSummary && (
            <button
              onClick={handleDownloadPdf}
              disabled={exportingPdf}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 active:scale-[0.98] text-slate-700 text-xs font-semibold shadow-xs transition-all disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            >
              <Download className={`w-3.5 h-3.5 ${exportingPdf ? 'animate-spin text-blue-600' : ''}`} />
              <span>{exportingPdf ? 'Generating PDF...' : 'Export HSE PDF'}</span>
            </button>
          )}


        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 mt-6 space-y-6">

        {/* ========================================================================= */}
        {/* STEP 1: EMPTY STATE (BEFORE CSV UPLOAD / SELECTION)                       */}
        {/* ========================================================================= */}
        {!datasetQuality && !processing && (
          <section className="bg-white border border-slate-200 rounded-2xl p-10 text-center shadow-xs space-y-5 my-8">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto border border-blue-100 shadow-2xs">
              <FileSpreadsheet className="w-8 h-8" />
            </div>

            <div className="max-w-md mx-auto space-y-1.5">
              <h2 className="text-lg font-black text-slate-900">No Dataset Loaded</h2>
              <p className="text-xs text-slate-500 leading-relaxed">
                Upload an OIL safety-report CSV to perform SIF precursor classification, IOGP Life-Saving Rule mapping, recurring precursor detection, and site risk prioritization.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".csv"
                className="hidden"
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
              >
                <Upload className="w-4 h-4" />
                <span>{uploading ? 'Uploading...' : 'Upload CSV Dataset'}</span>
              </button>

              <button
                onClick={handleLoadPresetSample}
                disabled={uploading}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl border border-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-colors disabled:opacity-50"
              >
                <Zap className="w-4 h-4 text-amber-500" />
                <span>Load OIL Preset Dataset (105,996 Records)</span>
              </button>
            </div>

            {datasetError && (
              <div className="max-w-md mx-auto p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-700 flex items-center justify-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
                <span>{datasetError}</span>
              </div>
            )}
          </section>
        )}

        {/* ========================================================================= */}
        {/* STEP 2: DATASET HEALTH SUMMARY & RUN ANALYSIS CONTROLS                   */}
        {/* ========================================================================= */}
        {datasetQuality && (
          <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Dataset Loaded & Validated
                  </h2>
                  <p className="text-xs font-mono font-bold text-blue-700 mt-0.5">
                    {datasetQuality.file_name}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".csv"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || processing}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
                >
                  Change File
                </button>

                <button
                  onClick={handleRunAnalysis}
                  disabled={processing}
                  className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{processing ? 'Processing SIF Pipeline...' : 'RUN COMPLETE SIF ANALYSIS'}</span>
                </button>
              </div>
            </div>

            {/* Health Metrics Chips */}
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5 text-xs">
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold uppercase block">Total Records</span>
                <span className="text-base font-black font-mono text-slate-900">{datasetQuality.total_rows.toLocaleString()}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-emerald-600 font-bold uppercase block">Data Health Score</span>
                <span className="text-base font-black font-mono text-emerald-600">{datasetQuality.health_score}%</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-amber-600 font-bold uppercase block">Duplicates</span>
                <span className="text-base font-black font-mono text-amber-600">{datasetQuality.duplicate_rows}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase block">Missing Text</span>
                <span className="text-base font-black font-mono text-slate-700">{datasetQuality.missing_text_count}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase block">Missing Date</span>
                <span className="text-base font-black font-mono text-slate-700">{datasetQuality.missing_date_count}</span>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-500 font-bold uppercase block">Missing Location</span>
                <span className="text-base font-black font-mono text-slate-700">{datasetQuality.missing_location_count}</span>
              </div>
            </div>

            {/* Detected Column Badges */}
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] pt-1">
              <span className="font-bold text-slate-500 uppercase text-[10px]">Detected Fields:</span>
              <span className="bg-blue-50 text-blue-800 border border-blue-200 px-2 py-0.5 rounded font-mono font-medium">
                Narrative: {datasetQuality.detected_columns?.narrative_col || 'None'}
              </span>
              {datasetQuality.detected_columns?.date_col && (
                <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                  Date: {datasetQuality.detected_columns.date_col}
                </span>
              )}
              {datasetQuality.detected_columns?.location_col && (
                <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                  Site: {datasetQuality.detected_columns.location_col}
                </span>
              )}
              {datasetQuality.detected_columns?.activity_col && (
                <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                  Activity: {datasetQuality.detected_columns.activity_col}
                </span>
              )}
            </div>

            {/* STEP 3: PIPELINE EXECUTION PROGRESS */}
            {processing && (
              <div className="bg-blue-50/50 border border-blue-200 rounded-xl p-4 space-y-3">
                <div className="flex justify-between text-xs font-bold text-blue-900">
                  <span>Executing NLP & SIF Precursor Analysis Pipeline...</span>
                  <span className="font-mono">{Math.round((pipelineStatus?.progress || 0) * 100)}%</span>
                </div>
                
                <div className="w-full bg-blue-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2 transition-all duration-300 rounded-full"
                    style={{ width: `${(pipelineStatus?.progress || 0) * 100}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 text-[11px]">
                  {pipelineStages.map((stage, idx) => (
                    <div key={idx} className="flex items-center space-x-1.5 text-slate-600">
                      <span className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                        stage.done ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500'
                      }`}>
                        {stage.done ? '✓' : idx + 1}
                      </span>
                      <span className={stage.done ? 'font-semibold text-slate-900' : 'text-slate-400'}>
                        {stage.title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* ========================================================================= */}
        {/* STEP 4 & 5: EXECUTIVE SUMMARY & TABBED DETAILED ANALYSIS                  */}
        {/* ========================================================================= */}
        {datasetSummary && (
          <div className="space-y-6">

            {/* Executive Summary Cards */}
            <section className="grid grid-cols-2 sm:grid-cols-6 gap-3">
              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Reports Analysed</span>
                <div className="text-xl font-black text-slate-900 font-mono mt-0.5">
                  {datasetSummary.section_1_executive_summary.reports_analyzed.toLocaleString()}
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-600">SIF Potential</span>
                <div className="text-xl font-black text-red-600 font-mono mt-0.5">
                  {datasetSummary.section_1_executive_summary.sif_density_pct}%
                </div>
                <span className="text-[10px] text-slate-400 block">{datasetSummary.section_1_executive_summary.sif_potential_count.toLocaleString()} reports</span>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Non-SIF Potential</span>
                <div className="text-xl font-black text-emerald-600 font-mono mt-0.5">
                  {(100 - datasetSummary.section_1_executive_summary.sif_density_pct).toFixed(1)}%
                </div>
                <span className="text-[10px] text-slate-400 block">{datasetSummary.section_1_executive_summary.non_sif_count.toLocaleString()} reports</span>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Highest Priority Site</span>
                <div className="text-xs font-black text-slate-900 line-clamp-1 mt-1">
                  {datasetSummary.section_1_executive_summary.top_site}
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Top Hazard Activity</span>
                <div className="text-xs font-black text-slate-900 line-clamp-1 mt-1">
                  {datasetSummary.section_1_executive_summary.top_activity}
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600">Top Recurring Precursor</span>
                <div className="text-xs font-black text-slate-900 line-clamp-1 mt-1">
                  {datasetSummary.section_1_executive_summary.top_precursor}
                </div>
              </div>
            </section>

            {/* TAB NAVIGATION BAR */}
            <div className="bg-white border border-slate-200 rounded-xl p-1.5 shadow-xs flex flex-wrap items-center gap-1">
              {[
                { id: 'OVERVIEW', label: '1. OVERVIEW', icon: BarChart3 },
                { id: 'PRECURSORS', label: '2. PRECURSOR INTELLIGENCE', icon: Layers },
                { id: 'SIF_LSR', label: '3. SIF / LIFE-SAVING RULES', icon: ShieldAlert },
                { id: 'FULL_REPORT', label: '4. COMPLETE HSE REPORT', icon: FileText },
              ].map(tab => {
                const IconComp = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                      activeTab === tab.id
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <IconComp className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* ========================================================================= */}
            {/* TAB 1: OVERVIEW                                                           */}
            {/* ========================================================================= */}
            {activeTab === 'OVERVIEW' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Risk Distribution */}
                  <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center space-x-2">
                      <PieChart className="w-4 h-4 text-blue-600" />
                      <span>Safety Event Risk Level Breakdown</span>
                    </h3>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-center text-xs">
                      <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
                        <span className="text-[10px] text-red-700 font-bold uppercase block">Critical</span>
                        <span className="text-lg font-black text-red-800 font-mono">
                          {datasetSummary.section_1_executive_summary.risk_distribution?.CRITICAL || 0}
                        </span>
                      </div>
                      <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg">
                        <span className="text-[10px] text-amber-700 font-bold uppercase block">High</span>
                        <span className="text-lg font-black text-amber-800 font-mono">
                          {datasetSummary.section_1_executive_summary.risk_distribution?.HIGH || 0}
                        </span>
                      </div>
                      <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
                        <span className="text-[10px] text-blue-700 font-bold uppercase block">Medium</span>
                        <span className="text-lg font-black text-blue-800 font-mono">
                          {datasetSummary.section_1_executive_summary.risk_distribution?.MEDIUM || 0}
                        </span>
                      </div>
                      <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-lg">
                        <span className="text-[10px] text-emerald-700 font-bold uppercase block">Low</span>
                        <span className="text-lg font-black text-emerald-800 font-mono">
                          {datasetSummary.section_1_executive_summary.risk_distribution?.LOW || 0}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* High Priority Recommendations */}
                  <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>HSE Immediate Action Priorities</span>
                    </h3>
                    
                    <div className="space-y-2">
                      {datasetSummary.section_9_action_priorities?.slice(0, 2).map((act, idx) => (
                        <div key={idx} className="p-3 bg-emerald-50/40 border border-emerald-200 rounded-lg text-xs space-y-1">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase">Priority {act.priority_rank} • {act.category}</span>
                          <h4 className="font-bold text-slate-900">{act.title}</h4>
                          <p className="text-[11px] text-slate-600 leading-snug">{act.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 2: PRECURSOR INTELLIGENCE                                            */}
            {/* ========================================================================= */}
            {activeTab === 'PRECURSORS' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Recurring Precursors */}
                  <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center space-x-2">
                      <Layers className="w-4 h-4 text-amber-600" />
                      <span>Recurring SIF Precursor Patterns (Activity + Location + Barrier Failure)</span>
                    </h3>
                    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                      {datasetSummary.section_4_recurring_precursors?.map((pat, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleApplyDrillDown('precursor_filter', pat.barrier_failure)}
                          className="p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-blue-50/50 cursor-pointer transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-900">{pat.title}</span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 font-mono">
                              {pat.sif_potential_count} SIF ({pat.sif_density_pct}%)
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-500 mt-1 flex justify-between">
                            <span>Activity: {pat.activity}</span>
                            <span>Occurrences: {pat.occurrences}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* Site Rankings */}
                  <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center space-x-2">
                      <MapPin className="w-4 h-4 text-red-600" />
                      <span>Site / Location Priority Rankings (by SIF Precursor Density)</span>
                    </h3>
                    <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                      {datasetSummary.section_5_site_rankings?.map((site, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleApplyDrillDown('site_filter', site.site_name)}
                          className="p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-blue-50/50 cursor-pointer transition-colors flex items-center justify-between"
                        >
                          <div>
                            <span className="text-xs font-bold text-slate-900">{site.site_name}</span>
                            <span className="text-[11px] text-slate-500 block">Dominant Precursor: {site.dominant_precursor}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-xs font-mono font-bold text-red-600 block">{site.sif_density_pct}% SIF Density</span>
                            <span className="text-[10px] text-slate-400">{site.sif_count} / {site.total_reports} reports</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 3: SIF / LIFE-SAVING RULES                                            */}
            {/* ========================================================================= */}
            {activeTab === 'SIF_LSR' && (
              <div className="space-y-6">
                
                {/* Ground Truth Model Metrics */}
                {datasetSummary.section_2_sif_analysis?.model_metrics?.has_ground_truth && (
                  <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                    <div className="flex items-center space-x-2">
                      <Target className="w-4 h-4 text-purple-600" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                        ML Model Validation Metrics (Evaluated on Actual Dataset Ground-Truth Labels)
                      </h3>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="bg-purple-50 border border-purple-200 p-3 rounded-lg text-center">
                        <span className="text-[10px] text-purple-700 font-bold uppercase block">Accuracy</span>
                        <span className="text-xl font-black text-purple-900 font-mono">{datasetSummary.section_2_sif_analysis.model_metrics.accuracy}%</span>
                      </div>
                      <div className="bg-purple-50 border border-purple-200 p-3 rounded-lg text-center">
                        <span className="text-[10px] text-purple-700 font-bold uppercase block">Precision</span>
                        <span className="text-xl font-black text-purple-900 font-mono">{datasetSummary.section_2_sif_analysis.model_metrics.precision}%</span>
                      </div>
                      <div className="bg-purple-50 border border-purple-200 p-3 rounded-lg text-center">
                        <span className="text-[10px] text-purple-700 font-bold uppercase block">Recall (Sensitivity)</span>
                        <span className="text-xl font-black text-purple-900 font-mono">{datasetSummary.section_2_sif_analysis.model_metrics.recall}%</span>
                      </div>
                      <div className="bg-purple-50 border border-purple-200 p-3 rounded-lg text-center">
                        <span className="text-[10px] text-purple-700 font-bold uppercase block">F1-Score</span>
                        <span className="text-xl font-black text-purple-900 font-mono">{datasetSummary.section_2_sif_analysis.model_metrics.f1_score}%</span>
                      </div>
                    </div>
                  </section>
                )}

                {/* IOGP Life-Saving Rules Matrix */}
                <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center space-x-2">
                    <ShieldAlert className="w-4 h-4 text-blue-600" />
                    <span>IOGP Life-Saving Rules Classification & SIF Density Matrix</span>
                  </h3>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    {datasetSummary.section_3_life_saving_rules?.map((item, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleApplyDrillDown('lsr_filter', item.rule)}
                        className="p-3 bg-slate-50 border border-slate-200 rounded-xl hover:border-blue-300 cursor-pointer transition-all"
                      >
                        <span className="text-xs font-bold text-slate-900 block">{item.rule}</span>
                        <div className="flex justify-between items-baseline mt-2 text-xs">
                          <span className="text-slate-500">{item.count} Reports</span>
                          <span className="font-mono font-bold text-red-600">{item.sif_density_pct}% SIF</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 4: COMPLETE HSE REPORT                                                */}
            {/* ========================================================================= */}
            {activeTab === 'FULL_REPORT' && (
              <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-6">
                <div className="border-b border-slate-200 pb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-black text-slate-900 uppercase tracking-wide">
                      Full 9-Section HSE Safety Intelligence Report
                    </h2>
                    <p className="text-xs text-slate-500">
                      Generated dynamically from dataset: <span className="font-mono font-bold text-blue-700">{datasetQuality?.file_name}</span>
                    </p>
                  </div>
                  <button
                    onClick={handleDownloadPdf}
                    disabled={exportingPdf}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white text-xs font-bold transition-all disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <Download className={`w-3.5 h-3.5 ${exportingPdf ? 'animate-spin' : ''}`} />
                    <span>{exportingPdf ? 'Generating PDF...' : 'Download Dossier PDF'}</span>
                  </button>

                </div>

                <div className="space-y-6 text-xs text-slate-700">
                  <div>
                    <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-1">Section 1 — Executive Summary</h3>
                    <p className="leading-relaxed text-slate-600">
                      Analyzed {datasetSummary.section_1_executive_summary.reports_analyzed.toLocaleString()} safety reports. Identified {datasetSummary.section_1_executive_summary.sif_potential_count.toLocaleString()} SIF potential precursors ({datasetSummary.section_1_executive_summary.sif_density_pct}% SIF density). Top risk location identified as {datasetSummary.section_1_executive_summary.top_site}.
                    </p>
                  </div>

                  <div>
                    <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-1">Section 4 — Top Recurring Precursor Patterns</h3>
                    <ul className="list-disc pl-4 space-y-1 text-slate-600">
                      {datasetSummary.section_4_recurring_precursors?.slice(0, 5).map((p, i) => (
                        <li key={i}><span className="font-bold text-slate-800">{p.title}</span> — {p.sif_potential_count} SIF events ({p.sif_density_pct}% density)</li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider mb-1">Section 9 — Action Priorities</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                      {datasetSummary.section_9_action_priorities?.map((act, idx) => (
                        <div key={idx} className="p-3 bg-emerald-50/50 border border-emerald-200 rounded-lg">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase block">Priority {act.priority_rank}</span>
                          <h4 className="font-bold text-slate-900 mt-0.5">{act.title}</h4>
                          <p className="text-[11px] text-slate-600 mt-1">{act.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* ========================================================================= */}
            {/* DRILL-DOWN TRACEABILITY REPORT TABLE                                      */}
            {/* ========================================================================= */}
            <section className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
              <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Report Drill-Down Traceability Table ({datasetTotal.toLocaleString()} Reports)
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Click any row to inspect original report narrative, extracted entities, and SIF reasoning.
                  </p>
                </div>

                {(drillDownFilter.lsr_filter || drillDownFilter.precursor_filter || drillDownFilter.site_filter || drillDownFilter.activity_filter) && (
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-amber-700 font-bold bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                      Filtered View
                    </span>
                    <button onClick={handleClearDrillDown} className="text-xs text-blue-600 font-bold underline">
                      Clear Filters
                    </button>
                  </div>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Report ID & Date</th>
                      <th className="py-3 px-4">Narrative Description</th>
                      <th className="py-3 px-4">Activity</th>
                      <th className="py-3 px-4">Location / Site</th>
                      <th className="py-3 px-4">Life-Saving Rule</th>
                      <th className="py-3 px-4">SIF Potential</th>
                      <th className="py-3 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {datasetReports.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-400">
                          No dataset reports match the current filters.
                        </td>
                      </tr>
                    ) : (
                      datasetReports.map((report) => (
                        <tr 
                          key={report.report_id}
                          onClick={() => handleSelectReport(report)}
                          className="hover:bg-blue-50/40 cursor-pointer transition-colors group"
                        >
                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className="font-mono text-[10px] text-blue-600 font-bold block">{report.report_id}</span>
                            <span className="text-[10px] text-slate-400">{report.timestamp}</span>
                          </td>

                          <td className="py-3 px-4 max-w-md">
                            <p className="font-medium text-slate-900 line-clamp-2 group-hover:text-blue-600 transition-colors">
                              {report.description}
                            </p>
                          </td>

                          <td className="py-3 px-4 text-slate-700 font-medium whitespace-nowrap">
                            {report.activity}
                          </td>

                          <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                            {report.location}
                          </td>

                          <td className="py-3 px-4 whitespace-nowrap">
                            {report.life_saving_rules?.[0] ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                                {report.life_saving_rules[0]}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[10px]">Unmapped</span>
                            )}
                          </td>

                          <td className="py-3 px-4 whitespace-nowrap">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              report.sif_potential ? 'bg-red-600 text-white' : 'bg-slate-100 text-slate-700'
                            }`}>
                              {report.sif_potential ? 'SIF YES' : 'SIF NO'}
                            </span>
                          </td>

                          <td className="py-3 px-4 text-right">
                            <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 inline" />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {datasetTotalPages > 1 && (
                <div className="p-3 border-t border-slate-200 flex items-center justify-between bg-slate-50 text-xs">
                  <span className="text-slate-500">
                    Page <span className="font-bold font-mono text-slate-800">{datasetPage}</span> of {datasetTotalPages} ({datasetTotal.toLocaleString()} total)
                  </span>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => loadDatasetReportsPage(datasetPage - 1)}
                      disabled={datasetPage <= 1}
                      className="px-3 py-1 bg-white border border-slate-200 rounded text-slate-700 disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => loadDatasetReportsPage(datasetPage + 1)}
                      disabled={datasetPage >= datasetTotalPages}
                      className="px-3 py-1 bg-white border border-slate-200 rounded text-slate-700 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </section>

          </div>
        )}

      </main>

      {/* Safety Report Detail Modal */}
      <SafetyReportDetailModal
        report={selectedReport}
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        onReviewUpdated={(updated) => {
          setSelectedReport(updated);
        }}
      />

    </div>
  );
}
