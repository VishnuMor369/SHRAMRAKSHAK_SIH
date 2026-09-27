import React from 'react';
import { ArrowRight, CheckCircle2, Clock, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ResponsePipelineCard({ alert }) {
  const status = alert?.status || 'IDLE';

  // 5-stage pipeline mapping to actual HSE SLA protocol
  const stages = [
    { key: 'AI_DETECTS', label: 'AI DETECTED', short: 'DETECT' },
    { key: 'ASSIGNED', label: 'ASSIGNED', short: 'ASSIGN' },
    { key: 'RESPONDING', label: 'RESPONDING', short: 'RESPOND' },
    { key: 'ACTION_TAKEN', label: 'ACTION TAKEN', short: 'ACTION' },
    { key: 'RESOLVED', label: 'RESOLVED', short: 'CLOSED' }
  ];

  let activeIndex = -1;
  let statusBadge = {
    dot: 'bg-emerald-500',
    title: 'NORMAL SURVEILLANCE',
    subtitle: 'System continuous monitoring active',
    badgeClass: 'bg-emerald-50 text-emerald-800 border-emerald-200'
  };

  if (status === 'WAITING_FOR_RESPONSE') {
    activeIndex = 1;
    statusBadge = {
      dot: 'bg-safety-crimson',
      title: 'WAITING FOR SUPERVISOR',
      subtitle: '20s Response SLA Active',
      badgeClass: 'bg-red-50 text-red-900 border-red-200'
    };
  } else if (status === 'RESPONDING') {
    activeIndex = 2;
    statusBadge = {
      dot: 'bg-safety-amber',
      title: 'SUPERVISOR ON-SITE',
      subtitle: '60s Corrective Action Window',
      badgeClass: 'bg-amber-50 text-amber-900 border-amber-200'
    };
  } else if (status === 'ESCALATED') {
    activeIndex = 1;
    statusBadge = {
      dot: 'bg-purple-600',
      title: 'ESCALATED TO CONTROL ROOM',
      subtitle: 'Supervisor SLA Expired',
      badgeClass: 'bg-purple-50 text-purple-900 border-purple-200'
    };
  } else if (status === 'RESOLVED') {
    activeIndex = 4;
    statusBadge = {
      dot: 'bg-safety-emerald',
      title: 'VERIFIED & RESOLVED',
      subtitle: 'Field Barrier Restored',
      badgeClass: 'bg-emerald-50 text-emerald-900 border-emerald-200'
    };
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 p-4 shadow-xs space-y-3.5 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-slate-700" />
          <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
            Response Pipeline
          </h3>
        </div>
        <span 
          tabIndex={0}
          className="text-[11px] font-mono-timer font-bold text-slate-500 bg-slate-100 hover:bg-slate-200/80 px-2 py-0.5 rounded border border-slate-200 hover:border-slate-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        >
          SLA: 20s / 60s
        </span>
      </div>

      {/* Horizontal Pipeline Steps */}
      <div className="grid grid-cols-5 gap-1.5 p-2 bg-slate-50 rounded-lg border border-slate-200">
        {stages.map((stage, idx) => {
          const isPassed = activeIndex >= 0 && idx < activeIndex;
          const isCurrent = activeIndex === idx;

          return (
            <div 
              key={stage.key}
              tabIndex={0}
              role="group"
              aria-label={`Pipeline Stage ${stage.label}`}
              className={cn(
                "flex flex-col items-center justify-center p-1.5 rounded text-center min-w-0 select-none cursor-default",
                "hover:border-slate-300 hover:shadow-2xs active:scale-[0.98] transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1",
                isCurrent 
                  ? "bg-white border border-slate-300 shadow-2xs hover:border-slate-400" 
                  : isPassed 
                  ? "bg-emerald-50/70 border border-emerald-200/60 hover:bg-emerald-100/70 hover:border-emerald-300" 
                  : "bg-transparent border border-transparent hover:bg-slate-100/80 hover:border-slate-200"
              )}
            >
              <div className="flex items-center space-x-1 mb-1">
                <span className={cn(
                  "w-2 h-2 rounded-full",
                  isCurrent 
                    ? (status === 'WAITING_FOR_RESPONSE' ? "bg-safety-crimson" : "bg-safety-amber")
                    : isPassed 
                    ? "bg-safety-emerald" 
                    : "bg-slate-300"
                )} />
                <span className={cn(
                  "text-[10px] font-bold font-mono-timer",
                  isCurrent ? "text-slate-950 font-black" : isPassed ? "text-emerald-800" : "text-slate-400"
                )}>
                  {isPassed ? '✓' : `0${idx + 1}`}
                </span>
              </div>
              <span className={cn(
                "text-[9px] sm:text-[10px] uppercase font-bold tracking-tight truncate w-full",
                isCurrent ? "text-slate-950 font-black" : isPassed ? "text-emerald-900" : "text-slate-400"
              )}>
                {stage.short}
              </span>
            </div>
          );
        })}
      </div>

      {/* Current Active Status Banner (Static high-contrast, no pulsing) */}
      <div 
        tabIndex={0}
        role="status"
        className={cn(
          "flex items-center justify-between p-2.5 rounded-lg border hover:shadow-xs active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1 transition-all cursor-default",
          statusBadge.badgeClass
        )}
      >
        <div className="flex items-center space-x-2 min-w-0">
          <span className={cn("w-2 h-2 rounded-full shrink-0", statusBadge.dot)} />
          <span className="text-xs font-black tracking-tight uppercase truncate">
            {statusBadge.title}
          </span>
        </div>
        <span className="text-[11px] font-bold tracking-tight opacity-90 shrink-0 ml-2">
          {statusBadge.subtitle}
        </span>
      </div>
    </div>
  );
}
