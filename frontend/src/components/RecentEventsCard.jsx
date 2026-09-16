import React, { useState, useEffect } from 'react';
import { History, CheckCircle2, AlertOctagon, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { fetchAlertHistory } from '../services/api';

export default function RecentEventsCard({ activeAlerts = [] }) {
  const [historyEvents, setHistoryEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const data = await fetchAlertHistory();
        if (Array.isArray(data)) {
          setHistoryEvents(data);
        }
      } catch (err) {
        console.error('Failed to load alert history:', err);
      }
    };

    loadHistory();
    const interval = setInterval(loadHistory, 3000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (isoString) => {
    if (!isoString) return '--:--';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return '--:--';
    }
  };

  // Combine top active alerts (if any) and resolved historical events (up to 4 items)
  const displayEvents = [];

  // Add active alerts first as ongoing events
  activeAlerts.forEach(a => {
    displayEvents.push({
      id: a.id,
      time: formatTime(a.created_at),
      type: a.type,
      title: a.title || a.type,
      camera: a.camera || 'C-01',
      severity: a.severity || 'HIGH',
      isZone: a.type === 'Restricted Zone Entry',
      status: a.status,
      isActive: true
    });
  });

  // Add history events
  historyEvents.forEach(h => {
    displayEvents.push({
      id: h.id,
      time: formatTime(h.resolved_at || h.created_at),
      type: h.type,
      title: h.status === 'RESOLVED' ? `${h.type} Resolved` : (h.title || h.type),
      camera: h.camera || 'C-01',
      severity: h.severity || 'HIGH',
      isZone: h.type === 'Restricted Zone Entry',
      status: h.status,
      isActive: false
    });
  });

  // Limit to latest 4 events
  const visibleEvents = displayEvents.slice(0, 4);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <History className="w-4 h-4 text-slate-700" />
          <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
            Recent Safety Events
          </h3>
        </div>
        <span className="text-[11px] font-semibold text-slate-500">
          Real Audit Log
        </span>
      </div>

      {visibleEvents.length === 0 ? (
        <div className="py-5 text-center text-xs text-slate-400">
          <p className="font-semibold text-slate-500">No Recent Incidents</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Safety events will record here when detected</p>
        </div>
      ) : (
        <div className="space-y-2">
          {visibleEvents.map((evt, idx) => {
            const isResolved = evt.status === 'RESOLVED';
            const isZone = evt.isZone;

            return (
              <div 
                key={`${evt.id}-${idx}`}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-50/70 border border-slate-200 text-xs"
              >
                <div className="flex items-center space-x-2.5">
                  <span className="font-mono text-slate-500 font-bold text-[11px]">
                    {evt.time}
                  </span>
                  <span className="text-sm">
                    {isResolved ? '✓' : isZone ? '🔴' : '🟠'}
                  </span>
                  <div>
                    <span className={`font-bold block text-xs ${
                      isResolved ? 'text-emerald-900' : isZone ? 'text-red-900' : 'text-amber-900'
                    }`}>
                      {evt.title}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      Camera {evt.camera}
                    </span>
                  </div>
                </div>

                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                  isResolved 
                    ? 'bg-emerald-100 text-emerald-800' 
                    : evt.isActive 
                    ? 'bg-red-100 text-red-800 animate-pulse' 
                    : 'bg-slate-200 text-slate-700'
                }`}>
                  {isResolved ? 'Resolved' : evt.isActive ? 'Active' : 'Logged'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
