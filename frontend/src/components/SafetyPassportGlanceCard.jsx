import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  ShieldCheck, 
  ShieldAlert, 
  PlusCircle, 
  ArrowRight 
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SafetyPassportGlanceCard({ status, onOpenPassport, onCreatePassport }) {
  const passport = status?.active_passport;
  const [remainingTime, setRemainingTime] = useState('');

  useEffect(() => {
    if (!passport || !passport.expires_at) return;

    const updateCountdown = () => {
      const now = Date.now();
      const exp = new Date(passport.expires_at).getTime();
      const diff = Math.max(0, Math.floor((exp - now) / 1000));
      const mins = Math.floor(diff / 60);
      const secs = diff % 60;
      setRemainingTime(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [passport]);

  // Case 1: No active passport clearance
  if (!passport || passport.status === 'CLOSED' || passport.status === 'EXPIRED') {
    return (
      <div className="bg-white rounded-xl border border-slate-200 px-4 py-2.5 shadow-xs flex items-center justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
            <Shield className="w-4 h-4 text-slate-600" />
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Safety Passport
            </span>
            <span className="text-xs font-semibold text-slate-700 block mt-0.5 truncate">
              No active clearance
            </span>
          </div>
        </div>

        <button
          onClick={onCreatePassport || onOpenPassport}
          className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 active:scale-[0.98] text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center space-x-1.5 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        >
          <PlusCircle className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden sm:inline">+ CREATE SAFETY PASSPORT</span>
          <span className="sm:hidden">+ CREATE</span>
        </button>
      </div>
    );
  }

  // Case 2: Active, Paused, or In-Progress Passport
  const isPaused = passport.status === 'PAUSED';
  const isAwaiting = passport.status === 'AWAITING_RESTORATION';
  const isActive = passport.status === 'ACTIVE';

  const badgeBg = isPaused 
    ? 'bg-red-50 text-safety-crimson border-red-200'
    : isAwaiting
    ? 'bg-amber-50 text-amber-900 border-amber-200'
    : isActive
    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
    : 'bg-slate-100 text-slate-800 border-slate-200';

  const statusLabel = isPaused
    ? 'PAUSED (BREACH)'
    : isAwaiting
    ? 'AWAITING RESTORATION'
    : isActive
    ? 'ACTIVE'
    : passport.status;

  return (
    <div className={cn(
      "rounded-xl border px-4 py-2.5 shadow-xs transition-colors flex items-center justify-between gap-3",
      isPaused 
        ? "bg-red-50/60 border-red-300" 
        : isAwaiting 
        ? "bg-amber-50/60 border-amber-300" 
        : "bg-white border-slate-200"
    )}>
      <div className="flex items-center space-x-3 min-w-0">
        <div className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-2xs",
          isPaused 
            ? "bg-safety-crimson text-white" 
            : isAwaiting
            ? "bg-safety-amber text-slate-950"
            : "bg-slate-900 text-amber-400"
        )}>
          {isPaused ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
        </div>

        <div className="min-w-0">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              Safety Passport
            </span>
            <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border", badgeBg)}>
              {statusLabel}
            </span>
          </div>
          <div className="text-xs font-black text-slate-900 truncate mt-0.5">
            {passport.task_type || 'High-Risk Operation'} • {passport.location || 'Site Area'}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2.5 shrink-0">
        {isActive && remainingTime && (
          <span className="text-xs font-mono-timer font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 hidden sm:inline">
            ⏱ {remainingTime}
          </span>
        )}
        <button
          onClick={onOpenPassport}
          className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 active:scale-[0.98] text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center space-x-1.5 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        >
          <span>VIEW PASSPORT</span>
          <ArrowRight className="w-3.5 h-3.5 text-amber-400" />
        </button>
      </div>
    </div>
  );
}
