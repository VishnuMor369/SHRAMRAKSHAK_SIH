import React, { useState, useEffect } from 'react';
import { MapPin, Activity, TrendingUp, CheckCircle2, AlertTriangle, Eye } from 'lucide-react';
import { fetchAlertHistory } from '../services/api';
import { cn } from '@/lib/utils';

export default function SafetyOverviewCard({ status, alerts = [] }) {
  const [recentEvents, setRecentEvents] = useState([]);

  useEffect(() => {
    let isMounted = true;
    const loadRecent = async () => {
      try {
        const history = await fetchAlertHistory();
        if (isMounted && Array.isArray(history)) {
          setRecentEvents(history.slice(0, 3));
        }
      } catch (err) {
        if (isMounted && Array.isArray(status?.recent_events)) {
          setRecentEvents(status.recent_events.slice(0, 3));
        }
      }
    };

    loadRecent();
    const interval = setInterval(loadRecent, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [status]);

  const activeAlertsCount = alerts.length > 0 
    ? alerts.length 
    : (status?.active_alert ? 1 : 0);

  // 1. High Risk Areas derived dynamically from active alerts and configured zones
  const riskAreas = [];
  if (alerts.length > 0) {
    alerts.forEach(a => {
      const loc = a.location || 'Monitored Work Area';
      if (!riskAreas.find(r => r.name === loc)) {
        riskAreas.push({
          name: loc,
          status: 'Active Hazard',
          critical: a.severity === 'CRITICAL' || a.type?.includes('Zone')
        });
      }
    });
  }
  if (status?.active_zone?.name && !riskAreas.find(r => r.name === status.active_zone.name)) {
    riskAreas.push({
      name: status.active_zone.name,
      status: status.zone_violation ? 'Breach Active' : 'Monitored Perimeter',
      critical: status.zone_violation
    });
  }

  // 2. Recent observations
  const observations = recentEvents.length > 0
    ? recentEvents
    : (status?.recent_events?.length > 0 ? status.recent_events.slice(0, 3) : []);

  // 3. Risk trend state
  const isHighRisk = activeAlertsCount > 0;

  return (
    <div className="space-y-3 pt-1">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-black tracking-wider text-safety-dark uppercase">
          Safety Overview
        </h2>
        <span className="text-[11px] font-semibold text-slate-500">
          Live Shift Insights
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* CARD 1: HIGH-RISK AREAS */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div>
            <div className="flex items-center space-x-2 text-slate-500 mb-2.5">
              <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
                High-Risk Areas
              </span>
            </div>

            {riskAreas.length > 0 ? (
              <div className="space-y-2 mt-1">
                {riskAreas.slice(0, 2).map((area, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-slate-100 last:border-0">
                    <span className="font-bold text-safety-dark truncate pr-2">
                      {area.name}
                    </span>
                    <span className={cn(
                      'px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0 border',
                      area.critical 
                        ? 'bg-red-50 text-safety-crimson border-safety-crimson/30' 
                        : 'bg-slate-100 text-slate-700 border-slate-200'
                    )}>
                      {area.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-3 text-center">
                <p className="text-xs font-bold text-safety-dark">No High-Risk Areas</p>
                <p className="text-[11px] text-slate-400 mt-0.5">All monitored zones clear</p>
              </div>
            )}
          </div>

          <div className="text-[10px] text-slate-400 font-medium pt-2.5 border-t border-slate-100 mt-2">
            Dynamic camera-mapped zones
          </div>
        </div>

        {/* CARD 2: RECENT OBSERVATIONS */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div>
            <div className="flex items-center space-x-2 text-slate-500 mb-2.5">
              <Eye className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
                Recent Observations
              </span>
            </div>

            {observations.length > 0 ? (
              <div className="space-y-2 mt-1">
                {observations.slice(0, 2).map((obs, idx) => {
                  const title = obs.title || obs.type || obs.event || 'Safety observation';
                  const time = obs.created_at || obs.timestamp
                    ? new Date(obs.created_at || obs.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : 'Recent';
                  return (
                    <div key={idx} className="text-xs py-1 border-b border-slate-100 last:border-0">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-safety-dark truncate pr-2">
                          {title}
                        </span>
                        <span className="text-[10px] font-mono-timer text-slate-400 shrink-0 tabular-nums">
                          {time}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 block truncate">
                        Camera {obs.camera || 'C-01'} • {obs.status || 'Verified'}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-3 text-center">
                <p className="text-xs font-bold text-safety-dark">No Recent Incidents</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Continuous CCTV surveillance</p>
              </div>
            )}
          </div>

          <div className="text-[10px] text-slate-400 font-medium pt-2.5 border-t border-slate-100 mt-2">
            Real-time visual audit trail
          </div>
        </div>

        {/* CARD 3: RISK TREND */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div>
            <div className="flex items-center space-x-2 text-slate-500 mb-2.5">
              <TrendingUp className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
                Risk Trend
              </span>
            </div>

            <div className="mt-1">
              <div className="flex items-center space-x-2">
                <span className={cn(
                  'w-2.5 h-2.5 rounded-full shrink-0',
                  isHighRisk ? 'bg-safety-red' : 'bg-safety-emerald'
                )} />
                <span className={cn(
                  'text-sm font-black uppercase tracking-tight',
                  isHighRisk ? 'text-safety-crimson' : 'text-safety-emerald'
                )}>
                  {isHighRisk ? 'Elevated Risk' : 'Normal / Stable'}
                </span>
              </div>
              <p className="text-xs text-slate-600 font-medium mt-1">
                {isHighRisk 
                  ? `${activeAlertsCount} active ${activeAlertsCount === 1 ? 'alert requires' : 'alerts require'} supervisor action` 
                  : 'PPE & zone compliance within normal safety threshold'}
              </p>
            </div>
          </div>

          <div className="text-[10px] text-slate-400 font-medium pt-2.5 border-t border-slate-100 mt-2 flex items-center justify-between">
            <span>Shift Status</span>
            <span className="font-semibold text-slate-600">Active Surveillance</span>
          </div>
        </div>
      </div>
    </div>
  );
}
