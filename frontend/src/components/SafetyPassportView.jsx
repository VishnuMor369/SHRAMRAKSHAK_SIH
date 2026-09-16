import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  MapPin, 
  Video, 
  Users, 
  CheckCircle2, 
  AlertTriangle, 
  X, 
  PlusCircle, 
  FileCheck, 
  ArrowLeft,
  Check,
  AlertOctagon,
  FileText,
  RotateCcw,
  Sparkles,
  Lock,
  Activity,
  ChevronRight
} from 'lucide-react';
import { 
  fetchPassports, 
  createPassport, 
  verifyPassportControl, 
  approvePassport, 
  activatePassport, 
  verifyBarrierRestored, 
  closePassport 
} from '../services/api';

export default function SafetyPassportView({ status, onClose }) {
  const activePassport = status?.active_passport;
  const [allPassports, setAllPassports] = useState([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [remainingTime, setRemainingTime] = useState('15:00');

  // Temporary Zone Design State
  const [isDesigningZone, setIsDesigningZone] = useState(false);
  const [tempZoneData, setTempZoneData] = useState(null);
  const [zonePoints, setZonePoints] = useState([]);
  const [zoneDuration, setZoneDuration] = useState(15);
  const [tempZoneName, setTempZoneName] = useState('Lifting Exclusion Zone');
  const modalSvgRef = React.useRef(null);

  // Form state pre-populated with Demo defaults
  const [formData, setFormData] = useState({
    task_type: 'Mechanical Lifting',
    location: 'Demo Lifting Area',
    supervisor: 'Demo Supervisor',
    camera_id: 'C-01',
    linked_zone_id: 'ZONE-001',
    linked_zone_name: 'Lifting Exclusion Zone',
    duration_minutes: 15,
    permit_reference: 'PTW-OIL-2026-8841',
  });

  const handleModalSvgClick = (e) => {
    if (!modalSvgRef.current) return;
    const rect = modalSvgRef.current.getBoundingClientRect();
    const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 640);
    const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 480);
    const clampedX = Math.max(0, Math.min(640, clickX));
    const clampedY = Math.max(0, Math.min(480, clickY));
    setZonePoints(prev => [...prev, [clampedX, clampedY]]);
  };

  const handleSaveTempZone = () => {
    const cappedDuration = Math.min(zoneDuration, formData.duration_minutes);
    const pts = zonePoints.length >= 3 ? zonePoints : [[150, 150], [490, 150], [490, 420], [150, 420]];
    const savedZone = {
      name: tempZoneName || `${formData.task_type} Exclusion Zone`,
      polygon: pts,
      duration_minutes: cappedDuration,
      camera_id: formData.camera_id || 'C-01',
      zone_category: 'PASSPORT_TEMPORARY'
    };
    setTempZoneData(savedZone);
    setIsDesigningZone(false);
  };

  // Load past passports list
  const loadPassports = async () => {
    try {
      const data = await fetchPassports();
      if (data?.passports) {
        setAllPassports(data.passports);
      }
    } catch (e) {
      console.error('Failed to load passports:', e);
    }
  };

  useEffect(() => {
    loadPassports();
    const interval = setInterval(loadPassports, 3000);
    return () => clearInterval(interval);
  }, []);

  // Update countdown timer for active passport
  useEffect(() => {
    if (!activePassport || !activePassport.expires_at) return;

    const updateCountdown = () => {
      const now = Date.now();
      const exp = new Date(activePassport.expires_at).getTime();
      const diff = Math.max(0, Math.floor((exp - now) / 1000));
      const mins = Math.floor(diff / 60);
      const secs = diff % 60;
      setRemainingTime(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [activePassport]);

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const payload = {
        ...formData,
        linked_zone_name: tempZoneData ? tempZoneData.name : formData.linked_zone_name,
        temporary_zone: tempZoneData,
        zone_polygon: tempZoneData?.polygon,
        zone_duration_minutes: tempZoneData?.duration_minutes
      };
      await createPassport(payload, 'hse');
      setIsCreateOpen(false);
      setTempZoneData(null);
      setZonePoints([]);
      await loadPassports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create safety passport');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleControl = async (ctrlId, currentStatus) => {
    if (!activePassport) return;
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await verifyPassportControl(activePassport.id, ctrlId, !currentStatus, 'HSE Lead', '', 'hse');
      await loadPassports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update control verification');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveAndActivate = async () => {
    if (!activePassport) return;
    try {
      setSubmitting(true);
      setErrorMsg(null);
      // Formal approval
      await approvePassport(activePassport.id, 'HSE Manager OIL-DemoLifting', '', 'hse');
      // Activation
      await activatePassport(activePassport.id, 'hse');
      await loadPassports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to approve and activate passport');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyRestoration = async () => {
    if (!activePassport) return;
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await verifyBarrierRestored(activePassport.id, 'Demo Supervisor', 'Lifting exclusion zone physically inspected and clear');
      await loadPassports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to verify barrier restoration');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!activePassport) return;
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await closePassport(activePassport.id);
      await loadPassports();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to close passport');
    } finally {
      setSubmitting(false);
    }
  };

  const isPaused = activePassport?.status === 'PAUSED';
  const isAwaiting = activePassport?.status === 'AWAITING_RESTORATION';
  const isActive = activePassport?.status === 'ACTIVE';
  const isPending = activePassport?.status === 'PENDING_VERIFICATION' || activePassport?.status === 'PENDING_APPROVAL';
  const controls = activePassport?.controls || [];
  const verifiedCount = controls.filter(c => c.verified).length;
  const totalControls = controls.length || 6;
  const canActivate = verifiedCount === totalControls;

  return (
    <div className="bg-slate-50 min-h-screen text-slate-900 pb-12">
      {/* View Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              title="Return to Monitoring Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="w-9 h-9 rounded-lg bg-slate-900 flex items-center justify-center text-amber-400 shadow-sm">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-slate-900 flex items-center space-x-2">
                <span>START WORK SAFETY PASSPORT</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                  HIGH-RISK PREVENTIVE CONTROL
                </span>
              </h1>
              <p className="text-xs text-slate-500 font-medium">
                Live time-bound safety authorization for critical operations
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5">
            <button
              onClick={() => setIsCreateOpen(true)}
              className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white rounded-lg text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5"
            >
              <PlusCircle className="w-4 h-4 text-amber-400" />
              <span>+ CREATE HIGH-RISK TASK</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Notification Banner */}
        {errorMsg && (
          <div className="p-3.5 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs font-semibold flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertOctagon className="w-4 h-4 text-red-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-red-500 hover:text-red-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* SECTION 1: ACTIVE / CURRENT SAFETY PASSPORT CARD */}
        {activePassport ? (
          <div className={`rounded-2xl border-2 shadow-sm overflow-hidden transition-all ${
            isPaused 
              ? 'bg-red-50/60 border-red-300 ring-2 ring-red-400/20' 
              : isAwaiting 
              ? 'bg-amber-50/60 border-amber-300 ring-2 ring-amber-400/20' 
              : isActive 
              ? 'bg-white border-emerald-300' 
              : 'bg-white border-slate-200'
          }`}>
            {/* Passport Banner */}
            <div className={`px-5 py-3 flex flex-wrap items-center justify-between gap-3 text-white ${
              isPaused 
                ? 'bg-red-700' 
                : isAwaiting 
                ? 'bg-amber-600' 
                : isActive 
                ? 'bg-emerald-700' 
                : 'bg-slate-900'
            }`}>
              <div className="flex items-center space-x-3">
                <span className="text-xl">
                  {isPaused ? '🔴' : isAwaiting ? '🟡' : isActive ? '🟢' : '⏳'}
                </span>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-black uppercase tracking-wider">
                      {isPaused 
                        ? 'SAFETY PASSPORT PAUSED' 
                        : isAwaiting 
                        ? 'AWAITING BARRIER VERIFICATION' 
                        : isActive 
                        ? 'SAFETY PASSPORT ACTIVE' 
                        : 'PENDING VERIFICATION & APPROVAL'}
                    </span>
                    <span className="text-[11px] font-mono bg-black/25 px-2 py-0.5 rounded">
                      {activePassport.id}
                    </span>
                  </div>
                  <h2 className="text-base font-extrabold mt-0.5">
                    {activePassport.task_type} — {activePassport.location}
                  </h2>
                </div>
              </div>

              {isActive && (
                <div className="flex items-center space-x-2 bg-black/20 px-3 py-1 rounded-lg">
                  <Clock className="w-4 h-4 text-emerald-300 animate-spin-slow" />
                  <div className="text-right">
                    <span className="text-xs font-black font-mono-timer">
                      VALID FOR: {remainingTime}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Passport Core Data Grid */}
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Location / Work Area</span>
                  <span className="font-extrabold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    <span>{activePassport.location}</span>
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Supervisor in Charge</span>
                  <span className="font-extrabold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <Users className="w-3.5 h-3.5 text-slate-500" />
                    <span>{activePassport.supervisor}</span>
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Linked Camera & Zone</span>
                  <span className="font-extrabold text-slate-800 flex items-center space-x-1 mt-0.5">
                    <Video className="w-3.5 h-3.5 text-slate-500" />
                    <span>Camera {activePassport.camera_id} • {activePassport.linked_zone_name}</span>
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Permit Reference</span>
                  <span className="font-mono font-bold text-slate-800 block mt-0.5">
                    {activePassport.permit_reference || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Specific State Action Callout */}
              {isPaused && (
                <div className="p-4 bg-red-100/80 border border-red-300 rounded-xl space-y-2.5">
                  <div className="flex items-center space-x-2 text-red-900 font-bold text-xs">
                    <AlertTriangle className="w-4 h-4 text-red-600 animate-pulse" />
                    <span className="uppercase">SAFETY PASSPORT PAUSED — CRITICAL BARRIER BREACH</span>
                  </div>
                  <div className="text-xs text-red-950 font-medium space-y-1 bg-white/70 p-2.5 rounded-lg border border-red-200">
                    <div><b>Reason:</b> {activePassport.breach_reason || 'Restricted Zone Breach'}</div>
                    <div><b>Pathway:</b> Exclusion zone breached → person exposed → line of fire → struck-by / crushing potential</div>
                    <div><b>Recommended Action:</b> Hold lifting activity and clear zone.</div>
                  </div>
                  <p className="text-[11px] text-red-800 font-medium">
                    Status: <b>Awaiting barrier restoration</b>. AI does not automatically reactivate the passport; on-site human supervisor verification remains mandatory before high-risk work can resume.
                  </p>
                </div>
              )}

              {isAwaiting && (
                <div className="p-4 bg-amber-100/70 border border-amber-300 rounded-xl flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center space-x-2 text-amber-900 font-bold text-xs">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="uppercase">Barrier Condition Visually Restored</span>
                    </div>
                    <p className="text-xs text-amber-800 font-medium mt-0.5">
                      AI indicates exclusion zone is clear. Human verification is strictly required to reactivate the passport.
                    </p>
                  </div>
                  <button
                    onClick={handleVerifyRestoration}
                    disabled={submitting}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-lg text-xs font-black tracking-wider transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    <span>VERIFY BARRIER RESTORED</span>
                  </button>
                </div>
              )}

              {/* Close Button if Active or Complete */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                <span className="text-slate-500 font-medium">
                  {isActive ? 'Live continuous monitoring active.' : 'Follow life-saving safety controls.'}
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleClose}
                    disabled={submitting}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-colors"
                  >
                    Close / End Task
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mx-auto">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">
              No Active Safety Passport
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              High-risk activities such as Mechanical Lifting require a verified pre-start safety clearance.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-sm inline-flex items-center space-x-2"
            >
              <PlusCircle className="w-4 h-4 text-amber-400" />
              <span>+ Create High-Risk Task Passport</span>
            </button>
          </div>
        )}
        
        {/* DUAL ZONE REGISTRY: PERMANENT VS TEMPORARY (CHANGE 2, CHANGE 8, CHANGE 12) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Permanent Site Safety Zones */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                <h4 className="text-xs font-black uppercase text-slate-800">🔵 Permanent Site Safety Zones</h4>
              </div>
              <span className="text-[10px] font-bold text-slate-500">
                {(status?.permanent_zones?.length || (status?.active_zone?.zone_category === 'PERMANENT' ? 1 : 1))} Site Area
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              {(status?.permanent_zones && status.permanent_zones.length > 0) ? (
                status.permanent_zones.map(z => (
                  <div key={z.zone_id} className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-200 flex items-center justify-between">
                    <div>
                      <div className="font-bold text-slate-900">{z.name}</div>
                      <div className="text-[10px] text-slate-500">Camera {z.camera_id} • Status: {z.enabled ? 'ACTIVE' : 'DISABLED'}</div>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-300">
                      PERMANENT
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-200 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-slate-900">Compressor Restricted Area</div>
                    <div className="text-[10px] text-slate-500">Camera C-01 • Status: ACTIVE</div>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-300">
                    PERMANENT
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Passport Temporary Exclusion Zones */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <h4 className="text-xs font-black uppercase text-slate-800">🟠 Passport Temporary Zones</h4>
              </div>
              <span className="text-[10px] font-bold text-amber-800">
                {status?.temporary_zones?.length || (activePassport ? 1 : 0)} Active
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              {status?.temporary_zones && status.temporary_zones.length > 0 ? (
                status.temporary_zones.map(tz => (
                  <div key={tz.zone_id} className="p-2.5 bg-amber-50/50 rounded-lg border border-amber-200 flex items-center justify-between">
                    <div>
                      <div className="font-bold text-slate-900">{tz.name}</div>
                      <div className="text-[10px] text-slate-500">
                        Camera {tz.camera_id} • Passport: {tz.passport_id || activePassport?.id}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 block">
                        🟠 TEMPORARY
                      </span>
                      <span className="text-[10px] font-mono font-bold text-amber-800 mt-0.5 block">
                        ⏱ {remainingTime}
                      </span>
                    </div>
                  </div>
                ))
              ) : activePassport ? (
                <div className="p-2.5 bg-amber-50/50 rounded-lg border border-amber-200 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-slate-900">{activePassport.linked_zone_name || 'Lifting Exclusion Zone'}</div>
                    <div className="text-[10px] text-slate-500">Camera {activePassport.camera_id} • Passport: {activePassport.id}</div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 block">
                      🟠 TEMPORARY
                    </span>
                    <span className="text-[10px] font-mono font-bold text-amber-800 mt-0.5 block">
                      ⏱ {remainingTime}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-400 italic py-3 text-center">
                  No temporary passport zones active. Created when High-Risk Task is initiated.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SECTION 2: PRE-START VERIFICATION CHECKLIST */}
        {activePassport && isPending && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-black uppercase tracking-tight text-slate-900">
                  Pre-Start Safety Checklist
                </h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Distinguishing honest verification sources before high-risk work commences
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <span className={`px-2.5 py-1 rounded-full text-xs font-black tracking-wider ${
                  canActivate ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                }`}>
                  {verifiedCount} / {totalControls} CONTROLS VERIFIED
                </span>
              </div>
            </div>

            {/* Controls List */}
            <div className="space-y-2.5">
              {controls.map((ctrl) => {
                let badgeStyle = 'bg-slate-100 text-slate-700 border-slate-200';
                if (ctrl.verification_source.includes('AI')) {
                  badgeStyle = 'bg-blue-50 text-blue-800 border-blue-200';
                } else if (ctrl.verification_source.includes('SUPERVISOR')) {
                  badgeStyle = 'bg-amber-50 text-amber-800 border-amber-200';
                } else if (ctrl.verification_source.includes('HSE')) {
                  badgeStyle = 'bg-purple-50 text-purple-800 border-purple-200';
                }

                return (
                  <div 
                    key={ctrl.id}
                    className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                      ctrl.verified ? 'bg-emerald-50/40 border-emerald-200' : 'bg-slate-50/80 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => handleToggleControl(ctrl.id, ctrl.verified)}
                        className={`w-6 h-6 rounded-md flex items-center justify-center border transition-all ${
                          ctrl.verified 
                            ? 'bg-emerald-600 border-emerald-700 text-white' 
                            : 'bg-white border-slate-300 text-transparent hover:border-slate-400'
                        }`}
                      >
                        <Check className="w-4 h-4" />
                      </button>

                      <div>
                        <div className="flex items-center space-x-2">
                          <span className={`text-xs font-black ${ctrl.verified ? 'text-slate-900' : 'text-slate-700'}`}>
                            {ctrl.name}
                          </span>
                          <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold border uppercase ${badgeStyle}`}>
                            {ctrl.verification_source}
                          </span>
                        </div>
                        {ctrl.verified && ctrl.verified_by && (
                          <span className="text-[10px] text-slate-500 font-medium block mt-0.5">
                            Verified by: {ctrl.verified_by}
                          </span>
                        )}
                      </div>
                    </div>

                    <span className={`text-xs font-bold ${ctrl.verified ? 'text-emerald-700' : 'text-slate-400'}`}>
                      {ctrl.verified ? '✓ Verified' : 'Pending'}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Clearance & Approval Action Card */}
            <div className={`p-4 rounded-xl border flex flex-wrap items-center justify-between gap-3 ${
              canActivate ? 'bg-emerald-50 border-emerald-300' : 'bg-slate-100 border-slate-200'
            }`}>
              <div>
                <span className={`text-xs font-black uppercase tracking-wider block ${
                  canActivate ? 'text-emerald-900' : 'text-slate-600'
                }`}>
                  {canActivate ? '🟢 READY FOR CLEARANCE' : '🔴 SAFETY PASSPORT BLOCKED'}
                </span>
                <p className="text-xs text-slate-600 font-medium mt-0.5">
                  {canActivate 
                    ? 'All mandatory barriers and physical controls verified. Authorize to start.' 
                    : `Complete missing controls (${totalControls - verifiedCount} remaining) before activating work.`}
                </p>
              </div>

              <button
                onClick={handleApproveAndActivate}
                disabled={!canActivate || submitting}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-lg text-xs font-black tracking-wider transition-all shadow-md flex items-center space-x-1.5 disabled:opacity-40"
              >
                <span>APPROVE & ACTIVATE PASSPORT</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* SECTION 3: PASSPORT HISTORY & AUDIT TRAIL */}
        {activePassport?.events && activePassport.events.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-900">
                Safety Passport Event Timeline (Audit Log)
              </h3>
              <span className="text-[11px] font-mono text-slate-400">
                {activePassport.events.length} Recorded Events
              </span>
            </div>

            <div className="space-y-2">
              {activePassport.events.slice().reverse().map((evt) => {
                const timeStr = new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                let dotColor = 'bg-slate-400';
                if (evt.event_type === 'activated' || evt.event_type === 'reactivated') dotColor = 'bg-emerald-500';
                if (evt.event_type === 'paused') dotColor = 'bg-red-600 animate-pulse';
                if (evt.event_type === 'barrier_clear') dotColor = 'bg-amber-500';
                if (evt.event_type === 'approved') dotColor = 'bg-purple-600';

                return (
                  <div key={evt.id} className="flex items-start space-x-3 text-xs p-2 rounded-lg bg-slate-50/70 border border-slate-100">
                    <span className="font-mono text-slate-500 font-bold text-[11px] shrink-0">
                      {timeStr}
                    </span>
                    <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${dotColor}`}></span>
                    <div className="flex-1 min-w-0">
                      <span className="font-bold text-slate-800">{evt.description}</span>
                      <span className="text-[10px] text-slate-400 block mt-0.5">Actor: {evt.actor}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* CREATE HIGH-RISK TASK MODAL */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden my-6">
            <div className="px-5 py-3.5 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-black uppercase tracking-wider">
                  {isDesigningZone ? 'Design Temporary Safety Zone' : 'Create Safety Passport'}
                </span>
              </div>
              <button 
                onClick={() => {
                  setIsCreateOpen(false);
                  setIsDesigningZone(false);
                }} 
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {isDesigningZone ? (
              <div className="p-5 space-y-3.5 text-xs">
                <div className="bg-slate-900 text-white p-3 rounded-xl flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-black uppercase text-amber-400">DESIGN TEMPORARY SAFETY ZONE</h3>
                    <p className="text-[10px] text-slate-300">Camera: {formData.camera_id} • Click frame to draw boundary</p>
                  </div>
                  <span className="font-mono text-xs text-amber-400 font-bold bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                    Points: {zonePoints.length} (Min 3)
                  </span>
                </div>

                <div className="relative aspect-[4/3] bg-slate-950 rounded-xl overflow-hidden border border-slate-700">
                  <img
                    src="/video_feed"
                    alt="CCTV Frame"
                    className="w-full h-full object-fill pointer-events-none select-none"
                  />
                  <svg
                    ref={modalSvgRef}
                    viewBox="0 0 640 480"
                    onClick={handleModalSvgClick}
                    className="absolute inset-0 w-full h-full cursor-crosshair z-10 select-none"
                  >
                    <rect x="1" y="1" width="638" height="478" fill="transparent" stroke="rgba(245, 158, 11, 0.5)" strokeWidth="2" strokeDasharray="6 3" />
                    {zonePoints.length > 1 && (
                      <polygon
                        points={zonePoints.map(p => `${p[0]},${p[1]}`).join(' ')}
                        fill="rgba(245, 158, 11, 0.28)"
                        stroke="#f59e0b"
                        strokeWidth="3"
                      />
                    )}
                    {zonePoints.map((p, idx) => (
                      <g key={idx}>
                        <circle cx={p[0]} cy={p[1]} r="6" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />
                        <text x={p[0] + 8} y={p[1] - 4} fill="#ffffff" fontSize="12" fontWeight="bold">
                          P{idx + 1}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Zone Name:</label>
                    <input
                      type="text"
                      value={tempZoneName}
                      onChange={(e) => setTempZoneName(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded font-semibold text-slate-900 outline-none focus:border-slate-800"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Zone Type:</label>
                    <div className="px-2.5 py-1.5 bg-amber-50 border border-amber-200 text-amber-900 font-bold rounded text-xs">
                      🟠 TEMPORARY PASSPORT ZONE
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">Duration:</label>
                    <select
                      value={zoneDuration}
                      onChange={(e) => setZoneDuration(Math.min(parseInt(e.target.value), formData.duration_minutes))}
                      className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded font-semibold text-slate-900 outline-none"
                    >
                      <option value={5}>5 minutes</option>
                      <option value={10}>10 minutes</option>
                      <option value={15}>15 minutes</option>
                      <option value={30}>30 minutes</option>
                      <option value={formData.duration_minutes}>{formData.duration_minutes} min (Match Passport)</option>
                    </select>
                    <span className="text-[9px] text-slate-500 mt-0.5 block">Capped to Passport duration ({formData.duration_minutes} min)</span>
                  </div>

                  <div className="flex items-end justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => setZonePoints([])}
                      className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-bold"
                    >
                      Clear
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsDesigningZone(false)}
                      className="px-2.5 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded font-bold"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveTempZone}
                      className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded font-black shadow-sm"
                    >
                      SAVE TEMPORARY ZONE
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateSubmit} className="p-5 space-y-3.5 text-xs">
                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">High-Risk Task Type:</label>
                  <select
                    value={formData.task_type}
                    onChange={(e) => setFormData({ ...formData, task_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-semibold text-slate-900 outline-none focus:border-slate-800"
                  >
                    <option value="Mechanical Lifting">Mechanical Lifting</option>
                    <option value="Working at Heights">Working at Heights</option>
                    <option value="Confined Space Entry">Confined Space Entry</option>
                    <option value="Hot Work / Welding">Hot Work / Welding</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">Location Area:</label>
                    <input
                      type="text"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold outline-none focus:border-slate-800"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">Supervisor in Charge:</label>
                    <input
                      type="text"
                      value={formData.supervisor}
                      onChange={(e) => setFormData({ ...formData, supervisor: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold outline-none focus:border-slate-800"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">Linked Camera:</label>
                    <select
                      value={formData.camera_id}
                      onChange={(e) => setFormData({ ...formData, camera_id: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold outline-none focus:border-slate-800"
                    >
                      <option value="C-01">Camera C-01 (Demo Work Zone)</option>
                      <option value="C-02">Camera C-02 (Rig Floor & Compressor Area)</option>
                      <option value="C-03">Camera C-03 (Tank Battery Confined Space)</option>
                      <option value="C-04">Camera C-04 (Pipe Crane Yard Line of Fire)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-700 block mb-1">Passport Duration (Minutes):</label>
                    <select
                      value={formData.duration_minutes}
                      onChange={(e) => {
                        const d = parseInt(e.target.value) || 15;
                        setFormData({ ...formData, duration_minutes: d });
                        if (zoneDuration > d) setZoneDuration(d);
                      }}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold outline-none focus:border-slate-800"
                    >
                      <option value={5}>5 minutes</option>
                      <option value={10}>10 minutes</option>
                      <option value={15}>15 minutes</option>
                      <option value={30}>30 minutes</option>
                      <option value={60}>60 minutes</option>
                    </select>
                  </div>
                </div>

                {/* TEMPORARY SAFETY ZONE DESIGNER SECTION (CHANGE 4) */}
                <div className="pt-2 pb-1 border-t border-slate-200">
                  <div className="text-[11px] font-black uppercase text-slate-800 tracking-wider mb-2">
                    TEMPORARY SAFETY ZONE
                  </div>

                  {tempZoneData ? (
                    <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span className="text-xs font-black text-slate-900 uppercase">✓ TEMPORARY ZONE CREATED</span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500 text-white uppercase">
                          🟠 Temporary
                        </span>
                      </div>
                      <div className="text-xs text-slate-700">
                        <div className="font-bold text-slate-900">{tempZoneData.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          Camera: {tempZoneData.camera_id} • Valid for: {tempZoneData.duration_minutes}:00 ({tempZoneData.polygon?.length || 4} points)
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 pt-1 border-t border-amber-200">
                        <button
                          type="button"
                          onClick={() => {
                            setZonePoints(tempZoneData.polygon || []);
                            setIsDesigningZone(true);
                          }}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-bold rounded shadow-sm"
                        >
                          EDIT ZONE
                        </button>
                        <button
                          type="button"
                          onClick={() => setTempZoneData(null)}
                          className="px-2.5 py-1 bg-white hover:bg-red-50 border border-red-200 text-red-600 text-xs font-bold rounded shadow-sm"
                        >
                          REMOVE ZONE
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-2">
                      <div className="text-xs text-slate-500 font-medium">
                        No temporary zone created yet.
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setZonePoints([[150, 150], [490, 150], [490, 420], [150, 420]]);
                          setIsDesigningZone(true);
                        }}
                        className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold inline-flex items-center space-x-1.5 shadow-sm"
                      >
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>+ DESIGN RESTRICTED ZONE</span>
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-700 block mb-1">Permit / Authorization Reference:</label>
                  <input
                    type="text"
                    value={formData.permit_reference}
                    onChange={(e) => setFormData({ ...formData, permit_reference: e.target.value })}
                    placeholder="e.g. PTW-OIL-2026-8841"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold outline-none focus:border-slate-800"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-bold shadow-sm disabled:opacity-50"
                  >
                    {submitting ? 'Creating...' : 'Create Passport'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
