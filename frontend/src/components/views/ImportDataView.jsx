import React, { useState, useEffect, useRef } from 'react';
import { 
  FileSpreadsheet, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Play, 
  Layers, 
  Database, 
  ArrowRight, 
  HelpCircle,
  Clock,
  Sparkles,
  Info
} from 'lucide-react';
import { 
  uploadDatasetFile, 
  executeDatasetImport, 
  fetchDatasetImportStatus 
} from '../../services/api';

export default function ImportDataView({ onNavigate }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [statusData, setStatusData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [batchLimit, setBatchLimit] = useState(200);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  const loadStatus = async () => {
    try {
      const data = await fetchDatasetImportStatus();
      setStatusData(data);
      const isRunning = data?.state === 'PROCESSING' || data?.status === 'PROCESSING' || data?.state === 'PARSING' || data?.state === 'NORMALIZING';
      setIsProcessing(isRunning);
      if (data?.error) {
        setErrorMsg(data.error);
      }
    } catch (err) {
      console.error('Failed to fetch dataset import status:', err);
    }
  };

  useEffect(() => {
    loadStatus();
    pollingRef.current = setInterval(loadStatus, isProcessing ? 1000 : 2500);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [isProcessing]);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setErrorMsg('');
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await uploadDatasetFile(formData);
      setStatusData(res.status);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to upload dataset file');
    } finally {
      setUploading(false);
    }
  };

  const handleExecuteImport = async () => {
    setErrorMsg('');
    setIsProcessing(true);
    try {
      const res = await executeDatasetImport(batchLimit);
      if (res?.status) {
        setStatusData(prev => ({ ...prev, ...res }));
      }
      loadStatus();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to execute import batch');
      setIsProcessing(false);
    }
  };

  const progressPct = statusData?.progress != null
    ? Math.round(statusData.progress * 100)
    : (statusData?.total_records > 0 ? Math.round((statusData.processed_count / statusData.total_records) * 100) : 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              ENTERPRISE DATASET INGESTION
            </span>
            <span className="text-xs font-semibold text-slate-500">
              CSV • XLSX • JSON • PDF Normalization & SIF Pipeline
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            Import Safety Data
          </h1>
        </div>

        <button
          onClick={loadStatus}
          className="self-start sm:self-auto p-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-sm flex items-center gap-2 text-xs font-bold"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* 2. Drag-and-Drop & File Upload Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left 7 Cols: File Dropzone & Schema Mapping */}
        <div className="lg:col-span-7 space-y-4">
          <div 
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-amber-500 bg-white hover:bg-amber-50/20 rounded-2xl p-8 text-center cursor-pointer transition-all space-y-3 group shadow-sm"
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              accept=".csv,.xlsx,.xls,.json,.pdf" 
              className="hidden" 
            />

            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-600 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
              <UploadCloud className="w-6 h-6" />
            </div>

            <div>
              <p className="text-sm font-bold text-slate-800">
                {uploading ? 'Parsing and normalizing dataset...' : 'Click to upload or drag & drop company dataset'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supports CSV, XLSX, JSON, and PDF (scanned tables automatically extracted)
              </p>
            </div>

            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-mono text-slate-600">
              Preset available: <strong>January2015toNovember2025.csv</strong>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Normalization & Schema Guidance */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3 shadow-sm text-xs">
            <div className="flex items-center space-x-2 text-slate-800 font-extrabold uppercase tracking-wider text-[11px]">
              <Layers className="w-4 h-4 text-amber-500" />
              <span>Automatic Normalization Layer</span>
            </div>
            <p className="text-slate-600 leading-relaxed text-[11px]">
              The dataset importer automatically performs fuzzy column alignment across diverse oil & gas E&P naming standards:
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] font-mono">
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">narrative</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← description, details, incident</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">location</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← area, site, rig, unit, plant</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">activity</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← task, operation, work_type</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">timestamp</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← date, datetime, incident_date</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">hazard</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← hazard_type, danger, energy</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 block text-[9px] uppercase">Canonical:</span>
                <strong className="text-slate-800">consequence</strong>
                <span className="text-slate-500 block text-[10px] mt-0.5">← injury, severity, outcome</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right 5 Cols: Batch Processing Execution & Live Telemetry */}
        <div className="lg:col-span-5 space-y-4">
          
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Database className="w-4 h-4 text-emerald-600" />
                <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
                  Batch Execution & Progress
                </h2>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                statusData?.state === 'COMPLETED'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : statusData?.state === 'PARSING' || isProcessing
                  ? 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
                  : 'bg-slate-50 text-slate-700 border-slate-200'
              }`}>
                {statusData?.state || 'IDLE'}
              </span>
            </div>

            {/* Current Loaded File Details */}
            <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 text-[11px]">Active File:</span>
                <span className="font-mono font-bold text-slate-800 text-[11px]">
                  {statusData?.file_name || 'January2015toNovember2025.csv'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 text-[11px]">Total Raw Rows:</span>
                <span className="font-mono font-bold text-slate-900">
                  {statusData?.total_records || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 text-[11px]">Successfully Ingested:</span>
                <span className="font-mono font-bold text-emerald-700">
                  {statusData?.processed_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 text-[11px]">Flagged for Review:</span>
                <span className="font-mono font-bold text-amber-700">
                  {statusData?.failed_count || 0}
                </span>
              </div>
              {statusData?.stage && (
                <div className="flex items-center justify-between pt-1 border-t border-slate-200/60">
                  <span className="text-slate-500 text-[11px]">Current Stage:</span>
                  <span className="font-mono font-bold text-amber-600 text-[11px] truncate max-w-[200px]" title={statusData.stage}>
                    {statusData.stage}
                  </span>
                </div>
              )}
            </div>

            {/* Industrial Dataset Transparency Banner (Section 35) */}
            <div className="p-2.5 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-800 text-[10px] leading-tight">
              <strong>Data Transparency Notice:</strong> External industrial dataset used for prototype stress testing. OIL proprietary records were not available for development validation.
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  NLP Pipeline Progress
                </span>
                <span className="font-mono font-extrabold text-slate-900">
                  {statusData?.processed_count || 0} / {statusData?.total_records || 0} ({progressPct}%)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200">
                <div 
                  className="bg-amber-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>

            {/* Batch Limit Selector */}
            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-slate-600 font-semibold text-[11px]">Batch Limit per Run:</span>
              <select
                value={batchLimit}
                onChange={(e) => setBatchLimit(Number(e.target.value))}
                className="px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white font-mono text-xs font-bold text-slate-800 focus:outline-none"
              >
                <option value={100}>100 records</option>
                <option value={200}>200 records</option>
                <option value={500}>500 records</option>
                <option value={1000}>1,000 records</option>
              </select>
            </div>

            {/* Trigger Button */}
            <button
              onClick={handleExecuteImport}
              disabled={isProcessing}
              className="w-full py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-amber-400 font-extrabold text-xs shadow-md flex items-center justify-center gap-2 transition-all transform active:scale-95 disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                  <span>BATCH INGESTION IN PROGRESS...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 text-amber-400 fill-amber-400" />
                  <span>RUN NLP & SIF PIPELINE ON BATCH</span>
                </>
              )}
            </button>

            {/* Completion Navigation */}
            {statusData?.processed_count > 0 && (
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-emerald-700 font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Canonical Events Saved
                </span>
                <button
                  onClick={() => onNavigate && onNavigate('REPORTS')}
                  className="text-amber-600 hover:text-amber-700 font-bold flex items-center gap-1 transition-colors"
                >
                  <span>View In Reports</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

          {/* SIH Architectural Note */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-600 space-y-1.5 leading-relaxed">
            <div className="flex items-center gap-1.5 font-bold text-slate-800">
              <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
              <span>Phase 5 & 30 Compliance:</span>
            </div>
            <p>
              Imported records enter the exact same canonical <strong>SafetyEvent</strong> store as human reports and CCTV observations. Dashboard KPIs, Safety Intelligence charts, and Safety Memory recurrence counts derive organically from these real records.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}
