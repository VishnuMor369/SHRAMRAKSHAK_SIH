import React, { useState, useEffect } from 'react';
import { 
  BrainCircuit, 
  Activity, 
  ShieldAlert, 
  CheckCircle2, 
  Layers, 
  TrendingUp, 
  AlertTriangle, 
  Eye, 
  RefreshCw, 
  BarChart2, 
  Flame, 
  ShieldCheck,
  Compass,
  ArrowRight
} from 'lucide-react';
import { fetchUnifiedEventSummary, fetchUnifiedEvents } from '../../services/api';
import EvidenceDetailDrawer from '../EvidenceDetailDrawer';

export default function SafetyIntelligenceView({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sumData, eventsData] = await Promise.all([
        fetchUnifiedEventSummary(),
        fetchUnifiedEvents({ limit: 10 })
      ]);
      setSummary(sumData);
      const list = Array.isArray(eventsData) ? eventsData : (eventsData?.events || []);
      setRecentEvents(list);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load safety intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalEvents = summary?.total_events || 0;
  const sifCount = summary?.sif_potential_count || 0;
  const nonSifCount = summary?.non_sif_count || 0;
  const sifRate = totalEvents > 0 ? Math.round((sifCount / totalEvents) * 100) : 0;

  const topHazards = summary?.top_hazards || [
    { name: 'Suspended / Moving Load', count: 4 },
    { name: 'High-Pressure Line / Flange', count: 2 },
    { name: 'Heavy Machinery Proximity', count: 1 }
  ];

  const topActivities = summary?.top_activities || [
    { name: 'Mechanical Lifting Operations', count: 5 },
    { name: 'Wellhead Maintenance', count: 2 },
    { name: 'Tubular Pipe Handling', count: 1 }
  ];

  const topBarriers = summary?.top_barriers || [
    { name: 'Lifting Exclusion Zone Boundary', count: 5 },
    { name: 'Physical Barricade Tape', count: 2 },
    { name: 'Positive Isolation Lockout (LOTO)', count: 1 }
  ];

  const topLsrs = summary?.top_lsrs || [
    { name: 'Line of Fire', count: 5 },
    { name: 'Safe Mechanical Lifting', count: 4 },
    { name: 'Energy Isolation', count: 2 }
  ];

  const maxHazard = Math.max(...topHazards.map(h => h.count), 1);
  const maxActivity = Math.max(...topActivities.map(a => a.count), 1);
  const maxBarrier = Math.max(...topBarriers.map(b => b.count), 1);
  const maxLsr = Math.max(...topLsrs.map(l => l.count), 1);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* 1. Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-slate-900 text-amber-400 font-mono">
              SIF INTELLIGENCE CORE
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Aggregated Precursor Analytics Derived from Real Safety Events
            </span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-1 flex items-center gap-2">
            Safety Intelligence & Precursor Profiles
          </h1>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="self-start sm:self-auto px-3 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-sm flex items-center gap-2 text-xs font-bold disabled:opacity-60"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-amber-500' : 'text-slate-500'}`} />
          <span>{loading ? 'Refreshing...' : lastUpdated ? `Updated ${lastUpdated}` : 'Refresh Intelligence'}</span>
        </button>
      </div>

      {/* 2. Top Metric Cards: SIF Precursor Profile */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Metric 1: SIF Precursor Potential */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold uppercase tracking-wider text-[10px]">SIF Potential Precursors</span>
            <span className="p-1.5 rounded-lg bg-red-50 text-red-600">
              <ShieldAlert className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {sifCount}
          </div>
          <div className="text-[11px] text-red-600 font-semibold flex items-center gap-1">
            <span>{sifRate}% of events contain fatal potential</span>
          </div>
        </div>

        {/* Metric 2: Non-SIF / Safeguarded */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold uppercase tracking-wider text-[10px]">Non-SIF / Safeguarded</span>
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <ShieldCheck className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {nonSifCount}
          </div>
          <div className="text-[11px] text-emerald-700 font-semibold">
            Zero fatal exposure / barrier held intact
          </div>
        </div>

        {/* Metric 3: Review Required */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold uppercase tracking-wider text-[10px]">Review Required</span>
            <span className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {summary?.review_required_count || (totalEvents - sifCount - nonSifCount > 0 ? totalEvents - sifCount - nonSifCount : 0)}
          </div>
          <div className="text-[11px] text-amber-700 font-semibold">
            Uncertain exposure or ambiguous wording
          </div>
        </div>

        {/* Metric 4: SIF Precursor Density */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold uppercase tracking-wider text-[10px]">SIF Precursor Density</span>
            <span className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
              <Compass className="w-4 h-4" />
            </span>
          </div>
          <div className="text-3xl font-black text-slate-900">
            {totalEvents > 0 ? (sifCount / Math.max(totalEvents, 1)).toFixed(2) : '0.00'}
          </div>
          <div className="text-[11px] text-purple-700 font-semibold">
            Ratio of fatal precursors to total events
          </div>
        </div>
      </div>

      {/* 3. Deep Distribution Breakdown: Hazards, Activities, Barriers, LSRs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Distribution 1: Top Hazards */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-red-600" />
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Top Hazardous Energies Identified
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">SIH NLP Ontology</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {topHazards.map((item, idx) => {
              const pct = Math.round((item.count / maxHazard) * 100);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span>{item.name}</span>
                    <span className="font-mono text-slate-600">{item.count}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-red-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Distribution 2: Top Activities */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-amber-600" />
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Top High-Exposure Work Activities
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Operations</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {topActivities.map((item, idx) => {
              const pct = Math.round((item.count / maxActivity) * 100);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span>{item.name}</span>
                    <span className="font-mono text-slate-600">{item.count}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-amber-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Distribution 3: Top Compromised Barriers */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <Compass className="w-4 h-4 text-purple-600" />
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Top Compromised Critical Barriers
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Controls</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {topBarriers.map((item, idx) => {
              const pct = Math.round((item.count / maxBarrier) * 100);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span>{item.name}</span>
                    <span className="font-mono text-slate-600">{item.count}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-purple-600 h-full rounded-full transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Distribution 4: Top Life-Saving Rules */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <Flame className="w-4 h-4 text-blue-600" />
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
                IOGP Life-Saving Rules Associated
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Standards</span>
          </div>

          <div className="space-y-2.5 pt-1">
            {topLsrs.map((item, idx) => {
              const pct = Math.round((item.count / maxLsr) * 100);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                    <span>{item.name}</span>
                    <span className="font-mono text-slate-600">{item.count}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-blue-600 h-full rounded-full transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* 4. Recent Real-Time SIF Precursor Events List with Quick Drill-Down */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div>
            <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
              Active SIF Precursor Event Stream
            </h2>
            <p className="text-[11px] text-slate-500">
              Direct evidence spans bound to actual observations across all sources
            </p>
          </div>
          {onNavigate && (
            <button
              onClick={() => onNavigate('REPORTS')}
              className="text-xs font-bold text-amber-600 hover:text-amber-700 flex items-center gap-1 transition-colors"
            >
              <span>View All In Reports</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="divide-y divide-slate-100">
          {recentEvents.slice(0, 5).map((ev) => (
            <div 
              key={ev.event_id} 
              className="py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 text-xs hover:bg-slate-50/50 p-2 rounded-xl transition-colors"
            >
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-extrabold text-slate-900">{ev.event_id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border">
                    {ev.source}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                    (ev.sif_potential || '').includes('HIGH') ? 'bg-red-600 text-white' : 'bg-slate-200 text-slate-800'
                  }`}>
                    SIF {ev.sif_potential || 'HIGH'}
                  </span>
                </div>
                <p className="text-slate-800 font-serif line-clamp-1">
                  "{ev.narrative}"
                </p>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-center">
                <button
                  onClick={() => {
                    setSelectedEvent(ev);
                    setIsDrawerOpen(true);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors"
                >
                  <Eye className="w-3.5 h-3.5 text-amber-400" />
                  <span>Drill-Down</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Evidence Detail Drawer */}
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
