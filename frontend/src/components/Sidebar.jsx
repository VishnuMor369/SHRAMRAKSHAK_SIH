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
  BarChart3,
  SlidersHorizontal,
  X
} from 'lucide-react';

export default function Sidebar({ isOpen, onClose, activeTab = 'HOME', onTabChange, activeAlertsCount = 0 }) {
  // Normalize activeTab for highlighting
  const currentTab = (activeTab || 'HOME').toUpperCase();

  const isTabActive = (id, aliases = []) => {
    if (currentTab === id) return true;
    return aliases.some(alias => currentTab === alias);
  };

  const navSections = [
    {
      title: 'PRIMARY OPERATIONS',
      items: [
        { 
          id: 'HOME', 
          aliases: ['OVERVIEW', 'DASHBOARD'], 
          label: '1. HOME', 
          icon: LayoutDashboard, 
          description: 'Current Safety Status' 
        },
        { 
          id: 'REPORTS', 
          aliases: ['SAFETY REPORTS'], 
          label: '2. SAFETY REPORTS', 
          icon: FileText, 
          badge: 'NLP SIF',
          description: 'Report Analysis Workspace' 
        },
        { 
          id: 'INTELLIGENCE', 
          aliases: ['SAFETY INTELLIGENCE', 'AI RISK INTELLIGENCE', 'AI SAFETY ANALYSIS'], 
          label: '3. INTELLIGENCE', 
          icon: BrainCircuit, 
          badge: 'AGGREGATED',
          description: 'Fatal Precursor Trends' 
        },
        { 
          id: 'SAFETY MEMORY', 
          aliases: [], 
          label: '4. SAFETY MEMORY', 
          icon: Database, 
          badge: 'RECURRENCE',
          description: 'Patterns & Preconditions' 
        },
        { 
          id: 'LIVE SAFETY', 
          aliases: ['LIVE MONITORING'], 
          label: '5. LIVE SAFETY', 
          icon: Video, 
          badge: 'CCTV',
          description: 'Field Zones & Passport' 
        },
        { 
          id: 'ACTIONS', 
          aliases: ['ACTIONS & VERIFICATION', 'ACTIONS / VERIFICATION', 'ALERTS'], 
          label: '6. ACTIONS & VERIFICATION', 
          icon: CheckCircle2, 
          badge: activeAlertsCount > 0 ? `${activeAlertsCount}` : null,
          badgeClass: activeAlertsCount > 0 ? 'bg-red-500/20 text-red-400 border-red-500/30' : null,
          description: 'Closed-Loop Verification' 
        },
      ]
    },
    {
      title: 'DATA',
      items: [
        { 
          id: 'DATASETS', 
          aliases: ['IMPORT DATA', 'DATASET INTELLIGENCE'], 
          label: '7. DATASETS', 
          icon: FileSpreadsheet, 
          badge: 'CSV/PDF',
          description: 'External Data Ingestion' 
        },
        { 
          id: 'ANALYSIS RUNS', 
          aliases: ['DATASET ANALYSIS'], 
          label: '8. ANALYSIS RUNS', 
          icon: BarChart3, 
          badge: 'REPORTS',
          description: 'Run Catalog & PDF' 
        },
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { 
          id: 'DEMO / SETTINGS', 
          aliases: ['SETTINGS / DEMO', 'SETTINGS', 'DEMO'], 
          label: '9. DEMO / SETTINGS', 
          icon: SlidersHorizontal, 
          badge: 'DEMO',
          description: 'Session & Simulation' 
        },
      ]
    }
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
                HSE AI COMMAND • OIL INDIA
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

        {/* Navigation List Grouped by 3 Sections */}
        <nav className="flex-1 px-3 py-3 space-y-4 overflow-y-auto">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              <div className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                {section.title}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = isTabActive(item.id, item.aliases);

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      if (onTabChange) onTabChange(item.id);
                      if (onClose) onClose();
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all text-left ${
                      active 
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm' 
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-amber-400' : 'text-slate-400'}`} />
                      <span className="truncate">{item.label}</span>
                    </div>

                    <div className="flex items-center space-x-1.5 shrink-0 ml-2">
                      {item.badge && (
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border ${item.badgeClass || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
                          {item.badge}
                        </span>
                      )}
                      {active && (
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* System Node / Edge Device Status Footer */}
        <div className="p-3 m-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs shrink-0">
          <div className="flex items-center justify-between text-[11px] mb-1">
            <span className="text-slate-400 font-medium">Vision Edge Node</span>
            <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-pulse"></span>
              ONLINE
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-300">
            <span className="font-mono text-slate-400">Node: C-01 (Rig 04)</span>
            <span className="text-[10px] text-amber-400/90 font-mono font-bold">NLP Active</span>
          </div>
        </div>
      </aside>
    </>
  );
}
