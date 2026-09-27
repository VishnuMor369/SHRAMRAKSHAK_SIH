import React from 'react';
import { UserCheck, Clock, CheckCircle2, AlertOctagon, ArrowRight, ShieldCheck, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ResponseStatusCard({ alert }) {
  const status = alert?.status || 'IDLE';

  const steps = [
    {
      id: 'WAITING_FOR_RESPONSE',
      stepNum: '01',
      label: 'Supervisor Acknowledgement',
      desc: '20s Initial Response SLA',
      active: status === 'WAITING_FOR_RESPONSE',
      completed: ['RESPONDING', 'RESOLVED', 'ESCALATED'].includes(status),
      color: 'red',
    },
    {
      id: 'RESPONDING',
      stepNum: '02',
      label: 'On-Site Hazard Mitigation',
      desc: '60s Corrective Action Window',
      active: status === 'RESPONDING',
      completed: status === 'RESOLVED',
      color: 'amber',
    },
    {
      id: 'RESOLVED',
      stepNum: '03',
      label: status === 'ESCALATED' ? 'Control Room Escalation' : 'Verification & Closure',
      desc: status === 'ESCALATED' ? 'Supervisor SLA Breached' : 'CCTV or Field Sign-Off',
      active: status === 'RESOLVED' || status === 'ESCALATED',
      completed: status === 'RESOLVED',
      color: status === 'ESCALATED' ? 'purple' : 'emerald',
    }
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 p-4 shadow-xs space-y-3.5 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <UserCheck className="w-4 h-4 text-slate-700" />
          <h4 className="text-xs font-black text-slate-900 tracking-wider uppercase">
            Human-in-the-Loop Protocol
          </h4>
        </div>
        <span 
          tabIndex={0}
          className={cn(
            "text-[10px] font-mono-timer font-bold px-2 py-0.5 rounded border uppercase transition-all hover:shadow-2xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900",
            status === 'WAITING_FOR_RESPONSE' ? "bg-red-50 text-safety-crimson border-red-200" :
            status === 'RESPONDING' ? "bg-amber-50 text-amber-800 border-amber-200" :
            status === 'RESOLVED' ? "bg-emerald-50 text-emerald-800 border-emerald-200" :
            status === 'ESCALATED' ? "bg-purple-50 text-purple-800 border-purple-200" :
            "bg-slate-100 text-slate-600 border-slate-200"
          )}
        >
          Status: {status}
        </span>
      </div>

      {/* Step Pipeline Visualization */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {steps.map((step) => {
          let cardStyle = 'bg-slate-50/80 border-slate-200 text-slate-400';
          let badgeStyle = 'bg-slate-200 text-slate-600 border-slate-300';

          if (step.active) {
            if (step.color === 'red') {
              cardStyle = 'bg-red-50/70 border-red-300 text-red-950 font-bold hover:border-red-400';
              badgeStyle = 'bg-safety-crimson text-white border-red-700';
            } else if (step.color === 'amber') {
              cardStyle = 'bg-amber-50/70 border-amber-300 text-amber-950 font-bold hover:border-amber-400';
              badgeStyle = 'bg-safety-amber text-slate-950 border-amber-500';
            } else if (step.color === 'purple') {
              cardStyle = 'bg-purple-50/70 border-purple-300 text-purple-950 font-bold hover:border-purple-400';
              badgeStyle = 'bg-purple-700 text-white border-purple-800';
            } else {
              cardStyle = 'bg-emerald-50/70 border-emerald-300 text-emerald-950 font-bold hover:border-emerald-400';
              badgeStyle = 'bg-safety-emerald text-white border-emerald-700';
            }
          } else if (step.completed && status !== 'ESCALATED') {
            cardStyle = 'bg-emerald-50/40 border-emerald-200 text-emerald-900 hover:border-emerald-300';
            badgeStyle = 'bg-safety-emerald text-white border-emerald-600';
          }

          return (
            <div
              key={step.id}
              tabIndex={0}
              role="region"
              aria-label={`Protocol Phase ${step.stepNum}: ${step.label}`}
              className={cn(
                "group p-3 rounded-lg border flex flex-col justify-between cursor-default",
                "hover:border-slate-400 hover:shadow-xs active:scale-[0.98] transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1",
                cardStyle
              )}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono-timer font-bold tracking-tight opacity-75">
                  PHASE {step.stepNum}
                </span>
                <span className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border group-hover:scale-105 transition-transform",
                  badgeStyle
                )}>
                  {step.completed ? '✓' : step.stepNum}
                </span>
              </div>
              <div>
                <p className="text-xs font-black tracking-tight leading-snug">
                  {step.label}
                </p>
                <p className="text-[10px] font-medium opacity-80 mt-1">
                  {step.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Audit Context */}
      <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-slate-500">
        <span>AI visual hazard detection → Human supervisor verification & on-site sign-off</span>
        <span className="font-mono-timer text-[10px] text-slate-400 font-bold shrink-0">
          SLA: 20s Resp | 60s Fix
        </span>
      </div>
    </div>
  );
}
