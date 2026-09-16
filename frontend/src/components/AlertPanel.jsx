import React from 'react';
import { CheckCircle2, ArrowRight } from 'lucide-react';

function getTimeAgo(isoString) {
  if (!isoString) return 'Detected just now';
  try {
    const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diffSec < 45) return 'Detected just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin <= 1) return 'Detected 1 min ago';
    if (diffMin < 60) return `Detected ${diffMin} min ago`;
    const diffHours = Math.floor(diffMin / 60);
    return `Detected ${diffHours}h ago`;
  } catch {
    return 'Detected recently';
  }
}

export default function AlertPanel({ alert, alerts = [], onSelectAlert, onViewAll }) {
  // Support both array and single alert object
  const activeList = alerts && alerts.length > 0
    ? alerts
    : (alert ? [alert] : []);

  return (
    <div className="space-y-3">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h2 className="text-xs font-black tracking-wider text-slate-800 uppercase">
            Active Alerts
          </h2>
          {activeList.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-red-100 text-red-700 border border-red-200">
              {activeList.length}
            </span>
          )}
        </div>

        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs font-bold text-slate-600 hover:text-slate-900 flex items-center space-x-1 transition-colors group"
          >
            <span>View All</span>
            <span className="text-slate-400 group-hover:text-slate-700 transition-colors">→</span>
          </button>
        )}
      </div>

      {/* Empty State when no active alerts */}
      {activeList.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-sm space-y-2">
          <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 mx-auto">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              ✓ NO ACTIVE SAFETY ALERTS
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 font-medium">
              All monitored conditions are currently clear.
            </p>
          </div>
        </div>
      ) : (
        /* List of Clean Active Alert Cards */
        <div className="space-y-2.5">
          {activeList.map((item) => {
            const isZone = item.type === 'Restricted Zone Entry' || item.title?.toLowerCase().includes('zone');
            const severity = item.severity || (isZone ? 'CRITICAL' : 'HIGH');
            
            // Format standard clean titles
            let displayTitle = item.title || item.type;
            if (isZone) {
              displayTitle = 'RESTRICTED ZONE BREACH';
            } else if (item.type?.includes('Helmet') || item.title?.includes('Helmet')) {
              displayTitle = 'NO HELMET DETECTED';
            }

            return (
              <div 
                key={item.id}
                className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 p-4 transition-all shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                    <span className="text-sm leading-none">{isZone ? '🔴' : '🟠'}</span>
                    <h3 className="text-xs font-black text-slate-900 uppercase tracking-tight">
                      {displayTitle}
                    </h3>
                    {item.incident_id && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                        {item.incident_id}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-600 font-medium flex items-center space-x-2 flex-wrap gap-y-1">
                    <span>Camera {item.camera || 'C-01'}</span>
                    <span className="text-slate-300">•</span>
                    <span>{item.location || 'Site Area'}</span>
                    <span className="text-slate-300">•</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      {item.source || 'CCTV'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-medium">
                    {getTimeAgo(item.created_at)}
                  </div>
                </div>

                <div className="flex items-center space-x-3 self-end sm:self-center shrink-0">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${
                    severity === 'CRITICAL'
                      ? 'bg-red-50 text-red-700 border-red-200'
                      : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {severity}
                  </span>

                  <button
                    onClick={() => onSelectAlert && onSelectAlert(item)}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center space-x-1"
                  >
                    <span>VIEW</span>
                    <span className="text-amber-400">→</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
