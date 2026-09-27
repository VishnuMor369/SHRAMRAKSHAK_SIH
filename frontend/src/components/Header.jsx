import React, { useState } from 'react';
import { 
  Shield, 
  RotateCcw, 
  Smartphone, 
  QrCode, 
  Menu
} from 'lucide-react';
import { resetDemo } from '../services/api';
import { cn } from '@/lib/utils';

export default function Header({ status, onOpenQr, onToggleSidebar }) {
  const [resetting, setResetting] = useState(false);

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
    <header className="sticky top-0 z-30 bg-white/75 backdrop-blur-md border-b border-slate-200/70 shadow-xs transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Left: Brand / Sidebar Toggle */}
        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 lg:hidden transition-all"
            aria-label="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-safety-dark flex items-center justify-center text-amber-400 shadow-2xs">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <span className="text-base font-extrabold tracking-tight text-safety-dark">
                SHRAMRAKSHAK
              </span>
            </div>
          </div>
        </div>

        {/* Right: System Status, Scanner, Reset Demo */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* System Online Status Indicator */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50/90 border border-emerald-200 text-safety-emerald text-xs font-bold shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-safety-emerald"></span>
            <span className="hidden sm:inline">SYSTEM ONLINE</span>
            <span className="sm:hidden">ONLINE</span>
          </div>

          {/* Scanner / Mobile Supervisor Button */}
          <button
            onClick={onOpenQr}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-white/80 hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/10 shadow-2xs"
            title="Scanner / Mobile Supervisor QR"
            aria-label="Scanner"
          >
            <Smartphone className="w-3.5 h-3.5 text-slate-600" />
            <QrCode className="w-3.5 h-3.5 text-safety-amber" />
          </button>

          {/* Reset Demo Button */}
          <button
            onClick={handleReset}
            disabled={resetting}
            className="flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg bg-safety-dark hover:bg-slate-800 active:scale-[0.98] text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
          >
            <RotateCcw className={cn('w-3.5 h-3.5', resetting && 'animate-spin')} />
            <span className="hidden md:inline">RESET DEMO</span>
            <span className="md:hidden">RESET</span>
          </button>
        </div>
      </div>
    </header>
  );
}
