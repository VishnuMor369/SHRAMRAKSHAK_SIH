import React, { useState } from 'react';
import { 
  Shield, 
  Smartphone, 
  QrCode, 
  Search, 
  Menu,
  BrainCircuit,
  Activity,
  CheckCircle2
} from 'lucide-react';

export default function Header({ status, onOpenQr, onToggleSidebar, onOpenPassport, onOpenSafetyAnalysis }) {
  const [searchQuery, setSearchQuery] = useState('');

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
              <span className="hidden sm:inline-block ml-2 px-1.5 py-0.5 rounded text-[9px] font-black uppercase bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                SIH26165 • OIL INDIA
              </span>
            </div>
          </div>
        </div>

        {/* Center: Search Field */}
        <div className="flex-1 max-w-md mx-2 hidden md:block">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search camera, restricted area, or safety event..."
              className="w-full pl-9 pr-3 py-1.5 bg-slate-50 hover:bg-slate-100/80 focus:bg-white border border-slate-200 focus:border-amber-500 rounded-lg text-xs text-slate-900 placeholder-slate-400 transition-all outline-none"
            />
          </div>
        </div>

        {/* Right: Operational Status, Safety Passport & Mobile Access */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Safety Passport Quick Access */}
          <button
            onClick={onOpenPassport}
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold border transition-all ${
              status?.active_passport?.status === 'PAUSED'
                ? 'bg-red-50 hover:bg-red-100 text-red-800 border-red-300 animate-pulse shadow-sm'
                : status?.active_passport?.status === 'ACTIVE'
                ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-300 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
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
            <span className="hidden sm:inline">SAFETY PASSPORT</span>
            <span className="sm:hidden">PASSPORT</span>
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

          {/* AI Intelligence Quick Access Button */}
          <button
            onClick={onOpenSafetyAnalysis}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold border transition-all bg-amber-50 hover:bg-amber-100 text-amber-900 border-amber-200 shadow-sm"
            title="AI Risk Intelligence & Explainable SIF Precursor Pathways"
          >
            <BrainCircuit className="w-3.5 h-3.5 text-amber-600" />
            <span className="hidden lg:inline">INTELLIGENCE</span>
            <span className="px-1 py-0.5 rounded text-[9px] font-black uppercase bg-amber-600 text-white">
              SIF
            </span>
          </button>

          {/* System Online Indicator */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
            </span>
            <span className="hidden sm:inline">NODE ONLINE</span>
            <span className="sm:hidden">LIVE</span>
          </div>

          {/* Mobile Supervisor Access */}
          <button
            onClick={onOpenQr}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium border border-slate-300 transition-colors shadow-sm"
            title="Open supervisor dashboard on mobile phone"
          >
            <Smartphone className="w-3.5 h-3.5 text-slate-600" />
            <span className="hidden xl:inline">Mobile Supervisor</span>
            <QrCode className="w-3.5 h-3.5 text-amber-600" />
          </button>
        </div>
      </div>
    </header>
  );
}
