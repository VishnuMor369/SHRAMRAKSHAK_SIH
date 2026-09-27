import React, { useState } from 'react';
import { 
  Shield, 
  ShieldAlert, 
  AlertTriangle, 
  Clock, 
  CheckCircle2, 
  ShieldCheck, 
  Activity, 
  Eye, 
  Maximize2, 
  Radio, 
  Terminal, 
  Sliders, 
  Zap, 
  Check, 
  ArrowRight,
  Flame,
  AlertOctagon
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function DesignPreviewDirections({ status, alerts = [], onSelectDirection }) {
  const [activeDirection, setActiveDirection] = useState('direction1');
  const [simulateAlert, setSimulateAlert] = useState(false);

  // Metric values
  const sifCount = simulateAlert ? 1 : (status?.sif_potential_count ?? 0);
  const activeAlertsCount = simulateAlert ? 2 : (alerts?.length > 0 ? alerts.length : (status?.active_alert ? 1 : 0));
  const openActionsCount = status?.open_actions_count ?? 0;
  const awaitingCount = status?.awaiting_verification_count ?? 0;
  const verifiedCount = status?.verified_count ?? 0;

  const formatNum = (num) => String(num ?? 0).padStart(2, '0');

  return (
    <div className="w-full space-y-6">
      {/* ============================================================ */}
      {/* DIRECTION SWITCHER CONTROL BAR                               */}
      {/* ============================================================ */}
      <div className="bg-slate-900 text-white rounded-2xl p-4 sm:p-5 shadow-lg border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest bg-amber-500 text-slate-950">
                Design System Audition
              </span>
              <span className="text-xs font-mono text-slate-400">
                3 Working Directions • Live Side-by-Side
              </span>
            </div>
            <h2 className="text-lg font-black tracking-tight text-white mt-1">
              Select Visual Direction for SHRAMRAKSHAK
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Compare Nav + KPI Cards + Content Panel across 3 distinct design philosophies.
            </p>
          </div>

          {/* Test State Simulator */}
          <div className="flex items-center space-x-3 bg-slate-800/80 p-2 rounded-xl border border-slate-700">
            <span className="text-xs font-semibold text-slate-300">Hazard State:</span>
            <button
              onClick={() => setSimulateAlert(!simulateAlert)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5',
                simulateAlert
                  ? 'bg-safety-crimson text-white shadow-xs'
                  : 'bg-safety-emerald text-white shadow-xs'
              )}
            >
              {simulateAlert ? (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Simulated SIF Alert: ON</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Normal Shift: CLEAR</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Direction Switcher Tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-4">
          {/* Tab 1 */}
          <button
            onClick={() => setActiveDirection('direction1')}
            className={cn(
              'p-3 rounded-xl border text-left transition-all',
              activeDirection === 'direction1'
                ? 'bg-slate-800 border-amber-400 ring-1 ring-amber-400/50 text-white'
                : 'bg-slate-800/40 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-wider text-amber-400">
                Direction 1
              </span>
              {activeDirection === 'direction1' && <Check className="w-4 h-4 text-amber-400" />}
            </div>
            <div className="text-sm font-bold text-white mt-1">Industrial Telemetry</div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Mission Control / SCADA feel: hairline grid borders, high data density, tabular mono metrics, zero fluff.
            </p>
          </button>

          {/* Tab 2 */}
          <button
            onClick={() => setActiveDirection('direction2')}
            className={cn(
              'p-3 rounded-xl border text-left transition-all',
              activeDirection === 'direction2'
                ? 'bg-slate-800 border-amber-400 ring-1 ring-amber-400/50 text-white'
                : 'bg-slate-800/40 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-wider text-amber-400">
                Direction 2
              </span>
              {activeDirection === 'direction2' && <Check className="w-4 h-4 text-amber-400" />}
            </div>
            <div className="text-sm font-bold text-white mt-1">Tactical HUD</div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Field Command / Ruggedized: bold 2px frames, brutalist tactile shadows, high-visibility badges for rapid scan.
            </p>
          </button>

          {/* Tab 3 */}
          <button
            onClick={() => setActiveDirection('direction3')}
            className={cn(
              'p-3 rounded-xl border text-left transition-all',
              activeDirection === 'direction3'
                ? 'bg-slate-800 border-amber-400 ring-1 ring-amber-400/50 text-white'
                : 'bg-slate-800/40 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-wider text-amber-400">
                Direction 3
              </span>
              {activeDirection === 'direction3' && <Check className="w-4 h-4 text-amber-400" />}
            </div>
            <div className="text-sm font-bold text-white mt-1">Swiss Minimalist HSE</div>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              Linear-Style Rigor: whisper-quiet surfaces, soft floating borders, pure typography, safety colors command focus.
            </p>
          </button>
        </div>
      </div>

      {/* ============================================================ */}
      {/* DIRECTION 1: INDUSTRIAL TELEMETRY (MISSION CONTROL / SCADA)   */}
      {/* ============================================================ */}
      {activeDirection === 'direction1' && (
        <div className="space-y-4 rounded-xl border border-slate-300 p-4 sm:p-5 bg-slate-100/70 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-slate-300">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 font-mono">
              PREVIEW // DIRECTION 1 — INDUSTRIAL TELEMETRY (SCADA)
            </span>
            <span className="text-[10px] font-mono bg-slate-200 px-2 py-0.5 rounded text-slate-700">
              DENSITY: HIGH • HAILINE GRIDS • TABULAR MONO
            </span>
          </div>

          {/* 1.1 Direction 1 Nav Bar */}
          <header className="bg-safety-slate text-white border border-slate-800 rounded-sm px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-1.5 font-bold tracking-tight text-amber-400">
                <Terminal className="w-4 h-4" />
                <span className="font-sans font-black text-white text-sm">SHRAMRAKSHAK</span>
                <span className="text-[10px] text-amber-400 font-mono">// SCADA-OS</span>
              </div>
              <span className="text-slate-600">|</span>
              <span className="text-[11px] text-slate-300">
                ZONE: <strong>UNIT-04 (COMPRESSOR)</strong>
              </span>
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1.5 text-[11px]">
                <span className="w-2 h-2 bg-safety-green"></span>
                <span className="text-slate-300 font-semibold">FEED: C-01 (ONLINE)</span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono-timer tabular-nums">
                25-SEP-2026 02:54:12 UTC
              </div>
              <div className="bg-slate-800 border border-slate-700 px-2 py-1 text-[10px] font-mono text-amber-300">
                LATENCY: 14ms
              </div>
            </div>
          </header>

          {/* 1.2 Direction 1 KPI Metric Grid (Connected SCADA Rack) */}
          <div className="grid grid-cols-2 sm:grid-cols-5 border border-slate-300 divide-x divide-y sm:divide-y-0 divide-slate-300 bg-white rounded-sm shadow-xs overflow-hidden">
            {/* Card 1 */}
            <div className={cn(
              'p-3 transition-colors flex flex-col justify-between',
              sifCount > 0 ? 'bg-red-50 text-safety-crimson' : 'bg-white text-slate-900'
            )}>
              <div className="flex items-center justify-between text-[10px] font-mono font-bold tracking-wider">
                <span>01 // SIF POTENTIAL</span>
                <ShieldAlert className="w-3.5 h-3.5" />
              </div>
              <div className="my-1.5">
                <span className="text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums">
                  {formatNum(sifCount)}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 truncate">
                {sifCount > 0 ? 'CRITICAL PRECURSOR' : 'STATUS: NOMINAL'}
              </span>
            </div>

            {/* Card 2 */}
            <div className={cn(
              'p-3 transition-colors flex flex-col justify-between',
              activeAlertsCount > 0 ? 'bg-amber-50 text-amber-900' : 'bg-white text-slate-900'
            )}>
              <div className="flex items-center justify-between text-[10px] font-mono font-bold tracking-wider">
                <span>02 // ACTIVE ALERTS</span>
                <AlertTriangle className="w-3.5 h-3.5" />
              </div>
              <div className="my-1.5">
                <span className="text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums text-amber-800">
                  {formatNum(activeAlertsCount)}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 truncate">
                {activeAlertsCount > 0 ? 'UNRESOLVED HAZARDS' : 'PERIMETER SECURE'}
              </span>
            </div>

            {/* Card 3 */}
            <div className="p-3 bg-white flex flex-col justify-between">
              <div className="flex items-center justify-between text-[10px] font-mono font-bold tracking-wider text-slate-500">
                <span>03 // OPEN ACTIONS</span>
                <Clock className="w-3.5 h-3.5 text-blue-600" />
              </div>
              <div className="my-1.5">
                <span className="text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums text-safety-dark">
                  {formatNum(openActionsCount)}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 truncate">
                DISPATCHED FIELD LOGS
              </span>
            </div>

            {/* Card 4 */}
            <div className="p-3 bg-white flex flex-col justify-between">
              <div className="flex items-center justify-between text-[10px] font-mono font-bold tracking-wider text-slate-500">
                <span>04 // VERIFICATION</span>
                <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
              </div>
              <div className="my-1.5">
                <span className="text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums text-safety-dark">
                  {formatNum(awaitingCount)}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 truncate">
                AUDIT QUEUE PENDING
              </span>
            </div>

            {/* Card 5 */}
            <div className="p-3 bg-white flex flex-col justify-between col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between text-[10px] font-mono font-bold tracking-wider text-slate-500">
                <span>05 // VERIFIED</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-safety-emerald" />
              </div>
              <div className="my-1.5">
                <span className="text-2xl sm:text-3xl font-black font-mono-timer tracking-tight tabular-nums text-safety-emerald">
                  {formatNum(verifiedCount)}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-500 truncate">
                SIGN-OFF VERIFIED
              </span>
            </div>
          </div>

          {/* 1.3 Direction 1 Content Panel (Industrial Exclusion Terminal) */}
          <div className="border border-slate-300 rounded-sm bg-white overflow-hidden shadow-xs">
            <div className="bg-slate-900 text-slate-200 px-4 py-2 border-b border-slate-800 flex items-center justify-between font-mono text-xs">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-amber-400"></span>
                <span className="font-bold text-white uppercase tracking-wider">
                  TELEMETRY CHANNEL 01 // EXCLUSION BOUNDARY
                </span>
              </div>
              <span className="text-[10px] text-slate-400">FPS: 30 • CONFIDENCE: 98%</span>
            </div>

            <div className="p-4 space-y-3 font-mono text-xs">
              <div className={cn(
                'p-3 border rounded-sm flex items-center justify-between',
                sifCount > 0
                  ? 'bg-red-50 border-safety-crimson text-safety-crimson font-bold'
                  : 'bg-slate-50 border-slate-200 text-slate-800'
              )}>
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                    EXCLUSION ZONE STATUS
                  </div>
                  <div className="text-sm font-sans font-black mt-0.5">
                    {sifCount > 0 ? 'BREACH ACTIVE — WORKER DETECTED IN HIGH-PRESSURE ZONE' : 'PERIMETER INTEGRITY NOMINAL'}
                  </div>
                </div>
                <div className="text-right">
                  <span className={cn(
                    'px-2.5 py-1 text-[10px] font-black uppercase tracking-wider inline-block rounded-none border',
                    sifCount > 0 ? 'bg-safety-crimson text-white border-safety-crimson' : 'bg-emerald-100 text-safety-emerald border-emerald-300'
                  )}>
                    {sifCount > 0 ? 'ALERT CODE: SIF-01' : 'STATUS: ARMED'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px]">
                <div className="p-2 border border-slate-200 bg-slate-50/50">
                  <span className="text-slate-500 block uppercase">ENGINE MODE</span>
                  <strong className="text-slate-900 font-sans">YOLO-Pose (Feet Contact)</strong>
                </div>
                <div className="p-2 border border-slate-200 bg-slate-50/50">
                  <span className="text-slate-500 block uppercase">POLYGON COORDINATES</span>
                  <strong className="text-slate-900 font-mono">4-POINT PERIMETER</strong>
                </div>
                <div className="p-2 border border-slate-200 bg-slate-50/50">
                  <span className="text-slate-500 block uppercase">SUPERVISOR ACK</span>
                  <strong className={sifCount > 0 ? 'text-red-700 font-sans' : 'text-slate-700 font-sans'}>
                    {sifCount > 0 ? 'REQUIRED IMMEDIATELY' : 'STANDBY'}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* DIRECTION 2: TACTICAL HUD (FIELD COMMAND / RUGGEDIZED)         */}
      {/* ============================================================ */}
      {activeDirection === 'direction2' && (
        <div className="space-y-4 rounded-xl border-2 border-slate-900 p-4 sm:p-5 bg-amber-50/30 shadow-[4px_4px_0px_0px_#0F172A]">
          <div className="flex items-center justify-between pb-2 border-b-2 border-slate-900">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-900 font-sans">
              PREVIEW // DIRECTION 2 — TACTICAL HUD (FIELD COMMAND)
            </span>
            <span className="text-[10px] font-black bg-slate-900 text-white px-2 py-0.5 rounded-none uppercase">
              RUGGEDIZED • 2PX FRAMES • HIGH CONTRAST
            </span>
          </div>

          {/* 2.1 Direction 2 Nav Bar */}
          <header className="bg-white border-2 border-slate-900 shadow-[3px_3px_0px_0px_#0F172A] px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-slate-900 text-white flex items-center justify-center font-black rounded-none">
                <Shield className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h1 className="text-base font-black text-slate-950 uppercase tracking-tight leading-none">
                  SHRAMRAKSHAK // HUD
                </h1>
                <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                  FIELD OPERATIONAL COMMAND
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 bg-amber-400 border border-slate-900 text-slate-950 text-[11px] font-black uppercase">
                SHIFT A • LEAD SUP-01
              </span>
              <span className="px-2.5 py-1 bg-slate-900 text-white text-[11px] font-black uppercase">
                CAM C-01 LIVE
              </span>
            </div>
          </header>

          {/* 2.2 Direction 2 KPI Cards (Tactical Modular Blocks) */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {/* Card 1 */}
            <div className={cn(
              'p-3.5 border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] flex flex-col justify-between transition-transform active:translate-x-0.5 active:translate-y-0.5',
              sifCount > 0 && 'bg-red-100 border-safety-crimson ring-2 ring-safety-red/40'
            )}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-900">
                  SIF POTENTIAL
                </span>
                <div className={cn('p-1 rounded-none border border-slate-900', sifCount > 0 ? 'bg-safety-crimson text-white' : 'bg-slate-100 text-slate-900')}>
                  <ShieldAlert className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="my-2">
                <span className={cn('text-3xl font-black font-mono-timer tabular-nums tracking-tighter', sifCount > 0 ? 'text-safety-crimson' : 'text-slate-950')}>
                  {formatNum(sifCount)}
                </span>
              </div>
              <span className={cn('text-[10px] font-black uppercase', sifCount > 0 ? 'text-safety-crimson' : 'text-slate-600')}>
                {sifCount > 0 ? 'PRECURSOR DETECTED' : 'CLEAR'}
              </span>
            </div>

            {/* Card 2 */}
            <div className={cn(
              'p-3.5 border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] flex flex-col justify-between transition-transform active:translate-x-0.5 active:translate-y-0.5',
              activeAlertsCount > 0 && 'bg-amber-100 border-amber-800'
            )}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-900">
                  ACTIVE ALERTS
                </span>
                <div className={cn('p-1 rounded-none border border-slate-900', activeAlertsCount > 0 ? 'bg-safety-amber text-slate-950' : 'bg-slate-100 text-slate-900')}>
                  <AlertTriangle className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="my-2">
                <span className="text-3xl font-black font-mono-timer tabular-nums tracking-tighter text-amber-900">
                  {formatNum(activeAlertsCount)}
                </span>
              </div>
              <span className="text-[10px] font-black uppercase text-slate-700">
                {activeAlertsCount > 0 ? 'ACTION REQUIRED' : 'ZERO INCIDENTS'}
              </span>
            </div>

            {/* Card 3 */}
            <div className="p-3.5 border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-900">
                  OPEN ACTIONS
                </span>
                <div className="p-1 rounded-none border border-slate-900 bg-blue-100 text-blue-900">
                  <Clock className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="my-2">
                <span className="text-3xl font-black font-mono-timer tabular-nums tracking-tighter text-slate-950">
                  {formatNum(openActionsCount)}
                </span>
              </div>
              <span className="text-[10px] font-black uppercase text-slate-600">
                ACTIVE ON SITE
              </span>
            </div>

            {/* Card 4 */}
            <div className="p-3.5 border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-900">
                  AWAITING VERIF.
                </span>
                <div className="p-1 rounded-none border border-slate-900 bg-purple-100 text-purple-900">
                  <ShieldCheck className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="my-2">
                <span className="text-3xl font-black font-mono-timer tabular-nums tracking-tighter text-slate-950">
                  {formatNum(awaitingCount)}
                </span>
              </div>
              <span className="text-[10px] font-black uppercase text-slate-600">
                CCTV AUDIT QUEUE
              </span>
            </div>

            {/* Card 5 */}
            <div className="p-3.5 border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] flex flex-col justify-between col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-900">
                  VERIFIED
                </span>
                <div className="p-1 rounded-none border border-slate-900 bg-emerald-100 text-safety-emerald">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="my-2">
                <span className="text-3xl font-black font-mono-timer tabular-nums tracking-tighter text-safety-emerald">
                  {formatNum(verifiedCount)}
                </span>
              </div>
              <span className="text-[10px] font-black uppercase text-slate-600">
                CONTROLS CLOSED
              </span>
            </div>
          </div>

          {/* 2.3 Direction 2 Content Panel (Tactical Action Board) */}
          <div className="border-2 border-slate-900 bg-white shadow-[3px_3px_0px_0px_#0F172A] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b-2 border-slate-900">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-600"></div>
                <h3 className="text-sm font-black uppercase text-slate-950 tracking-wide">
                  TACTICAL INCIDENT BOARD — C-01 LIVE
                </h3>
              </div>
              <span className="text-xs font-black uppercase bg-slate-100 border border-slate-900 px-2 py-0.5">
                PRIORITY: {sifCount > 0 ? 'CRITICAL P1' : 'MONITORING P4'}
              </span>
            </div>

            <div className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="text-sm font-black text-slate-900">
                  {sifCount > 0 ? 'UNAUTHORIZED OCCUPANCY IN EXCLUSION PERIMETER' : 'ALL MONITORED EQUIPMENT ZONES SECURE'}
                </div>
                <p className="text-xs font-semibold text-slate-600 mt-0.5">
                  Location: Unit 4 Gas Compressor Pad • Mode: Body & Footfall Sensor Grid
                </p>
              </div>

              {sifCount > 0 ? (
                <div className="flex items-center space-x-2 shrink-0">
                  <button className="px-3 py-1.5 bg-safety-crimson text-white font-black text-xs uppercase border-2 border-slate-900 shadow-[2px_2px_0px_0px_#0F172A] active:translate-x-0.5 active:translate-y-0.5">
                    [ DISPATCH RESPONSE ]
                  </button>
                  <button className="px-3 py-1.5 bg-white text-slate-900 font-black text-xs uppercase border-2 border-slate-900 shadow-[2px_2px_0px_0px_#0F172A] active:translate-x-0.5 active:translate-y-0.5">
                    [ TRIGGER HORN ]
                  </button>
                </div>
              ) : (
                <span className="px-3 py-1 bg-emerald-100 border border-slate-900 text-safety-emerald text-xs font-black uppercase">
                  ✓ NO ACTION PENDING
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* DIRECTION 3: SWISS MINIMALIST HSE (LINEAR-STYLE RIGOR)        */}
      {/* ============================================================ */}
      {activeDirection === 'direction3' && (
        <div className="space-y-4 rounded-2xl border border-slate-200/90 p-4 sm:p-5 bg-white shadow-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
              PREVIEW // DIRECTION 3 — SWISS MINIMALIST HSE (LINEAR RIGOR)
            </span>
            <span className="text-[10px] font-semibold text-slate-500">
              QUIET SURFACES • FLOATING CARDS • ACCENT CONCENTRATION
            </span>
          </div>

          {/* 3.1 Direction 3 Nav Bar */}
          <header className="bg-slate-50/80 border border-slate-200/80 rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-7 h-7 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-xs">
                S
              </div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-900 text-sm tracking-tight">Shramrakshak</span>
                <span className="text-slate-300">/</span>
                <span className="text-xs font-medium text-slate-500">Plant HSE Command</span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 text-xs font-medium text-slate-600">
                <span className="w-2 h-2 rounded-full bg-safety-emerald"></span>
                <span>Active Surveillance</span>
              </div>
              <span className="text-slate-200">|</span>
              <button className="text-xs font-bold text-slate-700 hover:text-slate-900 px-3 py-1 rounded-lg bg-white border border-slate-200 shadow-2xs">
                Audit Trail
              </button>
            </div>
          </header>

          {/* 3.2 Direction 3 KPI Cards (Airy Minimalist Tiles) */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
            {/* Card 1 */}
            <div className={cn(
              'p-4 rounded-xl border transition-colors flex flex-col justify-between',
              sifCount > 0
                ? 'bg-red-50/80 border-safety-crimson/50 text-slate-900 ring-1 ring-safety-red/20'
                : 'bg-white border-slate-200/80 hover:border-slate-300 shadow-2xs'
            )}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 tracking-tight">
                  SIF Precursor
                </span>
                <span className={cn('w-2 h-2 rounded-full', sifCount > 0 ? 'bg-safety-crimson' : 'bg-slate-300')} />
              </div>
              <div className="my-2.5">
                <span className={cn('text-3xl font-black font-mono-timer tracking-tight tabular-nums', sifCount > 0 ? 'text-safety-crimson' : 'text-slate-900')}>
                  {formatNum(sifCount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">
                {sifCount > 0 ? 'High potential flagged' : 'No active incident'}
              </p>
            </div>

            {/* Card 2 */}
            <div className={cn(
              'p-4 rounded-xl border transition-colors flex flex-col justify-between',
              activeAlertsCount > 0
                ? 'bg-amber-50/80 border-safety-amber/50 text-slate-900 ring-1 ring-safety-amber/20'
                : 'bg-white border-slate-200/80 hover:border-slate-300 shadow-2xs'
            )}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 tracking-tight">
                  Active Alerts
                </span>
                <span className={cn('w-2 h-2 rounded-full', activeAlertsCount > 0 ? 'bg-safety-amber' : 'bg-slate-300')} />
              </div>
              <div className="my-2.5">
                <span className={cn('text-3xl font-black font-mono-timer tracking-tight tabular-nums', activeAlertsCount > 0 ? 'text-amber-800' : 'text-slate-900')}>
                  {formatNum(activeAlertsCount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">
                {activeAlertsCount > 0 ? 'Requires attention' : 'Perimeter compliant'}
              </p>
            </div>

            {/* Card 3 */}
            <div className="p-4 rounded-xl border border-slate-200/80 hover:border-slate-300 bg-white shadow-2xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 tracking-tight">
                  Open Actions
                </span>
                <span className="w-2 h-2 rounded-full bg-slate-300" />
              </div>
              <div className="my-2.5">
                <span className="text-3xl font-black font-mono-timer tracking-tight tabular-nums text-slate-900">
                  {formatNum(openActionsCount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">
                Under supervisor response
              </p>
            </div>

            {/* Card 4 */}
            <div className="p-4 rounded-xl border border-slate-200/80 hover:border-slate-300 bg-white shadow-2xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 tracking-tight">
                  Verification
                </span>
                <span className="w-2 h-2 rounded-full bg-slate-300" />
              </div>
              <div className="my-2.5">
                <span className="text-3xl font-black font-mono-timer tracking-tight tabular-nums text-slate-900">
                  {formatNum(awaitingCount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">
                Awaiting CCTV audit
              </p>
            </div>

            {/* Card 5 */}
            <div className="p-4 rounded-xl border border-slate-200/80 hover:border-slate-300 bg-white shadow-2xs flex flex-col justify-between col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-500 tracking-tight">
                  Verified Controls
                </span>
                <span className="w-2 h-2 rounded-full bg-safety-emerald" />
              </div>
              <div className="my-2.5">
                <span className="text-3xl font-black font-mono-timer tracking-tight tabular-nums text-safety-emerald">
                  {formatNum(verifiedCount)}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium truncate">
                Shift safety verified
              </p>
            </div>
          </div>

          {/* 3.3 Direction 3 Content Panel (Quiet Minimalist Overview) */}
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-5 shadow-2xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                  Live Perimeter Surveillance
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Camera C-01 • Real-time AI pose detection
                </p>
              </div>
              <span className={cn(
                'px-2.5 py-1 rounded-full text-[11px] font-bold',
                sifCount > 0 ? 'bg-red-100 text-safety-crimson' : 'bg-emerald-100 text-safety-emerald'
              )}>
                {sifCount > 0 ? 'Zone Breach Active' : 'Zone Secure'}
              </span>
            </div>

            <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-1">
                <div className="font-semibold text-slate-800">
                  {sifCount > 0 
                    ? 'Worker body detected inside restricted compressor threshold.' 
                    : 'All personnel cleared from safety buffer perimeter.'}
                </div>
                <div className="text-[11px] text-slate-500">
                  Telemetry: Edge YOLO-Pose • Contact: Feet / Ground Anchor
                </div>
              </div>

              <button className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-xs self-start sm:self-auto transition-colors">
                View CCTV Stream →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
