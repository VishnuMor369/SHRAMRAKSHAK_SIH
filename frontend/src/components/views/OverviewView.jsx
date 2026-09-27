import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Database, 
  CheckCircle2, 
  ArrowRight, 
  Clock, 
  AlertTriangle, 
  Video,
  FileCheck,
  RefreshCw,
  Eye,
  Layers,
  MapPin,
  ExternalLink
} from 'lucide-react';
import { fetchSafetyMemorySummary, fetchUnifiedEventSummary, fetchUnifiedEvents } from '../../services/api';
import EvidenceDetailDrawer from '../EvidenceDetailDrawer';

export default function OverviewView({ status, onNavigate, onSelectAlert }) {
  const [memorySummary, setMemorySummary] = useState(null);
  const [eventSummary, setEventSummary] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const activeAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);
  const criticalAlerts = activeAlerts.filter(a => a.severity === 'CRITICAL' || a.sif_potential || a.sif_level === 'HIGH');
  const awaitingVerificationAlerts = activeAlerts.filter(
    a => a.verification_status === 'AWAITING_VERIFICATION' || a.lifecycle_state === 'AWAITING_VERIFICATION'
  );

  const loadData = async () => {
    setLoading(true);
    try {
      const [memData, evSum, evList] = await Promise.all([
        fetchSafetyMemorySummary().catch(() => null),
        fetchUnifiedEventSummary().catch(() => null),
        fetchUnifiedEvents({ limit: 6 }).catch(() => [])
      ]);
      setMemorySummary(memData);
      setEventSummary(evSum);
      setRecentEvents(Array.isArray(evList) ? evList : (evList?.events || []));
    } catch (err) {
      console.error('Failed to load overview data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [status]);

  const handleInspectEvent = (event) => {
    setSelectedEvent(event);
    setIsDrawerOpen(true);
  };

  const sifPotentialCount = eventSummary?.sif_potential_count ?? (memorySummary?.sif_potential_count ?? 0);
  const recurringPatternsCount = eventSummary?.recurring_patterns_count ?? (memorySummary?.pattern_count ?? (memorySummary?.patterns?.length || 0));
  const awaitingVerificationCount = eventSummary?.awaiting_verification_count ?? awaitingVerificationAlerts.length;

  const isZoneClear = status?.zone_status === 'CLEAR' && activeAlerts.length === 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Page Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              HOME • OPERATIONAL COMMAND
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Drilling Rig 04 — Active Safety Watch
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-1">
            Safety Command Overview
          </h1>
        </div>

        {/* Node Health Status */}
        <div className="flex items-center space-x-3 bg-white px-3.5 py-2 rounded-xl border border-slate-200 shadow-sm text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-bold text-slate-700">Vision Edge: {status?.camera_name || 'C-01'}</span>
          </div>
          <span className="text-slate-300">|</span>
          <div className="text-slate-600 font-mono text-[11px]">
            NLP SIF: <span className="font-bold text-slate-900">Active</span>
          </div>
          <span className="text-slate-300">|</span>
          <button 
            onClick={loadData}
            disabled={loading}
            className="text-slate-500 hover:text-slate-900 transition-colors p-0.5"
            title="Refresh operational data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-amber-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* 2. Top 4 Calm KPI Metrics (Section 5) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1: SIF Potential Precursors */}
        <div 
          onClick={() => onNavigate('INTELLIGENCE')}
          className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-red-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">SIF Potential</span>
            <span className={`p-1.5 rounded-lg ${sifPotentialCount > 0 ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-400'}`}>
              <ShieldAlert className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {sifPotentialCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className={sifPotentialCount > 0 ? 'text-red-600 font-semibold' : 'text-slate-500'}>
              {sifPotentialCount > 0 ? 'Fatal precursor risks identified' : 'Zero fatal potential flagged'}
            </span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-red-600 transition-colors" />
          </div>
        </div>

        {/* KPI 2: Open Safety Alerts */}
        <div 
          onClick={() => onNavigate('ACTIONS')}
          className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-amber-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Open Safety Alerts</span>
            <span className={`p-1.5 rounded-lg ${activeAlerts.length > 0 ? 'bg-amber-50 text-amber-600' : 'bg-slate-50 text-slate-400'}`}>
              <AlertTriangle className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {activeAlerts.length}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className={activeAlerts.length > 0 ? 'text-amber-700 font-semibold' : 'text-emerald-700 font-semibold'}>
              {activeAlerts.length > 0 ? `${criticalAlerts.length} critical / action required` : 'All perimeter zones secure'}
            </span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-amber-600 transition-colors" />
          </div>
        </div>

        {/* KPI 3: Active Recurring Patterns */}
        <div 
          onClick={() => onNavigate('SAFETY MEMORY')}
          className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-purple-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Recurring Patterns</span>
            <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
              <Database className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {recurringPatternsCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="text-purple-700 font-semibold">Safety Memory discovery</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-purple-600 transition-colors" />
          </div>
        </div>

        {/* KPI 4: Awaiting Verification */}
        <div 
          onClick={() => onNavigate('ACTIONS')}
          className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-blue-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Awaiting Verification</span>
            <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {awaitingVerificationCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="text-blue-700 font-semibold">"Completion is not proof"</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-colors" />
          </div>
        </div>
      </div>

      {/* 3. CURRENT SAFETY STATUS (Section 5) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2.5">
            <span className={`w-3 h-3 rounded-full ${isZoneClear ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`}></span>
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Current Safety Status
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Field Camera: {status?.camera_name || 'C-01 (Laptop Webcam)'}
          </span>
        </div>

        {/* Condition Banner */}
        {isZoneClear ? (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-emerald-950">
                  ALL MONITORED ZONES CLEAR
                </div>
                <p className="text-xs text-emerald-800 mt-0.5">
                  Zero active restricted-zone breaches or SIF precursor conditions reported by Computer Vision or Field Supervisors.
                </p>
              </div>
            </div>
            <button
              onClick={() => onNavigate('LIVE SAFETY')}
              className="px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs shrink-0 self-start sm:self-auto transition-colors shadow-sm"
            >
              Open Live Video Feed →
            </button>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-red-50 border border-red-300 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping"></span>
                <span className="text-xs font-black uppercase bg-red-600 text-white px-2 py-0.5 rounded">
                  SIF POTENTIAL ACTIVE
                </span>
                <span className="text-xs font-bold text-red-950">
                  Worker entered lifting exclusion zone
                </span>
              </div>
              <button
                onClick={() => onNavigate('ACTIONS')}
                className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded shadow-sm self-start sm:self-auto transition-colors"
              >
                Respond & Verify Alert →
              </button>
            </div>

            {activeAlerts.length > 0 && (
              <div className="space-y-2 pt-1">
                {activeAlerts.map(alert => (
                  <div 
                    key={alert.id || alert.event_id}
                    onClick={() => onSelectAlert ? onSelectAlert(alert) : onNavigate('ACTIONS')}
                    className="p-3 rounded-lg bg-white border border-red-200 hover:border-red-300 cursor-pointer flex items-center justify-between text-xs transition-all shadow-xs"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="font-mono font-bold text-red-700">{alert.event_id || alert.id}</span>
                      <span className="text-slate-800 font-semibold">{alert.title || alert.type || 'Restricted Zone Violation'}</span>
                      <span className="text-slate-500 text-[11px]">Location: {alert.location || 'Lifting Zone 03'}</span>
                    </div>
                    <span className="font-bold text-amber-700 flex items-center gap-1">
                      Inspect Alert <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quick Context Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Active Zone</span>
            <span className="font-bold text-slate-800 text-xs mt-0.5 block truncate">
              {status?.active_zone?.name || 'ZONE-001 (Compressor Area)'}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Zone Category</span>
            <span className="font-bold text-slate-800 text-xs mt-0.5 block">
              {status?.active_zone?.zone_category || 'PERMANENT'}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Safety Passport</span>
            <span className={`font-bold text-xs mt-0.5 block ${status?.active_passport?.status === 'ACTIVE' ? 'text-emerald-700' : 'text-slate-600'}`}>
              {status?.active_passport?.status || 'NO ACTIVE PASSPORT'}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] text-slate-400 font-bold block uppercase">Persons in Zone</span>
            <span className={`font-mono font-bold text-xs mt-0.5 block ${status?.persons_in_zone > 0 ? 'text-red-600' : 'text-emerald-700'}`}>
              {status?.persons_in_zone || 0} Detected
            </span>
          </div>
        </div>
      </div>

      {/* 4. RECENT SAFETY ACTIVITY (Section 5) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-amber-600" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
              Recent Safety Activity & Events
            </h2>
          </div>
          <button
            onClick={() => onNavigate('REPORTS')}
            className="text-xs font-bold text-amber-600 hover:text-amber-700 transition-colors flex items-center gap-1"
          >
            <span>Open All Reports</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentEvents.length === 0 ? (
          <div className="text-center py-8 text-slate-400 space-y-2">
            <Clock className="w-8 h-8 mx-auto text-slate-300" />
            <p className="text-xs font-semibold">No recent safety events recorded yet.</p>
            <p className="text-[11px]">Submit a human safety report or ingest external datasets to view activity.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                  <th className="pb-2 font-mono">Event ID</th>
                  <th className="pb-2">Source</th>
                  <th className="pb-2">Observation / Narrative</th>
                  <th className="pb-2">Critical Barrier</th>
                  <th className="pb-2">SIF Potential</th>
                  <th className="pb-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentEvents.map(evt => {
                  const isSif = evt.sif_potential === 'HIGH' || evt.sif_potential === 'CRITICAL';
                  const isNegated = evt.assertion_status === 'NEGATED';

                  return (
                    <tr 
                      key={evt.event_id || evt.id}
                      onClick={() => handleInspectEvent(evt)}
                      className="hover:bg-slate-50 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 font-mono font-bold text-slate-700 whitespace-nowrap">
                        {evt.event_id || evt.id}
                      </td>
                      <td className="py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          evt.source === 'HUMAN' 
                            ? 'bg-blue-50 text-blue-800 border-blue-200'
                            : evt.source === 'CCTV'
                            ? 'bg-purple-50 text-purple-800 border-purple-200'
                            : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        }`}>
                          {evt.source || 'HUMAN'}
                        </span>
                      </td>
                      <td className="py-3 max-w-xs sm:max-w-md pr-4">
                        <p className="line-clamp-1 font-medium text-slate-900">
                          {evt.narrative || evt.raw_text || evt.title || evt.observed_event || 'Safety observation logged'}
                        </p>
                        <span className="text-[10px] text-slate-400 block mt-0.5">
                          {evt.location || 'Wellhead Deck'} • {evt.activity || 'Operations'}
                        </span>
                      </td>
                      <td className="py-3 text-slate-700 whitespace-nowrap">
                        <span className="text-xs font-semibold">
                          {evt.critical_barrier || 'Exclusion Perimeter'}
                        </span>
                      </td>
                      <td className="py-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${
                          isNegated 
                            ? 'bg-slate-100 text-slate-600 border-slate-200'
                            : isSif 
                            ? 'bg-red-50 text-red-700 border-red-200' 
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}>
                          {isNegated ? 'NEGATED' : (evt.sif_potential || 'NON-SIF')}
                        </span>
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleInspectEvent(evt);
                          }}
                          className="font-bold text-amber-600 group-hover:text-amber-700 text-xs inline-flex items-center gap-1"
                        >
                          <span>Evidence</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Persistent Evidence Drill-Down Drawer */}
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
