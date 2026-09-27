import React from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  FileText,
  BrainCircuit,
  Database,
  Video, 
  CheckCircle2, 
  FileSpreadsheet,
  SlidersHorizontal,
  X, 
  Bell,
  BarChart3,
  History
} from 'lucide-react';

export default function Sidebar({ isOpen, onClose, activeTab = 'OVERVIEW', onTabChange, activeAlertsCount = 0 }) {
  const navItems = [
    { id: 'OVERVIEW', label: '1. OVERVIEW', icon: LayoutDashboard },
    { id: 'REPORTS', label: '2. REPORTS', icon: FileText, badge: 'UNIFIED' },
    { id: 'SAFETY INTELLIGENCE', label: '3. SAFETY INTELLIGENCE', icon: BrainCircuit, badge: 'NLP SIF' },
    { id: 'SAFETY MEMORY', label: '4. SAFETY MEMORY', icon: Database, badge: 'RECURRENCE' },
    { id: 'LIVE SAFETY', label: '5. LIVE SAFETY', icon: Video, badge: 'CCTV' },
    { id: 'ACTIONS', label: '6. ACTIONS', icon: CheckCircle2, badge: activeAlertsCount > 0 ? `${activeAlertsCount}` : null, badgeClass: activeAlertsCount > 0 ? 'bg-red-500/20 text-red-400 border-red-500/30' : null },
    { id: 'IMPORT DATA', label: '7. DATASET INTELLIGENCE', icon: FileSpreadsheet, badge: 'UPLOAD' },
    { id: 'DATASET ANALYSIS', label: '8. DATASET ANALYSIS', icon: BarChart3, badge: 'AR RUNS' },
    { id: 'ANALYSIS RUNS', label: '9. ANALYSIS RUNS', icon: History, badge: 'PDF' },
    { id: 'SETTINGS / DEMO', label: '10. SETTINGS / DEMO', icon: SlidersHorizontal, badge: 'DEMO' },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/60 z-40 lg:hidden backdrop-blur-sm transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside 
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 text-slate-200 flex flex-col border-r border-slate-800 transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-800/80 bg-slate-950/50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-sm">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-extrabold tracking-tight text-white">
                  SHRAMRAKSHAK
                </span>
              </div>
              <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase block">
                HSE AI COMMAND
              </span>
            </div>
          </div>

          {/* Close button on mobile */}
          <button 
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation List */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Main Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isItemActive = item.id === activeTab;

            return (
              <button
                key={item.id}
                onClick={() => {
                  if (onTabChange) onTabChange(item.id);
                  if (onClose) onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                  isItemActive 
                    ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm' 
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isItemActive ? 'text-amber-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {item.badge && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold border ${item.badgeClass || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
                      {item.badge}
                    </span>
                  )}
                  {isItemActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                  )}
                </div>
              </button>
            );
          })}
        </nav>

        {/* System Node / Edge Device Status Footer */}
        <div className="p-3.5 m-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs">
          <div className="flex items-center justify-between text-[11px] mb-1.5">
            <span className="text-slate-400 font-medium">Vision Edge Node</span>
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-pulse"></span>
              ONLINE
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-300">
            <span className="font-mono text-slate-400">Node: C-01 (Laptop)</span>
            <span className="text-[10px] text-amber-400/90 font-mono font-bold">YOLO-Pose</span>
          </div>
        </div>
      </aside>
    </>
  );
}
