import React, { useState, useEffect } from 'react';
import { 
  Video, 
  ShieldAlert, 
  MapPin, 
  Camera, 
  CheckCircle2, 
  Send, 
  Layers, 
  Eye, 
  Sparkles,
  ArrowRight,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import CCTVPanel from '../CCTVPanel';
import { fetchCorroborationScenarios, evaluateCorroboration } from '../../services/api';

export default function LiveSafetyView({ status, onSelectAlert, onNavigate }) {
  const [selectedCamera, setSelectedCamera] = useState('C-01');
  const [isDrawingZone, setIsDrawingZone] = useState(false);
  
  // Corroboration State
  const [corroborationScenarios, setCorroborationScenarios] = useState([]);
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('lifting_exclusion_corroborated');
  const [corroborationResult, setCorroborationResult] = useState(null);
  const [corroborating, setCorroborating] = useState(false);

  const activeAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);
  const machineAlert = activeAlerts.find(a => a.source === 'CCTV' || a.machine_observation) || activeAlerts[0];

  useEffect(() => {
    fetchCorroborationScenarios()
      .then(data => {
        setCorroborationScenarios(data?.scenarios || []);
        if (data?.scenarios?.length > 0) {
          handleRunCorroboration(data.scenarios[0].key);
        }
      })
      .catch(err => console.error('Failed to load corroboration scenarios:', err));
  }, []);

  const handleRunCorroboration = async (key) => {
    setSelectedScenarioKey(key);
    try {
      setCorroborating(true);
      const res = await evaluateCorroboration({ scenario_key: key });
      setCorroborationResult(res);
    } catch (err) {
      console.error('Failed to evaluate corroboration:', err);
    } finally {
      setCorroborating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-blue-100 text-blue-900 border border-blue-200">
              VISION INTELLIGENCE NODE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              CCTV restricted-zone breach → Machine-generated safety observation
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Live Safety & Machine Observation
          </h1>
        </div>

        <div className="text-xs text-slate-500 max-w-sm sm:text-right">
          CCTV Role: <b className="text-blue-700">GENERATE</b> (Machine Observation) → <b className="text-purple-700">SUPPORT</b> (Dual Evidence) → <b className="text-emerald-700">VERIFY</b> (Restoration).
        </div>
      </div>

      {/* 2. Machine Observation Banner (If Active CCTV Breach Exists) */}
      {machineAlert ? (
        <div className="bg-slate-900 text-white rounded-xl p-5 border border-slate-800 shadow-md space-y-3 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2.5">
              <span className="w-3 h-3 rounded-full bg-red-500 animate-ping inline-block" />
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white mr-2">
                  MACHINE-GENERATED SAFETY OBSERVATION
                </span>
                <span className="text-xs font-mono font-bold text-amber-400">
                  {machineAlert.event_id || machineAlert.id}
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 rounded bg-purple-900 text-purple-200 border border-purple-700 text-[10px] font-mono font-bold flex items-center gap-1">
                <Send className="w-3 h-3 text-purple-300" />
                SENT TO SIF INTELLIGENCE
              </span>
              <button
                onClick={() => onSelectAlert(machineAlert)}
                className="px-3 py-1 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs rounded transition-colors"
              >
                Inspect Event →
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-300">
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block">Evidence Source</span>
              <span className="font-bold text-white mt-0.5 block">CCTV Vision Edge (Camera C-01)</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block">Observed Condition</span>
              <span className="font-bold text-red-400 mt-0.5 block">Person inside lifting exclusion zone</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block">Temporal Confirmation</span>
              <span className="font-mono text-emerald-400 mt-0.5 block">5-Frame Confirmed • Ground-Contact</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] uppercase font-bold block">SIF Assessment</span>
              <span className="font-bold text-red-300 mt-0.5 block">CRITICAL / HIGH POTENTIAL</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-950">
          <div className="flex items-center space-x-2">
            <Eye className="w-4 h-4 text-blue-600" />
            <span>
              <b>CCTV Edge Detection Active:</b> Evaluates 5-frame confirmation, ground-contact bottom-center coordinates, and automatic debouncing.
            </span>
          </div>
          <span className="font-mono text-[11px] font-bold text-blue-800">C-01 Online</span>
        </div>
      )}

      {/* 3. Main CCTV Panel (Preserving All Ground-Contact, Polygons, and Detection Logic) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Video className="w-4 h-4 text-slate-800" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Live Camera Feed & Safety Exclusion Zones
            </h2>
          </div>
          <span className="text-xs font-semibold text-slate-500">
            Node: C-01 (Rig 04 Pipe Deck)
          </span>
        </div>

        <CCTVPanel 
          status={status}
          isDrawingMode={isDrawingZone}
          setIsDrawingMode={setIsDrawingZone}
          selectedCamera={selectedCamera}
          onSelectCamera={setSelectedCamera}
          onSelectAlert={onSelectAlert}
        />
      </div>

      {/* 4. Section 12: Dual Evidence Corroboration Showcase */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-purple-600" />
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Multi-Source Evidence Corroboration Engine
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Corroborates Human Field Reports against CCTV Machine Observations without accusing workers.
            </p>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-bold">Scenario:</span>
            {corroborationScenarios.map(sc => (
              <button
                key={sc.key}
                onClick={() => handleRunCorroboration(sc.key)}
                className={`px-2.5 py-1 rounded text-xs font-bold border transition-colors ${
                  selectedScenarioKey === sc.key 
                    ? 'bg-purple-700 text-white border-purple-700' 
                    : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
                }`}
              >
                {sc.name}
              </button>
            ))}
          </div>
        </div>

        {/* Corroboration Comparison Card */}
        {corroborationResult && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                corroborationResult.status === 'CORROBORATED'
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : corroborationResult.status === 'CCTV_ONLY'
                  ? 'bg-blue-100 text-blue-800 border-blue-300'
                  : 'bg-amber-100 text-amber-800 border-amber-300'
              }`}>
                STATUS: {corroborationResult.status}
              </span>
              <span className="text-xs font-mono text-slate-500">
                Confidence: <b className="text-slate-900">{Math.round((corroborationResult.confidence || 0.95) * 100)}%</b>
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {/* Human Report Side */}
              <div className="bg-white p-3.5 rounded-lg border border-slate-200 space-y-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Human Field Safety Report
                </span>
                <p className="font-serif text-slate-800 italic">
                  "{corroborationResult.human_report_text || 'No human report filed for this event.'}"
                </p>
                <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                  Location: <b className="text-slate-700">{corroborationResult.human_location || 'Pipe Deck'}</b> • Time: <b className="text-slate-700">{corroborationResult.human_timestamp || '10:42'}</b>
                </div>
              </div>

              {/* CCTV Machine Evidence Side */}
              <div className="bg-white p-3.5 rounded-lg border border-slate-200 space-y-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  CCTV Machine Observation
                </span>
                <p className="font-serif text-slate-800 italic">
                  "{corroborationResult.cctv_observed_event || 'Person entered defined exclusion zone.'}"
                </p>
                <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                  Camera: <b className="text-slate-700">{corroborationResult.camera_id || 'C-01'}</b> • State: <b className="text-red-700">Breach Confirmed</b>
                </div>
              </div>
            </div>

            <div className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-700">
              <span className="font-bold text-slate-900 block mb-0.5">Corroboration Synthesis:</span>
              <p>{corroborationResult.corroboration_summary}</p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
