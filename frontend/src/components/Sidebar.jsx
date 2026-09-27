import React from 'react';
import { 
  Shield, 
  LayoutDashboard, 
  Video, 
  MapPin, 
  Bell, 
  X, 
  BrainCircuit,
  FileText
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Sidebar({ isOpen, onClose, activeTab = 'Dashboard', onTabChange, activeAlertsCount = 0, hasActivePassport = false }) {
  const navItems = [
    { id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'HSE Observation', label: 'HSE Observation', icon: FileText, badge: 'FIELD' },
    { id: 'Safety Passport', label: 'Safety Passport', icon: Shield, badge: hasActivePassport ? 'ACTIVE' : null },
    { id: 'AI Risk Intelligence', label: 'AI Risk Intelligence', icon: BrainCircuit, badge: 'NLP' },
    { id: 'Live Monitoring', label: 'Live Monitoring', icon: Video, badge: 'C-01' },
    { id: 'Alerts', label: 'Alerts', icon: Bell, badge: activeAlertsCount > 0 ? `${activeAlertsCount}` : null, badgeClass: activeAlertsCount > 0 ? 'bg-safety-crimson text-white' : null },
    { id: 'Locations / Zones', label: 'Locations / Zones', icon: MapPin },
  ];

  return (
    <>
      {/* Mobile Backdrop with blur */}
      {isOpen && (
        <div 
          onClick={onClose}
          className="fixed inset-0 bg-slate-950/60 z-40 lg:hidden backdrop-blur-sm transition-opacity"
        />
      )}

      {/* Sidebar Container with frosted glass on dark chrome */}
      <aside 
        className={cn(
          'fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900/90 backdrop-blur-xl text-slate-200 flex flex-col border-r border-slate-800/80 transition-transform duration-200 ease-in-out lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-2xs">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-extrabold tracking-tight text-white">
                  SHRAMRAKSHAK
                </span>
              </div>
              <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase block">
                HSE AI Command
              </span>
            </div>
          </div>

          {/* Close button on mobile */}
          <button 
            onClick={onClose}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden transition-colors active:scale-[0.98]"
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
                className={cn(
                  'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400',
                  isItemActive 
                    ? 'bg-amber-500/15 text-amber-400 border-l-4 border-l-amber-400 rounded-l-none border-y border-r border-amber-500/20 shadow-xs font-bold' 
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                )}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={cn('w-4 h-4 transition-colors', isItemActive ? 'text-amber-400' : 'text-slate-400')} />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {item.badge && (
                    <span className={cn(
                      'px-1.5 py-0.2 rounded text-[10px] font-mono-timer font-bold border',
                      item.badgeClass || 'bg-slate-800 text-slate-300 border-slate-700'
                    )}>
                      {item.badge}
                    </span>
                  )}
                  {isItemActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  )}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Vision Edge Status Footer */}
        <div className="p-3.5 m-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs shadow-2xs">
          <div className="flex items-center justify-between text-[11px] mb-1.5">
            <span className="text-slate-400 font-medium">Vision Edge Node</span>
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/80">
              <span className="w-1.5 h-1.5 rounded-full bg-safety-green mr-1"></span>
              ONLINE
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-300">
            <span className="font-mono-timer text-slate-400">Node: C-01 (Laptop)</span>
            <span className="text-[10px] text-amber-400/90 font-mono-timer font-bold">YOLO-Pose</span>
          </div>
        </div>
      </aside>
    </>
  );
}
