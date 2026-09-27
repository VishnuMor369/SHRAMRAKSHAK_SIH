import React from 'react';
import { ShieldAlert, AlertTriangle, Clock, CheckCircle2, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SummaryCards({ status, alerts = [] }) {
  // SIF Potential Count
  const sifPotentialCount = status?.sif_potential_count !== undefined 
    ? status.sif_potential_count 
    : alerts.filter(a => getattrSif(a)).length;

  // Active Alerts Count
  const activeAlertsCount = alerts.length > 0 
    ? alerts.length 
    : (status?.active_alerts?.length ?? (status?.active_alert ? 1 : 0));

  // Open Actions Count
  const openActionsCount = status?.open_actions_count !== undefined
    ? status.open_actions_count
    : alerts.filter(a => a.action_status !== 'COMPLETED').length;

  // Awaiting Verification Count
  const awaitingVerificationCount = status?.awaiting_verification_count !== undefined
    ? status.awaiting_verification_count
    : alerts.filter(a => a.verification_status === 'AWAITING_VERIFICATION').length;

  // Verified Count — fallback to 0 (no hardcoded fake number; requires backend field status.verified_count or real verified alerts)
  const verifiedCount = status?.verified_count !== undefined
    ? status.verified_count
    : alerts.filter(a => a.verification_status === 'VERIFIED' || a.action_status === 'VERIFIED' || a.resolved === true).length;

  function getattrSif(a) {
    const lvl = a?.sif_level || '';
    const pot = String(a?.sif_potential || '');
    return lvl === 'CRITICAL' || lvl === 'HIGH' || pot.includes('SIF') || pot.includes('HIGH');
  }

  const formatNum = (num) => String(num ?? 0).padStart(2, '0');

  const cards = [
    {
      id: 'sif',
      label: 'SIF POTENTIAL',
      count: sifPotentialCount,
      subtitle: sifPotentialCount > 0 ? 'Precursors flagged' : 'No precursor active',
      icon: ShieldAlert,
      isAlert: sifPotentialCount > 0,
      alertStyles: {
        card: 'bg-red-50/80 border-safety-crimson/40 ring-1 ring-safety-crimson/20 text-slate-900',
        label: 'text-safety-crimson',
        icon: 'bg-safety-crimson text-white shadow-xs',
        number: 'text-safety-crimson',
        sub: 'text-red-700 font-semibold',
      },
      normalStyles: {
        card: 'bg-white border-slate-200 text-slate-900 hover:border-slate-300',
        label: 'text-slate-500',
        icon: 'bg-slate-100 text-slate-500',
        number: 'text-safety-dark',
        sub: 'text-slate-500',
      },
    },
    {
      id: 'active_alerts',
      label: 'ACTIVE ALERTS',
      count: activeAlertsCount,
      subtitle: activeAlertsCount > 0 ? 'Unresolved events' : 'Perimeter clear',
      icon: AlertTriangle,
      isAlert: activeAlertsCount > 0,
      alertStyles: {
        card: 'bg-amber-50/80 border-safety-amber/50 ring-1 ring-safety-amber/20 text-slate-900',
        label: 'text-amber-800',
        icon: 'bg-safety-amber text-slate-950 shadow-xs',
        number: 'text-amber-800',
        sub: 'text-amber-700 font-semibold',
      },
      normalStyles: {
        card: 'bg-white border-slate-200 text-slate-900 hover:border-slate-300',
        label: 'text-slate-500',
        icon: 'bg-slate-100 text-slate-500',
        number: 'text-safety-dark',
        sub: 'text-slate-500',
      },
    },
    {
      id: 'open_actions',
      label: 'OPEN ACTIONS',
      count: openActionsCount,
      subtitle: openActionsCount > 0 ? 'In progress on-site' : 'All actions assigned',
      icon: Clock,
      isAlert: false,
      normalStyles: {
        card: 'bg-white border-slate-200 text-slate-900 hover:border-slate-300',
        label: 'text-slate-500',
        icon: 'bg-slate-100 text-blue-600',
        number: 'text-safety-dark',
        sub: 'text-slate-500',
      },
    },
    {
      id: 'awaiting_verification',
      label: 'AWAITING VERIFICATION',
      count: awaitingVerificationCount,
      subtitle: 'CCTV / Field audit',
      icon: ShieldCheck,
      isAlert: false,
      normalStyles: {
        card: 'bg-white border-slate-200 text-slate-900 hover:border-slate-300',
        label: 'text-slate-500',
        icon: 'bg-slate-100 text-purple-600',
        number: 'text-safety-dark',
        sub: 'text-slate-500',
      },
    },
    {
      id: 'verified',
      label: 'VERIFIED',
      count: verifiedCount,
      subtitle: 'Controls verified & closed',
      icon: CheckCircle2,
      isAlert: false,
      className: 'col-span-2 sm:col-span-1',
      normalStyles: {
        card: 'bg-white border-slate-200 text-slate-900 hover:border-slate-300',
        label: 'text-slate-500',
        icon: 'bg-emerald-50 text-safety-emerald border border-emerald-100',
        number: 'text-safety-emerald',
        sub: 'text-slate-500',
      },
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {cards.map((card) => {
        const Icon = card.icon;
        const styles = card.isAlert ? card.alertStyles : card.normalStyles;

        return (
          <div
            key={card.id}
            className={cn(
              'p-3.5 rounded-xl border transition-all duration-150 shadow-xs flex flex-col justify-between',
              styles.card,
              card.className
            )}
          >
            <div className="flex items-center justify-between">
              <span className={cn('text-[10px] font-black uppercase tracking-wider', styles.label)}>
                {card.label}
              </span>
              <div className={cn('w-6 h-6 rounded-md flex items-center justify-center shrink-0', styles.icon)}>
                <Icon className="w-3.5 h-3.5" />
              </div>
            </div>

            <div className="mt-2">
              <div className={cn('text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums', styles.number)}>
                {formatNum(card.count)}
              </div>
              <p className={cn('text-[11px] font-medium mt-0.5 truncate', styles.sub)}>
                {card.subtitle}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
