import React, { useState } from 'react';
import { PlayCircle, ShieldCheck, RotateCcw, AlertTriangle, ChevronDown, ChevronUp, Sliders, ShieldAlert } from 'lucide-react';
import { simulateNoHelmet, simulateSafe, simulateZoneEntry, simulateMultiViolation, resetDemo } from '../services/api';

export default function DemoControls() {
  const [isOpen, setIsOpen] = useState(true);
  const [loading, setLoading] = useState(false);

  const handleSimulateViolation = async () => {
    try {
      setLoading(true);
      await simulateNoHelmet();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateZoneViolation = async () => {
    try {
      setLoading(true);
      await simulateZoneEntry();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateMultiViolation = async () => {
    try {
      setLoading(true);
      await simulateMultiViolation();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateSafe = async () => {
    try {
      setLoading(true);
      await simulateSafe();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      await resetDemo();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="industrial-card border border-slate-300 bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2.5 bg-slate-100 hover:bg-slate-200/80 border-b border-slate-200 flex items-center justify-between text-slate-800 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-slate-600" />
          <span className="text-xs font-black uppercase tracking-wider">
            Presentation Demo Controls & Fallback Mode
          </span>
          <span className="text-[11px] font-medium text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
            Failsafe Tools
          </span>
        </div>
        <div className="flex items-center space-x-1 text-slate-500 text-xs">
          <span>{isOpen ? 'Hide' : 'Show'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-4 bg-slate-50 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-slate-800">
              Manual Simulation Triggers
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5 max-w-md">
              Use these buttons during presentation if webcam angles or lighting make detection difficult. They trigger the exact same alert pipeline.
            </p>
          </div>

          <div className="flex items-center flex-wrap gap-2.5">
            <button
              onClick={handleSimulateViolation}
              disabled={loading}
              className="px-3.5 py-2 rounded-md bg-red-600 hover:bg-red-700 active:bg-red-800 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>SIMULATE NO HELMET</span>
            </button>

            <button
              onClick={handleSimulateZoneViolation}
              disabled={loading}
              className="px-3.5 py-2 rounded-md bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>SIMULATE ZONE ENTRY</span>
            </button>

            <button
              onClick={handleSimulateMultiViolation}
              disabled={loading}
              className="px-3.5 py-2 rounded-md bg-purple-700 hover:bg-purple-800 active:bg-purple-900 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>SIMULATE DUAL HAZARD (ZONE + 2 NO-HELMET)</span>
            </button>

            <button
              onClick={handleSimulateSafe}
              disabled={loading}
              className="px-3.5 py-2 rounded-md bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>SIMULATE SAFE</span>
            </button>

            <button
              onClick={handleReset}
              disabled={loading}
              className="px-3.5 py-2 rounded-md bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>RESET DEMO</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
