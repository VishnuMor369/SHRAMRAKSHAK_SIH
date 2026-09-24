import React, { useState } from 'react';
import { CheckCircle2, ShieldAlert, ChevronRight, Activity, Clock, Check, Users, AlertTriangle } from 'lucide-react';
import { respondToAlert, markActionTaken } from '../services/api';

function getTimeAgo(isoString) {
  if (!isoString) return 'Just now';
  try {
    const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diffSec < 45) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin <= 1) return '1m ago';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    return `${diffHours}h ago`;
  } catch {
    return 'Recently';
  }
}

export default function AlertPanel({ alert, alerts = [], onSelectAlert, onViewAll }) {
  const [actingId, setActingId] = useState(null);

  const activeList = alerts && alerts.length > 0
    ? alerts
    : (alert ? [alert] : []);

  const sortedList = [...activeList].sort((a, b) => {
    const aIsProx = a.is_high_priority || a.type === 'Person–Vehicle Proximity' || (a.priority_score && a.priority_score >= 150);
    const bIsProx = b.is_high_priority || b.type === 'Person–Vehicle Proximity' || (b.priority_score && b.priority_score >= 150);
    if (aIsProx && !bIsProx) return -1;
    if (!aIsProx && bIsProx) return 1;
    const aPriority = a.priority_score ?? 80;
    const bPriority = b.priority_score ?? 80;
    if (bPriority !== aPriority) return bPriority - aPriority;
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
  });

  const handleAcknowledge = async (e, item) => {
    e.stopPropagation();
    try {
      setActingId(item.id);
      await respondToAlert('SUP-01', 'Supervisor acknowledged alert', item.id);
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    } finally {
      setActingId(null);
    }
  };

  const handleActionTaken = async (e, item) => {
    e.stopPropagation();
    try {
      setActingId(item.id);
      await markActionTaken('SUP-01', 'Action executed on-site', 'Action Taken', item.id);
    } catch (err) {
      console.error('Failed to mark action taken:', err);
    } finally {
      setActingId(null);
    }
  };

  return (
    <div className="space-y-3">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h2 className="text-xs font-black tracking-wider text-slate-800 uppercase">
            Active SIF Events
          </h2>
          {sortedList.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-rose-100 text-rose-800 border border-rose-200">
              {sortedList.length}
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
      {sortedList.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs space-y-2">
          <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 mx-auto">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              ✓ NO ACTIVE SIF PRECURSORS
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 font-medium">
              All monitored camera zones and critical exclusion barriers are currently compliant.
            </p>
          </div>
        </div>
      ) : (
        /* Compact Industrial SIF Precursor Cards (Phase 6 Hierarchy) */
        <div className="space-y-3">
          {sortedList.map((item) => {
            const isWaiting = item.status === 'WAITING_FOR_RESPONSE';
            const isResponding = item.status === 'RESPONDING';
            const isAwaitingVerification = item.verification_status === 'AWAITING_VERIFICATION' || item.action_status === 'COMPLETED';
            const isEscalated = item.status === 'ESCALATED';
            const sifLevel = item.sif_level || (item.priority_score >= 100 ? 'CRITICAL' : 'HIGH');
            const personCount = item.person_count || (item.affected_person_ids?.length || 1);

            return (
              <div 
                key={item.id}
                onClick={() => onSelectAlert && onSelectAlert(item)}
                className={`bg-white rounded-xl border p-4 transition-all shadow-xs hover:shadow-md cursor-pointer flex flex-col justify-between space-y-3 ${
                  sifLevel === 'CRITICAL' || item.is_high_priority
                    ? 'border-red-400 ring-1 ring-red-400/20'
                    : 'border-slate-300'
                }`}
              >
                {/* 1. TOP HEADER: SIF POTENTIAL + SEVERITY + LOCATION */}
                <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-base leading-none">🚨</span>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-black uppercase tracking-wider text-rose-700">
                          SIF POTENTIAL
                        </span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-black uppercase tracking-wider ${
                          sifLevel === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
                        }`}>
                          {sifLevel}
                        </span>
                      </div>
                      <h3 className="text-xs font-bold text-slate-900 mt-0.5">
                        {item.title || item.type}
                      </h3>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-[10px] font-mono font-bold text-slate-500 block">
                      Camera {item.camera || 'C-01'}
                    </span>
                    <span className="text-[10px] font-medium text-slate-400 block">
                      {getTimeAgo(item.created_at)}
                    </span>
                  </div>
                </div>

                {/* 2. THREE COMPACT EVIDENCE BULLETS (No paragraphs) */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-[11px] font-medium text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                  <div className="flex items-center space-x-1.5 truncate">
                    <Users className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <span className="font-bold text-slate-900">{personCount} {personCount > 1 ? 'PERSONS' : 'PERSON'} EXPOSED</span>
                  </div>
                  <div className="flex items-center space-x-1.5 truncate">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span className="truncate">{item.hazard || item.potential_consequence || 'Line-of-Fire'}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 truncate">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    <span className="truncate">{item.critical_barrier || 'Exclusion Barrier Violated'}</span>
                  </div>
                </div>

                {/* 3. IMMEDIATE ACTION & CONSEQUENCE (Concise) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-2">
                    <span className="text-[9px] font-black uppercase text-amber-800 tracking-wider block">
                      IMMEDIATE ACTION
                    </span>
                    <p className="text-[11px] font-bold text-slate-900 mt-0.5 leading-snug">
                      {item.immediate_action || 'Stop/hold hazardous activity and clear zone.'}
                    </p>
                  </div>
                  <div className="bg-rose-50/50 border border-rose-200 rounded-lg p-2">
                    <span className="text-[9px] font-black uppercase text-rose-800 tracking-wider block">
                      IF NOT ADDRESSED
                    </span>
                    <p className="text-[11px] font-medium text-slate-700 mt-0.5 leading-snug">
                      {item.consequence_if_not_addressed || 'Continued exposure may result in serious injury or fatality.'}
                    </p>
                  </div>
                </div>

                {/* 4. ACTIONS & STATUS BUTTONS */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-100 flex-wrap gap-2">
                  <div className="flex items-center space-x-1.5">
                    {isWaiting && (
                      <button
                        onClick={(e) => handleAcknowledge(e, item)}
                        disabled={actingId === item.id}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white rounded-lg text-xs font-black shadow-xs transition-colors disabled:opacity-50"
                      >
                        {actingId === item.id ? 'Saving...' : 'ACKNOWLEDGE'}
                      </button>
                    )}

                    {isResponding && !isAwaitingVerification && (
                      <button
                        onClick={(e) => handleActionTaken(e, item)}
                        disabled={actingId === item.id}
                        className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 rounded-lg text-xs font-black shadow-xs transition-colors disabled:opacity-50"
                      >
                        {actingId === item.id ? 'Saving...' : 'ACTION TAKEN'}
                      </button>
                    )}

                    {isAwaitingVerification && (
                      <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-black uppercase">
                        AWAITING VERIFICATION
                      </span>
                    )}

                    {isEscalated && (
                      <span className="px-2.5 py-1 rounded bg-rose-100 text-rose-800 border border-rose-200 text-[10px] font-black uppercase">
                        ESCALATED TO HSE
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => onSelectAlert && onSelectAlert(item)}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center space-x-1"
                  >
                    <span>VIEW DETAILS</span>
                    <ChevronRight className="w-3.5 h-3.5 text-amber-400" />
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
