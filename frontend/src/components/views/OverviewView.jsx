import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Database, 
  CheckCircle2, 
  ArrowRight, 
  Clock, 
  AlertTriangle, 
  Layers, 
  Video,
  FileCheck
} from 'lucide-react';
import { fetchSafetyMemorySummary, fetchUnifiedEventSummary } from '../../services/api';

export default function OverviewView({ status, onNavigate, onSelectAlert }) {
  const [memorySummary, setMemorySummary] = useState(null);
  const [eventSummary, setEventSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const activeAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);
  const criticalAlerts = activeAlerts.filter(a => a.severity === 'CRITICAL' || a.sif_potential || a.sif_level === 'HIGH');
  const awaitingVerificationAlerts = activeAlerts.filter(
    a => a.verification_status === 'AWAITING_VERIFICATION' || a.lifecycle_state === 'AWAITING_VERIFICATION'
  );

  useEffect(() => {
    fetchSafetyMemorySummary()
      .then(data => setMemorySummary(data))
      .catch(err => console.error('Failed to load memory summary in overview:', err));

    fetchUnifiedEventSummary()
      .then(data => setEventSummary(data))
      .catch(err => console.error('Failed to load event summary in overview:', err));
  }, [status]);

  const topPattern = memorySummary?.recurring_patterns?.[0] || {
    pattern_title: 'Exclusion-Zone Segregation Failure in Mechanical Lifting',
    independent_occurrences: 5,
    duplicate_count: 2,
    validation_status: 'CANDIDATE',
    critical_barrier: 'Lifting Exclusion Zone Boundary'
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header & Quick Architecture Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              SIH26165 • OIL INDIA
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Safety Intelligence & Learning Architecture
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1">
            Safety Command Overview
          </h1>
        </div>

        {/* Small System Status */}
        <div className="flex items-center space-x-3 bg-white px-3.5 py-2 rounded-xl border border-slate-200 shadow-sm text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-bold text-slate-700">Vision Node Online</span>
          </div>
          <span className="text-slate-300">|</span>
          <div className="text-slate-600 font-mono text-[11px]">
            NLP Engine: <span className="font-bold text-slate-900">Active</span>
          </div>
          <span className="text-slate-300">|</span>
          <div className="text-slate-600 font-mono text-[11px]">
            Memory Store: <span className="font-bold text-emerald-700">Synchronized</span>
          </div>
        </div>
      </div>

      {/* 2. Top Summary KPI Cards (Clean, Restrained) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Active Critical Alerts */}
        <div 
          onClick={() => onNavigate('ACTIONS')}
          className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-red-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Active Critical Alerts</span>
            <span className={`p-1.5 rounded-lg ${criticalAlerts.length > 0 ? 'bg-red-50 text-red-600' : 'bg-slate-50 text-slate-400'}`}>
              <ShieldAlert className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {criticalAlerts.length}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span>{criticalAlerts.length > 0 ? 'Immediate action required' : 'Perimeter nominal'}</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-red-600 transition-colors" />
          </div>
        </div>

        {/* Card 2: SIF Precursor Trend */}
        <div 
          onClick={() => onNavigate('SAFETY INTELLIGENCE')}
          className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-amber-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">SIF Precursors Detected</span>
            <span className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <Activity className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {eventSummary?.sif_potential_count ?? (memorySummary?.total_events || 6)}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="text-amber-700 font-semibold">Exclusion zone & LOTO precursors</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-amber-600 transition-colors" />
          </div>
        </div>

        {/* Card 3: Top Recurring Safety Pattern */}
        <div 
          onClick={() => onNavigate('SAFETY MEMORY')}
          className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-purple-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Safety Memory Patterns</span>
            <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
              <Database className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {eventSummary?.recurring_patterns_count ?? (memorySummary?.pattern_count || 2)}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span>{topPattern.independent_occurrences} independent occurrences</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-purple-600 transition-colors" />
          </div>
        </div>

        {/* Card 4: Actions Awaiting Verification */}
        <div 
          onClick={() => onNavigate('ACTIONS')}
          className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-blue-300 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px]">Awaiting Verification</span>
            <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {eventSummary?.awaiting_verification_count ?? awaitingVerificationAlerts.length}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 flex items-center justify-between">
            <span className="text-blue-700 font-semibold">"Completion is not proof"</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-colors" />
          </div>
        </div>
      </div>

      {/* 2.5 Unified Source Registry Banner */}
      {eventSummary && (
        <div className="bg-white px-4 py-3 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2 font-bold text-slate-700">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span>Unified Safety Event Pipeline:</span>
            <span className="font-mono text-slate-900">{eventSummary.total_events} Total Events Processed</span>
          </div>

          <div className="flex items-center space-x-3 text-[11px] font-mono">
            <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-bold">
              👤 Human: {eventSummary.source_breakdown?.HUMAN || 0}
            </span>
            <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-bold">
              📹 CCTV: {eventSummary.source_breakdown?.CCTV || 0}
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
              📄 Imported: {eventSummary.source_breakdown?.IMPORTED || 0}
            </span>
            <button
              onClick={() => onNavigate('REPORTS')}
              className="font-sans font-bold text-amber-600 hover:text-amber-700 ml-2"
            >
              Open Reports →
            </button>
          </div>
        </div>
      )}

      {/* 3. Two Focused Operational Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left 7 cols: Active Alerts & Response Priority */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-red-600" />
              <h2 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
                Active Operational Safety Alerts
              </h2>
            </div>
            <button 
              onClick={() => onNavigate('ACTIONS / VERIFICATION')}
              className="text-xs font-bold text-amber-600 hover:text-amber-700 transition-colors"
            >
              View All Lifecycle States →
            </button>
          </div>

          {activeAlerts.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <p className="text-sm font-bold text-slate-800">All Safety Zones Clear</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No active restricted-zone breaches or SIF precursor conditions currently reported by Vision or Field teams.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeAlerts.map(alert => (
                <div 
                  key={alert.id}
                  onClick={() => onSelectAlert(alert)}
                  className="bg-white p-4 rounded-xl border-l-4 border-l-red-500 border border-slate-200 shadow-sm hover:shadow-md transition-all cursor-pointer space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white">
                        SIF: {alert.sif_level || 'HIGH'}
                      </span>
                      <span className="font-mono text-xs font-bold text-slate-700">
                        {alert.event_id || alert.id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                        {alert.source || 'CCTV'}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200">
                      {alert.lifecycle_state || alert.status}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-xs font-extrabold text-slate-900 uppercase">
                      {alert.title || alert.type || 'Restricted Zone Violation'}
                    </h3>
                    <p className="text-xs text-slate-600 mt-0.5 line-clamp-1">
                      {alert.immediate_action || 'Stop lifting operations and secure exclusion perimeter immediately.'}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Location: <b className="text-slate-800">{alert.location || 'Lifting Zone 03'}</b></span>
                    <span className="font-semibold text-amber-600">Click for Evidence Drill-Down →</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right 5 cols: Top Recurring Control Pattern & Future-Work Learning */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-4 h-4 text-purple-600" />
              <h2 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider">
                Top Recurring Safety-Control Pattern
              </h2>
            </div>
            <button 
              onClick={() => onNavigate('SAFETY MEMORY')}
              className="text-xs font-bold text-purple-600 hover:text-purple-700 transition-colors"
            >
              Open Memory →
            </button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-purple-100 text-purple-900 border border-purple-200 inline-block mb-1.5">
                  RECURRING CONTROL PATTERN
                </span>
                <h3 className="text-xs font-extrabold text-slate-900 leading-snug">
                  {topPattern.pattern_title}
                </h3>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${
                topPattern.validation_status === 'HSE_VALIDATED' 
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                  : 'bg-amber-100 text-amber-800 border-amber-300'
              }`}>
                {topPattern.validation_status === 'HSE_VALIDATED' ? '✓ HSE VALIDATED' : 'CANDIDATE PATTERN'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Occurrences</span>
                <span className="text-base font-black text-slate-900 mt-0.5 block">
                  {topPattern.independent_occurrences} independent
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  ({topPattern.duplicate_count || 0} duplicates filtered)
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block uppercase">Critical Barrier</span>
                <span className="text-xs font-bold text-slate-900 mt-0.5 block leading-tight">
                  {topPattern.critical_barrier || 'Exclusion Zone Segregation'}
                </span>
              </div>
            </div>

            <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs space-y-1">
              <span className="font-bold text-amber-900 block text-[11px] uppercase tracking-wider">
                Future-Work Precondition Applied:
              </span>
              <p className="text-slate-700 leading-tight">
                Mandatory physical barrier check & independent zone verification required before any lifting authorization.
              </p>
            </div>

            <button 
              onClick={() => onNavigate('SAFETY MEMORY')}
              className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow transition-colors flex items-center justify-center space-x-1.5"
            >
              <span>Inspect Memory & Validate Pattern</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Demo Phase Switcher Prompt */}
          <div className="bg-slate-900 text-white p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold text-amber-400 uppercase">
                SIH 2026 Judge Demonstration
              </span>
              <span className="text-[10px] text-slate-400">9-Phase Complete Flow</span>
            </div>
            <p className="text-xs text-slate-300">
              Run the full end-to-end lifecycle: Safety Intelligence → Safety Memory → Live CCTV Observation → Mobile Alert → Verification → Safety Memory Update.
            </p>
            <button
              onClick={() => onNavigate('SETTINGS / DEMO')}
              className="w-full py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-xs rounded-lg transition-colors"
            >
              Open Storyboard & Demo Controls →
            </button>
          </div>

        </div>

      </div>

    </div>
  );
}
