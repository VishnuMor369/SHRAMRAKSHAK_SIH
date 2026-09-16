import React, { useState } from 'react';
import { 
  Shield, 
  RotateCcw, 
  Smartphone, 
  QrCode, 
  Search, 
  Menu,
  CheckCircle2,
  BrainCircuit
} from 'lucide-react';
import { resetDemo } from '../services/api';

export default function Header({ status, onOpenQr, onToggleSidebar, onOpenPassport, onOpenSafetyAnalysis }) {
  const [resetting, setResetting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleReset = async () => {
    try {
      setResetting(true);
      await resetDemo();
    } catch (e) {
      console.error('Failed to reset demo:', e);
    } finally {
      setResetting(false);
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Left: Brand / Sidebar Toggle */}
        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 lg:hidden focus:outline-none"
            aria-label="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-amber-400 shadow-sm">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <span className="text-base font-extrabold tracking-tight text-slate-900">
                SHRAMRAKSHAK
              </span>
            </div>
          </div>
        </div>

        {/* Center: Search Field */}
        <div className="flex-1 max-w-md mx-2 hidden sm:block">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search camera, area or alert..."
              className="w-full pl-9 pr-3 py-1.5 bg-slate-50 hover:bg-slate-100/80 focus:bg-white border border-slate-200 focus:border-amber-500 rounded-lg text-xs text-slate-900 placeholder-slate-400 transition-all outline-none"
            />
          </div>
        </div>

        {/* Right: Status, Mobile Pairing, Reset Demo */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Safety Passport Quick Access */}
          <button
            onClick={onOpenPassport}
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md text-xs font-bold border transition-all ${
              status?.active_passport?.status === 'PAUSED'
                ? 'bg-red-50 hover:bg-red-100 text-red-800 border-red-300 animate-pulse shadow-sm'
                : status?.active_passport?.status === 'ACTIVE'
                ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-300 shadow-sm'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300'
            }`}
            title="Manage High-Risk Start Work Safety Passports"
          >
            <Shield className={`w-3.5 h-3.5 ${
              status?.active_passport?.status === 'PAUSED' 
                ? 'text-red-600' 
                : status?.active_passport?.status === 'ACTIVE'
                ? 'text-emerald-600'
                : 'text-amber-500'
            }`} />
            <span>SAFETY PASSPORT</span>
            {status?.active_passport && (
              <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase ${
                status?.active_passport?.status === 'PAUSED'
                  ? 'bg-red-600 text-white'
                  : status?.active_passport?.status === 'ACTIVE'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-200 text-slate-700'
              }`}>
                {status?.active_passport?.status === 'PAUSED' ? 'PAUSED' : status?.active_passport?.status === 'ACTIVE' ? 'ACTIVE' : 'PENDING'}
              </span>
            )}
          </button>

          {/* AI RISK INTELLIGENCE Quick Access Button (SIH PS 26165) */}
          <button
            onClick={onOpenSafetyAnalysis}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md text-xs font-bold border transition-all bg-blue-50 hover:bg-blue-100 text-blue-900 border-blue-200 shadow-sm"
            title="AI Risk Intelligence & Explainable SIF Precursor Pathways"
          >
            <BrainCircuit className="w-3.5 h-3.5 text-blue-600" />
            <span className="hidden sm:inline">AI RISK INTELLIGENCE</span>
            <span className="sm:hidden">RISK AI</span>
            <span className="px-1 py-0.5 rounded text-[9px] font-black uppercase bg-blue-600 text-white">
              NLP
            </span>
          </button>

          {/* System Online Indicator */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
            </span>
            <span className="hidden md:inline">SYSTEM ONLINE</span>
            <span className="md:hidden">ONLINE</span>
          </div>

          {/* Mobile Supervisor Access */}
          <button
            onClick={onOpenQr}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200/90 text-slate-700 text-xs font-medium border border-slate-300 transition-colors"
            title="Open supervisor dashboard on mobile phone"
          >
            <Smartphone className="w-3.5 h-3.5 text-slate-600" />
            <span className="hidden lg:inline">Mobile Supervisor</span>
            <QrCode className="w-3.5 h-3.5 text-amber-600" />
          </button>

          {/* Reset Demo Button */}
          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white text-xs font-semibold transition-colors shadow-sm disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${resetting ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">RESET DEMO</span>
            <span className="sm:hidden">RESET</span>
          </button>
        </div>
      </div>
    </header>
  );
}
