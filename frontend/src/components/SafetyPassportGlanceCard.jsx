import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  ShieldCheck, 
  ShieldAlert, 
  PlusCircle, 
  ArrowRight 
} from 'lucide-react';

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
      <div className="bg-white rounded-xl border border-slate-200 px-4 py-2.5 shadow-sm flex items-center justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
            <Shield className="w-4 h-4 text-slate-600" />
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Safety Passport
            </span>
            <span className="text-xs font-semibold text-slate-700 block mt-0.5">
              No active clearance
            </span>
          </div>
        </div>

        <button
          onClick={onCreatePassport || onOpenPassport}
          className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 shrink-0"
        >
          <PlusCircle className="w-3.5 h-3.5 text-amber-400" />
          <span>+ CREATE SAFETY PASSPORT</span>
        </button>
      </div>
    );
  }

  // Case 2: Active, Paused, or In-Progress Passport
  const isPaused = passport.status === 'PAUSED';
  const isAwaiting = passport.status === 'AWAITING_RESTORATION';
  const isActive = passport.status === 'ACTIVE';

  const badgeBg = isPaused 
    ? 'bg-red-100 text-red-800 border-red-300'
    : isAwaiting
    ? 'bg-amber-100 text-amber-800 border-amber-300'
    : isActive
    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
    : 'bg-blue-100 text-blue-800 border-blue-300';

  const statusLabel = isPaused
    ? 'PAUSED (BREACH)'
    : isAwaiting
    ? 'AWAITING RESTORATION'
    : isActive
    ? 'ACTIVE'
    : passport.status;

  return (
    <div className={`rounded-xl border px-4 py-2.5 shadow-sm transition-all flex items-center justify-between gap-3 ${
      isPaused 
        ? 'bg-red-50/70 border-red-300 ring-1 ring-red-400/30' 
        : isAwaiting 
        ? 'bg-amber-50/70 border-amber-300 ring-1 ring-amber-400/30' 
        : 'bg-white border-slate-200'
    }`}>
      <div className="flex items-center space-x-3 min-w-0">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isPaused 
            ? 'bg-red-600 text-white shadow-sm' 
            : isAwaiting
            ? 'bg-amber-600 text-white shadow-sm'
            : 'bg-slate-900 text-amber-400'
        }`}>
          {isPaused ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
        </div>

        <div className="min-w-0">
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              Safety Passport
            </span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider border ${badgeBg}`}>
              {statusLabel}
            </span>
          </div>
          <div className="text-xs font-bold text-slate-900 truncate mt-0.5">
            {passport.task_type || 'High-Risk Operation'} • {passport.location || 'Site Area'}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-3 shrink-0">
        {isActive && remainingTime && (
          <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 hidden sm:inline">
            ⏱ {remainingTime}
          </span>
        )}
        <button
          onClick={onOpenPassport}
          className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 shrink-0"
        >
          <span>VIEW PASSPORT</span>
          <ArrowRight className="w-3.5 h-3.5 text-amber-400" />
        </button>
      </div>
    </div>
  );
}
