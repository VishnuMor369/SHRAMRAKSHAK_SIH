import React from 'react';
import { UserCheck, Clock, CheckCircle2, AlertOctagon, ArrowRight, ShieldCheck } from 'lucide-react';

export default function ResponseStatusCard({ alert }) {
  const status = alert?.status || 'IDLE';

  const steps = [
    {
      id: 'WAITING_FOR_RESPONSE',
      label: '1. Waiting for Supervisor',
      desc: '20s Response Window',
      active: status === 'WAITING_FOR_RESPONSE',
      completed: ['RESPONDING', 'RESOLVED', 'ESCALATED'].includes(status),
      color: 'red',
    },
    {
      id: 'RESPONDING',
      label: '2. Supervisor Responding',
      desc: '60s On-Site Action',
      active: status === 'RESPONDING',
      completed: status === 'RESOLVED',
      color: 'amber',
    },
    {
      id: 'RESOLVED',
      label: status === 'ESCALATED' ? '3. Escalated' : '3. Resolved',
      desc: status === 'ESCALATED' ? 'Control Room Notified' : 'PPE Verified on Site',
      active: status === 'RESOLVED' || status === 'ESCALATED',
      completed: status === 'RESOLVED',
      color: status === 'ESCALATED' ? 'purple' : 'emerald',
    }
  ];

  return (
    <div className="industrial-card p-5 bg-white">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
        <h4 className="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <UserCheck className="w-4 h-4 text-slate-700" />
          <span>HUMAN-IN-THE-LOOP RESPONSE PIPELINE</span>
        </h4>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
          Status: {status}
        </span>
      </div>

      {/* Step Pipeline Visualization */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mt-4">
        {steps.map((step, idx) => {
          let cardStyle = 'bg-slate-50 border-slate-200 text-slate-400';
          let badgeStyle = 'bg-slate-200 text-slate-500';

          if (step.active) {
            if (step.color === 'red') {
              cardStyle = 'bg-red-50 border-red-300 text-red-900 ring-2 ring-red-400/50';
              badgeStyle = 'bg-red-600 text-white animate-pulse';
            } else if (step.color === 'amber') {
              cardStyle = 'bg-amber-50 border-amber-300 text-amber-900 ring-2 ring-amber-400/50';
              badgeStyle = 'bg-amber-600 text-white animate-pulse';
            } else if (step.color === 'purple') {
              cardStyle = 'bg-purple-50 border-purple-300 text-purple-900 ring-2 ring-purple-400/50';
              badgeStyle = 'bg-purple-700 text-white';
            } else {
              cardStyle = 'bg-emerald-50 border-emerald-300 text-emerald-900 ring-2 ring-emerald-400/50';
              badgeStyle = 'bg-emerald-600 text-white';
            }
          } else if (step.completed && status !== 'ESCALATED') {
            cardStyle = 'bg-emerald-50/60 border-emerald-200 text-emerald-900';
            badgeStyle = 'bg-emerald-600 text-white';
          }

          return (
            <div
              key={step.id}
              className={`p-3.5 rounded-lg border transition-all ${cardStyle}`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-black tracking-tight">{step.label}</span>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${badgeStyle}`}>
                  {step.completed ? '✓' : idx + 1}
                </span>
              </div>
              <p className="text-[11px] font-medium opacity-80">{step.desc}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span>AI detects visible safety violations → Human supervisor verifies & resolves</span>
        <span className="font-mono text-[11px]">SLA: Stage 1 (20s) | Stage 2 (60s)</span>
      </div>
    </div>
  );
}
