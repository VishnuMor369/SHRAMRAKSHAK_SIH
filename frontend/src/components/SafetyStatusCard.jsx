import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function SafetyStatusCard({ status }) {
  const currentSafetyState = status?.current_safety_state || 'MONITORING';
  const activeAlert = status?.active_alert;
  const isResolved = activeAlert?.status === 'RESOLVED';
  const isEscalated = activeAlert?.status === 'ESCALATED';

  // Determine display configuration based on safety status
  let theme = {
    bg: 'bg-slate-50',
    border: 'border-slate-200',
    badgeBg: 'bg-slate-200',
    badgeText: 'text-slate-800',
    titleColor: 'text-slate-800',
    icon: <AlertTriangle className="w-8 h-8 text-slate-500" />,
    title: 'ZONE MONITORING ACTIVE',
    subtitle: 'AI video stream analyzing workplace PPE compliance in real-time.',
    statusBadge: 'MONITORING',
  };

  if (currentSafetyState === 'VIOLATION' || (activeAlert && !isResolved)) {
    theme = {
      bg: 'bg-red-50',
      border: 'border-red-300',
      badgeBg: 'bg-red-600',
      badgeText: 'text-white',
      titleColor: 'text-red-900',
      icon: <ShieldAlert className="w-9 h-9 text-safety-crimson" />,
      title: 'SAFETY VIOLATION — NO HELMET',
      subtitle: 'Worker detected in hazardous work zone without required hard hat/PPE.',
      statusBadge: 'CRITICAL HAZARD',
    };
  } else if (isResolved || currentSafetyState === 'SAFE') {
    theme = {
      bg: 'bg-emerald-50',
      border: 'border-emerald-300',
      badgeBg: 'bg-emerald-600',
      badgeText: 'text-white',
      titleColor: 'text-emerald-950',
      icon: <ShieldCheck className="w-9 h-9 text-emerald-600" />,
      title: 'SAFE — Helmet Detected',
      subtitle: isResolved 
        ? 'Supervisor confirmed PPE compliance. Hazard resolved and closed.' 
        : 'All detected personnel are compliant with mandatory head protection standards.',
      statusBadge: isResolved ? 'RESOLVED & SAFE' : 'PPE COMPLIANT',
    };
  }

  return (
    <div 
      tabIndex={0}
      role="region"
      aria-label={`Safety Status: ${theme.title}`}
      className={`industrial-card group p-5 border-2 ${theme.border} ${theme.bg} rounded-xl hover:shadow-md hover:border-slate-400 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 transition-all duration-200 cursor-default`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-4">
          <div className="p-2.5 rounded-lg bg-white shadow-xs border border-slate-200/80 group-hover:scale-105 group-hover:shadow-sm transition-all duration-200 shrink-0">
            {theme.icon}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className={`px-2.5 py-0.5 rounded text-xs font-black tracking-wider uppercase transition-transform group-hover:scale-[1.02] ${theme.badgeBg} ${theme.badgeText}`}>
                {theme.statusBadge}
              </span>
              <span className="text-xs font-semibold text-slate-500">
                Rule: LSR #01 PPE Compliance
              </span>
            </div>
            <h2 className={`text-xl sm:text-2xl font-black mt-1.5 tracking-tight ${theme.titleColor}`}>
              {theme.title}
            </h2>
            <p className="text-xs sm:text-sm font-medium text-slate-600 mt-1 max-w-xl">
              {theme.subtitle}
            </p>
          </div>
        </div>

        {/* Real-time Indicator pill */}
        <div className="hidden sm:block text-right">
          <div className="text-xs font-mono font-medium text-slate-400">
            {new Date().toLocaleTimeString()}
          </div>
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">
            Zone: Demo C-01
          </div>
        </div>
      </div>
    </div>
  );
}
