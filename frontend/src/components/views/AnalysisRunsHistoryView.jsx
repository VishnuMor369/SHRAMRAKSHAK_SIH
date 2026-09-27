import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, 
  Download, 
  Eye, 
  RefreshCw, 
  ArrowRight, 
  Clock, 
  ShieldAlert, 
  FileText,
  Database
} from 'lucide-react';
import { 
  fetchAnalysisRuns, 
  getAnalysisRunPdfUrl 
} from '../../services/api';

export default function AnalysisRunsHistoryView({ onSelectRun, onNavigate }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  const loadRuns = () => {
    setLoading(true);
    setErrorMsg('');
    fetchAnalysisRuns()
      .then(res => {
        setRuns(res.runs || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load analysis runs:', err);
        setErrorMsg('Failed to load analysis runs history.');
        setLoading(false);
      });
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleDownload = (e, runId) => {
    e.stopPropagation();
    window.open(getAnalysisRunPdfUrl(runId), '_blank');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              ANALYSIS RUN REGISTRY
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Persisted Dataset Intelligence History
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Analysis Runs History
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadRuns}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => onNavigate && onNavigate('IMPORT DATA')}
            className="px-3.5 py-1.5 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-sm transition-all"
          >
            + Upload New File
          </button>
        </div>
      </div>

      {/* 2. Runs List Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Recorded Runs ({runs.length})
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            Isolated Workspaces • Persisted on Disk
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {runs.map(run => (
            <div 
              key={run.run_id} 
              className="p-4 sm:p-5 hover:bg-slate-50/70 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center space-x-3">
                  <span className="font-mono font-extrabold text-slate-900 text-sm bg-slate-100 px-2 py-0.5 rounded">
                    {run.run_id}
                  </span>
                  <span className="font-bold text-slate-800 text-sm">
                    {run.filename}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
                    {run.file_type || 'CSV'}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {run.status || 'COMPLETED'}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 font-mono pt-1">
                  <span>Detected: <strong className="text-slate-700">{run.records_detected}</strong></span>
                  <span>•</span>
                  <span>Analyzed: <strong className="text-emerald-700">{run.records_analyzed}</strong></span>
                  <span>•</span>
                  <span>SIF Count: <strong className="text-red-600">{run.sif_count}</strong> ({run.sif_percentage}%)</span>
                  <span>•</span>
                  <span>Uploaded: {new Date(run.upload_time).toLocaleString()}</span>
                </div>

                <p className="text-[11px] text-slate-400 italic">
                  Provenance: {run.provenance || 'Uploaded Dataset'}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 shrink-0 self-start md:self-auto">
                <button
                  onClick={() => onSelectRun ? onSelectRun(run.run_id) : onNavigate('DATASET ANALYSIS')}
                  className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 rounded-lg shadow-sm transition-all"
                >
                  <Eye className="w-3.5 h-3.5 text-slate-500" />
                  <span>OPEN RUN</span>
                </button>

                <button
                  onClick={(e) => handleDownload(e, run.run_id)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-sm transition-all"
                >
                  <Download className="w-3.5 h-3.5 text-amber-400" />
                  <span>DOWNLOAD PDF</span>
                </button>
              </div>
            </div>
          ))}

          {runs.length === 0 && !loading && (
            <div className="p-8 text-center text-xs text-slate-500">
              No analysis runs recorded yet. Upload a CSV or PDF dataset to generate an Analysis Run.
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
