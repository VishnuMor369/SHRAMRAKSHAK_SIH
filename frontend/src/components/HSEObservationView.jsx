import React, { useState } from 'react';
import { 
  FileText, 
  Brain, 
  History, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowLeft, 
  Download, 
  ExternalLink, 
  ShieldCheck, 
  Activity as ActivityIcon,
  Sparkles,
  MapPin,
  User
} from 'lucide-react';
import { createHSEObservation } from '../services/api';

export default function HSEObservationView({ status, onClose, onSelectAlert, onOpenAlerts }) {
  const [workerId, setWorkerId] = useState('W-104');
  const [activity, setActivity] = useState('Maintenance');
  const [location, setLocation] = useState('Compressor Area');
  const [hazard, setHazard] = useState('Energized equipment');
  const [observation, setObservation] = useState(
    'Worker was performing maintenance near energized equipment. Isolation was not verified before maintenance activity.'
  );
  const [notes, setNotes] = useState('Worker instructed to leave area until energy isolation verified.');
  const [linkedAlertId, setLinkedAlertId] = useState('');

  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [error, setError] = useState(null);

  const activeAlerts = status?.active_alerts || [];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!observation.trim()) {
      setError('Please enter a detailed safety observation description.');
      return;
    }
    try {
      setAnalyzing(true);
      setError(null);
      const res = await createHSEObservation({
        worker_identifier: workerId,
        activity,
        location,
        hazard,
        observation,
        notes,
        linked_alert_id: linkedAlertId || null,
        reviewer_role: 'HSE Manager'
      });
      setAnalysisResult(res.alert);
    } catch (err) {
      console.error('HSE observation analysis failed:', err);
      setError(err.message || 'Failed to submit observation for AI analysis.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setObservation('');
    setNotes('');
    setError(null);
  };

  const handleExportPdf = () => {
    window.open('/api/reports/export-pdf', '_blank');
  };

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-black bg-blue-100 text-blue-800 border border-blue-200 uppercase">
                DEDICATED HSE MODULE
              </span>
              <span className="text-xs font-mono text-slate-400">SIH PS 26165</span>
            </div>
            <h1 className="text-base font-black text-slate-900 tracking-tight uppercase mt-0.5 flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <span>HSE Manual Field Observation & SIF Intelligence Engine</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            onClick={handleExportPdf}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-amber-400 font-bold rounded-lg text-xs transition-all shadow flex items-center space-x-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>EXPORT PDF REPORT</span>
          </button>
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: OBSERVATION INPUT FORM */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2 text-slate-900">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <h2 className="text-xs font-black uppercase tracking-wider">
                Enter Field Safety Observation
              </h2>
            </div>
            {analysisResult && (
              <button
                onClick={handleReset}
                className="text-xs text-blue-600 font-bold hover:underline"
              >
                + New Observation
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Worker Identifier</label>
                <input
                  type="text"
                  value={workerId}
                  onChange={(e) => setWorkerId(e.target.value)}
                  placeholder="e.g. W-104"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:bg-white focus:border-slate-800 outline-none"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Activity</label>
                <input
                  type="text"
                  value={activity}
                  onChange={(e) => setActivity(e.target.value)}
                  placeholder="e.g. Maintenance / Lifting"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:bg-white focus:border-slate-800 outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Location / Site</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Compressor Area"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:bg-white focus:border-slate-800 outline-none"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Observed Hazard</label>
                <input
                  type="text"
                  value={hazard}
                  onChange={(e) => setHazard(e.target.value)}
                  placeholder="e.g. Energized equipment"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-900 focus:bg-white focus:border-slate-800 outline-none"
                />
              </div>
            </div>

            <div className="text-xs">
              <label className="font-bold text-slate-700 block mb-1">
                Detailed Observation / Unsafe Act / Near-Miss Narrative *
              </label>
              <textarea
                rows={4}
                value={observation}
                onChange={(e) => setObservation(e.target.value)}
                placeholder="Write detailed safety observation text..."
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:bg-white focus:border-slate-800 outline-none leading-relaxed"
                required
              />
            </div>

            <div className="text-xs">
              <label className="font-bold text-slate-700 block mb-1">Additional HSE Notes (Optional)</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Work stopped until energy isolation verified"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:bg-white focus:border-slate-800 outline-none"
              />
            </div>

            {/* Optional CCTV Incident Link */}
            {activeAlerts.length > 0 && (
              <div className="text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
                <label className="font-bold text-slate-700 block">Link to Active CCTV Incident (Optional)</label>
                <select
                  value={linkedAlertId}
                  onChange={(e) => setLinkedAlertId(e.target.value)}
                  className="w-full px-2 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-800"
                >
                  <option value="">-- None (Create Standalone HSE Incident SR-2026-XXXX) --</option>
                  {activeAlerts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.incident_id || a.id} — {a.type} ({a.location})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs font-bold">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={analyzing}
              className="w-full py-3 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-amber-400 font-black rounded-xl text-xs transition-all shadow-md flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Brain className="w-4 h-4 text-amber-400" />
              <span>{analyzing ? 'Executing AI/NLP SIF Pipeline...' : 'ANALYZE & SUBMIT OBSERVATION'}</span>
            </button>
          </form>
        </div>

        {/* RIGHT COLUMN: AI ANALYTICS RESULTS PANEL */}
        <div className="lg:col-span-7 space-y-5">
          {!analysisResult ? (
            /* EMPTY / NO DATA STATE */
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 mx-auto">
                <Brain className="w-7 h-7" />
              </div>
              <div className="max-w-md mx-auto space-y-2">
                <h3 className="text-sm font-black text-slate-900 uppercase tracking-tight">
                  Write a safety observation to begin AI/NLP analysis.
                </h3>
                <p className="text-xs text-slate-500 font-medium leading-relaxed">
                  Every submitted HSE observation is processed through the Campbell SIF risk pathway matrix, mapped against IOGP Life-Saving Rules, and correlated with historical OIL safety report patterns.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 max-w-lg mx-auto pt-4 text-[11px] font-bold text-slate-600">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  ⚡ SIF Precursor Detection
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  🛡️ IOGP Rule Classification
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                  📊 Historical Pattern Match
                </div>
              </div>
            </div>
          ) : (
            /* ACTIVE NLP ANALYSIS RESULT PANEL */
            <div className="space-y-4">
              {/* Incident Header & Source Banner */}
              <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-lg border border-slate-800 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2.5 py-1 rounded-md text-xs font-mono font-black bg-amber-500 text-slate-950 border border-amber-400">
                      INCIDENT {analysisResult.incident_id || analysisResult.id}
                    </span>
                    <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-900 text-blue-200 border border-blue-700">
                      SOURCE: {analysisResult.source || 'HSE + NLP'}
                    </span>
                  </div>

                  <span className={`px-3 py-1 rounded-md text-xs font-black uppercase tracking-wider ${
                    analysisResult.nlp_sif_potential ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                  }`}>
                    SIF POTENTIAL: {analysisResult.nlp_sif_potential ? 'HIGH / POTENTIAL' : 'LOW'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Risk Score</span>
                    <span className="text-base font-black text-amber-400 font-mono">
                      {analysisResult.nlp_risk_score || 50}/100
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Risk Level</span>
                    <span className="text-sm font-bold text-white uppercase">
                      {analysisResult.nlp_risk_level || 'MEDIUM'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Confidence</span>
                    <span className="text-sm font-bold text-emerald-400 font-mono">
                      {analysisResult.nlp_confidence || 85}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold block uppercase">Worker ID</span>
                    <span className="text-sm font-bold text-slate-200 font-mono">
                      {analysisResult.worker_identifier || 'W-104'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 1. EXTRACTED NLP ENTITIES CARD */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3.5 shadow-sm text-xs">
                <div className="flex items-center space-x-2 text-slate-900 font-black uppercase tracking-wider border-b border-slate-100 pb-2">
                  <Brain className="w-4 h-4 text-purple-600" />
                  <span>NLP SIF PRECURSOR EXTRACTION</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Extracted Activity</span>
                    <span className="font-bold text-slate-900">{analysisResult.nlp_activity || analysisResult.hse_activity}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Extracted Hazard</span>
                    <span className="font-bold text-slate-900">{analysisResult.nlp_hazard || analysisResult.hse_observed_hazard}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Extracted Location</span>
                    <span className="font-bold text-slate-900">{analysisResult.nlp_location || analysisResult.hse_location}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Barrier Failure</span>
                    <span className="font-bold text-red-600 block bg-red-50 p-2 rounded-lg border border-red-200">
                      ⚠️ {analysisResult.nlp_barrier_failure || 'Energy isolation not verified'}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">SIF Precursor Signature</span>
                    <span className="font-bold text-amber-700 block bg-amber-50 p-2 rounded-lg border border-amber-200">
                      ⚡ {analysisResult.nlp_precursor || 'Unverified Energy Isolation'}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">IOGP Life-Saving Rules</span>
                    <div className="flex flex-wrap gap-1.5">
                      {(analysisResult.nlp_life_saving_rules || ['Energy Isolation']).map((rule, idx) => (
                        <span key={idx} className="px-2.5 py-1 rounded-md text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                          {rule}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {analysisResult.nlp_reasoning && analysisResult.nlp_reasoning.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Explainable AI Reasoning</span>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-700 font-medium">
                      {analysisResult.nlp_reasoning.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 2. HISTORICAL DATASET PATTERN ANALYSIS CARD */}
              <div className={`rounded-2xl border p-5 space-y-3 text-xs shadow-sm ${
                analysisResult.has_historical_match 
                  ? 'bg-amber-50/80 border-amber-300 text-amber-950' 
                  : 'bg-white border-slate-200 text-slate-700'
              }`}>
                <div className="flex items-center justify-between border-b border-amber-200 pb-2">
                  <div className="flex items-center space-x-2 font-black uppercase tracking-wider text-amber-950">
                    <History className="w-4 h-4 text-amber-700" />
                    <span>HISTORICAL PRECURSOR PATTERN MATCH (Active OIL Dataset)</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-amber-800">
                    January2015toNovember2025.csv
                  </span>
                </div>

                {analysisResult.has_historical_match ? (
                  <div className="space-y-3">
                    <p className="font-semibold text-amber-900">
                      Recurring SIF precursor pattern matched against active safety report dataset:
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-white p-3 rounded-xl border border-amber-300 font-mono">
                      <div>
                        <span className="text-[9px] font-sans font-bold text-slate-400 block uppercase">Matching Pattern</span>
                        <span className="font-bold text-slate-900 text-[11px]">{analysisResult.historical_pattern_title}</span>
                      </div>
                      <div>
                        <span className="text-[9px] font-sans font-bold text-slate-400 block uppercase">Occurrences</span>
                        <span className="font-bold text-slate-900 text-[11px]">{analysisResult.historical_occurrence_count} reports</span>
                      </div>
                      <div>
                        <span className="text-[9px] font-sans font-bold text-slate-400 block uppercase">SIF Reports</span>
                        <span className="font-bold text-red-600 text-[11px]">{analysisResult.historical_sif_count}</span>
                      </div>
                      <div>
                        <span className="text-[9px] font-sans font-bold text-slate-400 block uppercase">SIF Density</span>
                        <span className="font-bold text-amber-700 text-[11px]">{analysisResult.historical_sif_density_pct}%</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-center font-bold text-slate-500">
                    NO HISTORICAL MATCH FOUND
                  </div>
                )}
              </div>

              {/* 3. QUICK NAVIGATION & PDF REPORT ACTIONS */}
              <div className="flex items-center justify-between gap-3 pt-2">
                <button
                  onClick={() => {
                    if (onSelectAlert) onSelectAlert(analysisResult);
                    if (onOpenAlerts) onOpenAlerts();
                  }}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl text-xs transition-all flex items-center space-x-1.5 shadow"
                >
                  <span>VIEW IN MAIN ALERTS</span>
                  <ExternalLink className="w-3.5 h-3.5 text-amber-400" />
                </button>

                <button
                  onClick={handleExportPdf}
                  className="px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black rounded-xl text-xs transition-all shadow flex items-center space-x-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>DOWNLOAD HSE PDF REPORT</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
