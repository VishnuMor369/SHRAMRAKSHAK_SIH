import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  AlertOctagon, 
  MapPin, 
  Activity, 
  Eye, 
  Power, 
  Trash2, 
  RotateCcw, 
  Loader2 
} from 'lucide-react';
import { toggleZone, deleteZone, restoreDefaultZone } from '../services/api';
import { cn } from '@/lib/utils';

export default function ZoneStatusCard({ status, onDefineZone }) {
  const activeZone = status?.active_zone;
  const [localEnabled, setLocalEnabled] = useState(null);
  const [isDeleted, setIsDeleted] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Sync with incoming status updates
  useEffect(() => {
    if (activeZone && activeZone.polygon && activeZone.polygon.length >= 3) {
      setLocalEnabled(activeZone.enabled ?? false);
      setIsDeleted(false);
    } else {
      setIsDeleted(true);
    }
  }, [activeZone?.zone_id, activeZone?.enabled, activeZone?.polygon?.length]);

  const effectiveZone = !isDeleted ? activeZone : null;
  const hasZone = !!(effectiveZone && effectiveZone.polygon && effectiveZone.polygon.length >= 3);
  const isEnabled = hasZone && (localEnabled !== null ? localEnabled : (effectiveZone?.enabled ?? false));
  const zoneViolation = (isEnabled && !isDeleted) ? (status?.zone_violation ?? false) : false;
  const personsInZone = (isEnabled && !isDeleted) ? (status?.persons_in_zone ?? 0) : 0;

  const handleToggle = async () => {
    if (actionLoading) return;
    const nextState = !isEnabled;
    setLocalEnabled(nextState);
    setActionLoading(true);
    try {
      await toggleZone(activeZone?.zone_id || 'ZONE-001');
    } catch (err) {
      console.error('Failed to toggle zone:', err);
      // Revert optimistic state on error
      setLocalEnabled(!nextState);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (actionLoading) return;
    setIsDeleted(true);
    setActionLoading(true);
    try {
      await deleteZone(activeZone?.zone_id || 'ZONE-001');
    } catch (err) {
      console.error('Failed to delete zone:', err);
      setIsDeleted(false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestore = async () => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      await restoreDefaultZone();
      setIsDeleted(false);
      setLocalEnabled(true);
    } catch (err) {
      console.error('Failed to restore default zone:', err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div
      className={cn(
        'rounded-xl border transition-colors shadow-xs overflow-hidden',
        zoneViolation
          ? 'border-safety-crimson/50 bg-red-50/40 ring-1 ring-safety-red/20'
          : hasZone
          ? 'border-slate-200 bg-white'
          : 'border-dashed border-slate-300 bg-slate-50/50'
      )}
    >
      {/* Card Header */}
      <div
        className={cn(
          'px-4 py-2.5 flex items-center justify-between border-b',
          zoneViolation
            ? 'bg-safety-crimson text-white border-safety-crimson'
            : 'bg-safety-slate text-white border-slate-800'
        )}
      >
        <div className="flex items-center space-x-2">
          {zoneViolation ? (
            <AlertOctagon className="w-4 h-4 text-white shrink-0" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-safety-amber shrink-0" />
          )}
          <span className="text-xs font-black uppercase tracking-wider">
            Safety Restricted Zones — C-01
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {hasZone && (
            <span
              className={cn(
                'px-2 py-0.5 rounded text-[10px] font-bold tracking-wider',
                isEnabled
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-700 text-slate-400'
              )}
            >
              {isEnabled ? 'ENABLED' : 'DISABLED'}
            </span>
          )}
          <span className="text-xs font-mono-timer font-semibold text-slate-300">
            CAM C-01
          </span>
        </div>
      </div>

      <div className="p-4 space-y-3.5">
        {hasZone ? (
          <>
            {/* Zone Identity & Primary Status Badge */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-slate-500 shrink-0" />
                <div>
                  <div className="flex items-center space-x-2">
                    <h4 className="text-sm font-bold text-safety-dark">{effectiveZone.name}</h4>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200">
                      {(effectiveZone.zone_type || 'floor') === 'surface' ? 'SURFACE / PLATFORM' : 'FLOOR / GROUND'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                    Camera-Aligned Perimeter ({effectiveZone.polygon.length} vertices) • {
                      (effectiveZone.zone_type || 'floor') === 'surface'
                        ? 'Body & hip occupancy mode (bed/platform)'
                        : 'Ground-contact mode (feet/ankles)'
                    }
                  </p>
                </div>
              </div>

              {/* Status Badge */}
              <div
                className={cn(
                  'px-3 py-1.5 rounded-md flex items-center space-x-2 border font-bold text-xs',
                  !isEnabled
                    ? 'bg-slate-100 text-slate-600 border-slate-200'
                    : zoneViolation
                    ? 'bg-red-100 text-safety-crimson border-safety-crimson/30 ring-1 ring-safety-red/20'
                    : 'bg-emerald-50 text-safety-emerald border-emerald-200'
                )}
              >
                <span
                  className={cn(
                    'w-2 h-2 rounded-full shrink-0',
                    !isEnabled ? 'bg-slate-400' : zoneViolation ? 'bg-safety-crimson' : 'bg-safety-emerald'
                  )}
                />
                <span>
                  {!isEnabled
                    ? '⚪ ZONE DISABLED'
                    : zoneViolation
                    ? '🔴 RESTRICTED ZONE ENTRY'
                    : '🟢 ZONE CLEAR'}
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-200/80">
                <span className="text-slate-400 text-[10px] font-semibold block uppercase">Persons In Zone</span>
                <span className={cn('text-base font-black font-mono-timer tabular-nums', zoneViolation ? 'text-safety-crimson' : 'text-safety-dark')}>
                  {personsInZone}
                </span>
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-200/80">
                <span className="text-slate-400 text-[10px] font-semibold block uppercase">SIF Potential</span>
                <span className="text-xs font-bold text-safety-crimson flex items-center space-x-1 mt-0.5">
                  <Activity className="w-3 h-3 text-safety-red shrink-0" />
                  <span>HIGH / POTENTIAL</span>
                </span>
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-200/80">
                <span className="text-slate-400 text-[10px] font-semibold block uppercase">Detection Engine</span>
                <span className="text-xs font-semibold text-slate-700 flex items-center space-x-1 mt-0.5">
                  <Eye className="w-3 h-3 text-blue-600 shrink-0" />
                  <span>
                    {(effectiveZone.zone_type || 'floor') === 'surface' ? 'YOLO-Pose (Hip/Body)' : 'YOLO-Pose (Feet/Ground)'}
                  </span>
                </span>
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-200/80">
                <span className="text-slate-400 text-[10px] font-semibold block uppercase">Zone Actions</span>
                <div className="flex items-center space-x-2 mt-0.5">
                  <button
                    onClick={handleToggle}
                    disabled={actionLoading}
                    className="text-[11px] font-bold text-slate-700 hover:text-slate-900 underline flex items-center space-x-1 transition-colors disabled:opacity-50"
                    title={isEnabled ? 'Disable zone' : 'Enable zone'}
                  >
                    {actionLoading ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Power className={cn('w-3 h-3', isEnabled ? 'text-safety-amber' : 'text-slate-400')} />
                    )}
                    <span>{isEnabled ? 'Disable' : 'Enable'}</span>
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    onClick={handleDelete}
                    disabled={actionLoading}
                    className="text-[11px] font-bold text-safety-crimson hover:text-red-800 underline flex items-center space-x-1 transition-colors disabled:opacity-50"
                    title="Delete zone"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Real-time Telemetry Bar */}
            {status?.zone_debug_info && (
              <div className="bg-safety-dark text-slate-200 px-3 py-1.5 rounded-md text-[11px] font-mono-timer tabular-nums flex items-center justify-between border border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-safety-amber shrink-0"></span>
                  <span className="text-slate-400 font-sans font-semibold">Live Telemetry:</span>
                  <span className="font-bold text-amber-300">{status.zone_debug_info}</span>
                </div>
                {status?.zone_occupancy_score > 0 && (
                  <span className="text-slate-400">
                    Confidence: <strong className="text-white">{Math.round(status.zone_occupancy_score * 100)}%</strong>
                  </span>
                )}
              </div>
            )}
          </>
        ) : (
          /* Empty State */
          <div className="py-6 text-center space-y-2.5">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto">
              <ShieldAlert className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-xs font-bold text-safety-dark">No Restricted Safety Zone Configured</p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              The safety exclusion zone has been removed or disabled. Draw a new perimeter on the live video feed, or restore the default compressor zone with one click.
            </p>
            <div className="flex items-center justify-center space-x-2 pt-1">
              <button
                onClick={handleRestore}
                disabled={actionLoading}
                className="px-3 py-1.5 bg-safety-amber hover:bg-amber-400 active:bg-amber-600 text-slate-950 rounded-md text-xs font-bold shadow-xs inline-flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <RotateCcw className={cn('w-3.5 h-3.5', actionLoading && 'animate-spin')} />
                <span>Restore Default Zone</span>
              </button>
              <button
                onClick={onDefineZone}
                className="px-3 py-1.5 bg-safety-dark hover:bg-slate-800 active:bg-slate-950 text-white rounded-md text-xs font-bold shadow-xs inline-flex items-center space-x-1.5 transition-colors"
              >
                <span>+ Draw Custom Zone</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
