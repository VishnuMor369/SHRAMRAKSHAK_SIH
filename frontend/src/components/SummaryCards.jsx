import React from 'react';
import { Users, Video, ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function SummaryCards({ status, alerts = [] }) {
  const personCount = status?.person_count ?? (status?.person_detected ? 1 : 0);
  const cameraActive = status?.camera_active ?? true;
  const camerasCount = cameraActive ? 1 : 0;
  
  const hasZone = !!(status?.active_zone && status.active_zone.polygon && status.active_zone.polygon.length >= 3);
  const isZoneEnabled = hasZone && (status?.active_zone?.enabled ?? false);
  const zonesCount = hasZone ? 1 : 0;

  // Active alerts count from real state
  const activeAlertsCount = alerts.length > 0 
    ? alerts.length 
    : (status?.active_alert ? 1 : 0);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
      {/* CARD 1: PERSONS DETECTED */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-start justify-between">
        <div>
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Persons Detected
          </span>
          <div className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
            {personCount}
          </div>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            {personCount === 1 ? '1 person visible' : `${personCount} people visible`}
          </p>
        </div>
        <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shrink-0">
          <Users className="w-5 h-5" />
        </div>
      </div>

      {/* CARD 2: CAMERAS ACTIVE */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-start justify-between">
        <div>
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Cameras Active
          </span>
          <div className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
            {camerasCount}
          </div>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            {cameraActive ? 'Live AI camera' : 'Camera offline'}
          </p>
        </div>
        <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
          <Video className="w-5 h-5" />
        </div>
      </div>

      {/* CARD 3: SAFETY ZONES */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-start justify-between">
        <div>
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
            Safety Zones
          </span>
          <div className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
            {zonesCount}
          </div>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            {hasZone 
              ? (isZoneEnabled ? 'Active restricted zone' : 'Zone disabled') 
              : 'No zone configured'}
          </p>
        </div>
        <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600 shrink-0">
          <ShieldAlert className="w-5 h-5" />
        </div>
      </div>

      {/* CARD 4: ACTIVE ALERTS - Visually stands out when alerts exist */}
      <div className={`p-4 rounded-xl border transition-all shadow-sm flex items-start justify-between ${
        activeAlertsCount > 0 
          ? 'bg-red-50/70 border-red-300 ring-2 ring-red-400/30 text-red-950' 
          : 'bg-white border-slate-200 text-slate-900'
      }`}>
        <div>
          <span className={`text-[11px] font-black uppercase tracking-wider block ${
            activeAlertsCount > 0 ? 'text-red-700' : 'text-slate-500'
          }`}>
            Active Alerts
          </span>
          <div className={`text-2xl sm:text-3xl font-black mt-1 ${
            activeAlertsCount > 0 ? 'text-red-700' : 'text-slate-900'
          }`}>
            {activeAlertsCount}
          </div>
          <p className={`text-xs font-semibold mt-0.5 ${
            activeAlertsCount > 0 ? 'text-red-600' : 'text-slate-500'
          }`}>
            {activeAlertsCount > 0 
              ? (activeAlertsCount === 1 ? 'Requires attention' : `${activeAlertsCount} require attention`) 
              : 'All clear / No hazard'}
          </p>
        </div>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${
          activeAlertsCount > 0 
            ? 'bg-red-600 text-white border-red-700 animate-pulse shadow-sm' 
            : 'bg-emerald-50 text-emerald-600 border-emerald-100'
        }`}>
          {activeAlertsCount > 0 ? (
            <AlertTriangle className="w-5 h-5" />
          ) : (
            <CheckCircle2 className="w-5 h-5" />
          )}
        </div>
      </div>
    </div>
  );
}
