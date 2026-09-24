import React from 'react';
import { ShieldAlert, AlertTriangle, Clock, CheckCircle2, ShieldCheck } from 'lucide-react';

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

  // Verified Count
  const verifiedCount = status?.verified_count !== undefined
    ? status.verified_count
    : 18;

  function getattrSif(a) {
    const lvl = a?.sif_level || '';
    const pot = String(a?.sif_potential || '');
    return lvl === 'CRITICAL' || lvl === 'HIGH' || pot.includes('SIF') || pot.includes('HIGH');
  }

  const formatNum = (num) => String(num ?? 0).padStart(2, '0');

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {/* 1. SIF POTENTIAL */}
      <div className={`p-3.5 rounded-xl border transition-all shadow-xs flex flex-col justify-between ${
        sifPotentialCount > 0 
          ? 'bg-rose-50/90 border-rose-300 ring-2 ring-rose-400/20 text-rose-950' 
          : 'bg-white border-slate-200 text-slate-900'
      }`}>
        <div className="flex items-center justify-between">
          <span className={`text-[10px] font-black uppercase tracking-wider ${
            sifPotentialCount > 0 ? 'text-rose-700' : 'text-slate-500'
          }`}>
            SIF POTENTIAL
          </span>
          <div className={`w-6 h-6 rounded-md flex items-center justify-center ${
            sifPotentialCount > 0 ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-500'
          }`}>
            <ShieldAlert className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className={`text-2xl sm:text-3xl font-black font-mono tracking-tight ${
            sifPotentialCount > 0 ? 'text-rose-700' : 'text-slate-900'
          }`}>
            {formatNum(sifPotentialCount)}
          </div>
          <p className="text-[11px] font-medium text-slate-500 mt-0.5 truncate">
            {sifPotentialCount > 0 ? 'Precursors flagged' : 'No precursor active'}
          </p>
        </div>
      </div>

      {/* 2. ACTIVE ALERTS */}
      <div className={`p-3.5 rounded-xl border transition-all shadow-xs flex flex-col justify-between ${
        activeAlertsCount > 0 
          ? 'bg-amber-50/90 border-amber-300 ring-2 ring-amber-400/20 text-amber-950' 
          : 'bg-white border-slate-200 text-slate-900'
      }`}>
        <div className="flex items-center justify-between">
          <span className={`text-[10px] font-black uppercase tracking-wider ${
            activeAlertsCount > 0 ? 'text-amber-800' : 'text-slate-500'
          }`}>
            ACTIVE ALERTS
          </span>
          <div className={`w-6 h-6 rounded-md flex items-center justify-center ${
            activeAlertsCount > 0 ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-500'
          }`}>
            <AlertTriangle className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className={`text-2xl sm:text-3xl font-black font-mono tracking-tight ${
            activeAlertsCount > 0 ? 'text-amber-800' : 'text-slate-900'
          }`}>
            {formatNum(activeAlertsCount)}
          </div>
          <p className="text-[11px] font-medium text-slate-500 mt-0.5 truncate">
            {activeAlertsCount > 0 ? 'Unresolved events' : 'Perimeter clear'}
          </p>
        </div>
      </div>

      {/* 3. OPEN ACTIONS */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
            OPEN ACTIONS
          </span>
          <div className="w-6 h-6 rounded-md bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <Clock className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900 tracking-tight">
            {formatNum(openActionsCount)}
          </div>
          <p className="text-[11px] font-medium text-slate-500 mt-0.5 truncate">
            {openActionsCount > 0 ? 'In progress on-site' : 'All actions assigned'}
          </p>
        </div>
      </div>

      {/* 4. AWAITING VERIFICATION */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
            AWAITING VERIFICATION
          </span>
          <div className="w-6 h-6 rounded-md bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
            <ShieldCheck className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900 tracking-tight">
            {formatNum(awaitingVerificationCount)}
          </div>
          <p className="text-[11px] font-medium text-slate-500 mt-0.5 truncate">
            CCTV / Field audit
          </p>
        </div>
      </div>

      {/* 5. VERIFIED */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between col-span-2 sm:col-span-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
            VERIFIED
          </span>
          <div className="w-6 h-6 rounded-md bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="mt-2">
          <div className="text-2xl sm:text-3xl font-black font-mono text-emerald-700 tracking-tight">
            {formatNum(verifiedCount)}
          </div>
          <p className="text-[11px] font-medium text-slate-500 mt-0.5 truncate">
            Controls verified & closed
          </p>
        </div>
      </div>
    </div>
  );
}
