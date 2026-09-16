import React from 'react';
import { ArrowRight, CheckCircle2, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function ResponsePipelineCard({ alert }) {
  const status = alert?.status || 'IDLE';

  // Pipeline stages
  const stages = [
    { key: 'AI_DETECTS', label: 'AI DETECTS' },
    { key: 'ALERT', label: 'ALERT' },
    { key: 'RESPOND', label: 'RESPOND' },
    { key: 'FIX', label: 'FIX' },
    { key: 'RESOLVE', label: 'RESOLVE' }
  ];

  // Determine stage active index:
  // IDLE: 0 (or all inactive)
  // WAITING_FOR_RESPONSE: 1 (ALERT active, waiting for respond)
  // RESPONDING: 2 (RESPOND / FIX active)
  // ESCALATED: 1 (ALERT escalated)
  // RESOLVED: 4 (RESOLVE active)
  let activeIndex = -1;
  let statusBadge = {
    dot: 'bg-emerald-500',
    title: 'NORMAL SURVEILLANCE',
    subtitle: 'System continuous monitoring active',
    colorClass: 'text-slate-700'
  };

  if (status === 'WAITING_FOR_RESPONSE') {
    activeIndex = 1;
    statusBadge = {
      dot: 'bg-red-500 animate-pulse',
      title: '● WAITING FOR SUPERVISOR',
      subtitle: '20s RESPONSE WINDOW',
      colorClass: 'text-red-700'
    };
  } else if (status === 'RESPONDING') {
    activeIndex = 2;
    statusBadge = {
      dot: 'bg-amber-500 animate-pulse',
      title: '● SUPERVISOR RESPONDING',
      subtitle: '60s ACTION WINDOW',
      colorClass: 'text-amber-700'
    };
  } else if (status === 'ESCALATED') {
    activeIndex = 1;
    statusBadge = {
      dot: 'bg-purple-600 animate-pulse',
      title: '⚠️ ESCALATED TO CONTROL ROOM',
      subtitle: 'SUPERVISOR SLA EXPIRED',
      colorClass: 'text-purple-800'
    };
  } else if (status === 'RESOLVED') {
    activeIndex = 4;
    statusBadge = {
      dot: 'bg-emerald-600',
      title: '✓ RESOLVED',
      subtitle: 'SAFETY VERIFIED ON SITE',
      colorClass: 'text-emerald-700'
    };
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
          Response Pipeline
        </h3>
        <span className="text-[11px] font-mono font-bold text-slate-400">
          SLA: 20s / 60s
        </span>
      </div>

      {/* Horizontal Pipeline Process Flow */}
      <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[10px] sm:text-xs font-bold text-slate-500">
        {stages.map((stage, idx) => {
          const isPassed = activeIndex >= 0 && idx < activeIndex;
          const isCurrent = activeIndex === idx;

          return (
            <React.Fragment key={stage.key}>
              <div className={`flex items-center space-x-1 ${
                isCurrent 
                  ? 'text-slate-900 font-black' 
                  : isPassed 
                  ? 'text-emerald-600 font-bold' 
                  : 'text-slate-400 font-medium'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  isCurrent ? 'bg-amber-500 ring-2 ring-amber-400/50' : isPassed ? 'bg-emerald-500' : 'bg-slate-300'
                }`}></span>
                <span>{stage.label}</span>
              </div>

              {idx < stages.length - 1 && (
                <span className="text-slate-300 font-normal">→</span>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Current Active Stage Display */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${statusBadge.dot}`}></span>
          <span className={`text-xs font-black tracking-tight ${statusBadge.colorClass}`}>
            {statusBadge.title}
          </span>
        </div>
        <span className="text-xs font-bold text-slate-500 tracking-tight">
          {statusBadge.subtitle}
        </span>
      </div>
    </div>
  );
}
