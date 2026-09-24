import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ShieldAlert, 
  MapPin, 
  Video, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  ArrowRight,
  ArrowLeft,
  Users,
  HardHat,
  ChevronRight,
  Activity,
  History,
  AlertOctagon,
  RefreshCw,
  Shield,
  PlusCircle,
  Check,
  X,
  FileCheck,
  Lock,
  FileText
} from 'lucide-react';
import { 
  respondToAlert, 
  resolveAlert, 
  markActionTaken,
  verifyAlert,
  fetchAlertHistory,
  createPassport,
  verifyPassportControl,
  approvePassport,
  activatePassport,
  verifyBarrierRestored,
  closePassport
} from '../services/api';

export default function Supervisor({ stateData }) {
  const status = stateData?.status;
  const isConnected = stateData?.isConnected;
  const activePassport = status?.active_passport;
  
  // All active alerts sorted by priority from backend (Proximity Critical first)
  const rawActiveAlerts = status?.active_alerts || (status?.active_alert ? [status.active_alert] : []);
  const activeAlerts = [...rawActiveAlerts].sort((a, b) => {
    const aIsProx = a.is_high_priority || a.type === 'Person–Vehicle Proximity' || (a.priority_score && a.priority_score >= 150);
    const bIsProx = b.is_high_priority || b.type === 'Person–Vehicle Proximity' || (b.priority_score && b.priority_score >= 150);
    if (aIsProx && !bIsProx) return -1;
    if (!aIsProx && bIsProx) return 1;
    const aPriority = a.priority_score ?? 80;
    const bPriority = b.priority_score ?? 80;
    if (bPriority !== aPriority) return bPriority - aPriority;
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
  });
  
  // Navigation tabs: 'alerts', 'passport', 'history', 'status'
  const [currentTab, setCurrentTab] = useState('alerts');
  
  // Selected alert for Detail View (null = Inbox View)
  const [selectedAlertId, setSelectedAlertId] = useState(null);
  
  // Local submission states & deduplication
  const [submitting, setSubmitting] = useState(false);
  const [acknowledgedAlertIds, setAcknowledgedAlertIds] = useState(() => new Set());
  const isRespondingRef = useRef(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [resolveSuccessMsg, setResolveSuccessMsg] = useState(null);

  // Passport Mobile Form State
  const [isCreatePassportModalOpen, setIsCreatePassportModalOpen] = useState(false);
  const [passportFormData, setPassportFormData] = useState({
    task_type: 'Mechanical Lifting',
    location: 'Demo Lifting Area',
    supervisor: 'Demo Supervisor',
    camera_id: 'C-01',
    linked_zone_id: 'ZONE-001',
    linked_zone_name: 'Lifting Exclusion Zone',
    duration_minutes: 15,
    permit_reference: 'PTW-OIL-2026-8841',
  });
  const [passportTimeLeft, setPassportTimeLeft] = useState('15:00');
  const [showPassportDetails, setShowPassportDetails] = useState(false);

  // Temporary Zone Design State in Supervisor Mobile
  const [isMobileDesigningZone, setIsMobileDesigningZone] = useState(false);
  const [mobileTempZoneData, setMobileTempZoneData] = useState(null);
  const [mobileZonePoints, setMobileZonePoints] = useState([]);
  const [mobileZoneDuration, setMobileZoneDuration] = useState(15);
  const [mobileZoneName, setMobileZoneName] = useState('Lifting Exclusion Zone');
  const mobileSvgRef = useRef(null);

  const handleMobileSvgClick = (e) => {
    if (!mobileSvgRef.current) return;
    const rect = mobileSvgRef.current.getBoundingClientRect();
    const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 640);
    const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 480);
    const clampedX = Math.max(0, Math.min(640, clickX));
    const clampedY = Math.max(0, Math.min(480, clickY));
    setMobileZonePoints(prev => [...prev, [clampedX, clampedY]]);
  };

  const handleSaveMobileTempZone = () => {
    const cappedDuration = Math.min(mobileZoneDuration, passportFormData.duration_minutes);
    const pts = mobileZonePoints.length >= 3 ? mobileZonePoints : [[150, 150], [490, 150], [490, 420], [150, 420]];
    const savedZone = {
      name: mobileZoneName || `${passportFormData.task_type} Exclusion Zone`,
      polygon: pts,
      duration_minutes: cappedDuration,
      camera_id: passportFormData.camera_id || 'C-01',
      zone_category: 'PASSPORT_TEMPORARY'
    };
    setMobileTempZoneData(savedZone);
    setIsMobileDesigningZone(false);
  };

  // History State
  const [historyAlerts, setHistoryAlerts] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [selectedHistoryAlert, setSelectedHistoryAlert] = useState(null);

  // Auto-clear success messages
  useEffect(() => {
    if (resolveSuccessMsg) {
      const t = setTimeout(() => setResolveSuccessMsg(null), 3000);
      return () => clearTimeout(t);
    }
  }, [resolveSuccessMsg]);

  // Helpers for time formatting
  const formatTime = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatDuration = (startIso, endIso) => {
    if (!startIso || !endIso) return 'N/A';
    try {
      const start = new Date(startIso).getTime();
      const end = new Date(endIso).getTime();
      const sec = Math.max(0, Math.round((end - start) / 1000));
      return `${sec} sec`;
    } catch {
      return 'N/A';
    }
  };

  // Fetch real alert history from backend
  const loadHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      setHistoryError(null);
      const data = await fetchAlertHistory();
      const list = data?.history || data?.alerts || [];
      setHistoryAlerts(list);
    } catch (err) {
      console.error('Failed to load alert history:', err);
      setHistoryError('Unable to load alert history. Check connection and retry.');
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  // Poll history when on History tab
  useEffect(() => {
    if (currentTab === 'history') {
      loadHistory();
      const interval = setInterval(loadHistory, 2500);
      return () => clearInterval(interval);
    }
  }, [currentTab, loadHistory]);

  // If selected alert was resolved or removed, check if still exists
  const selectedAlert = activeAlerts.find(a => a.id === selectedAlertId);

  // Synchronized countdown timer for the selected alert
  const [remainingSec, setRemainingSec] = useState(0);
  useEffect(() => {
    if (!selectedAlert) return;

    const calculateRemaining = () => {
      const now = Date.now();
      if (selectedAlert.status === 'WAITING_FOR_RESPONSE') {
        const deadline = new Date(selectedAlert.response_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((deadline - now) / 1000)));
      } else if (selectedAlert.status === 'RESPONDING' && selectedAlert.action_deadline) {
        const deadline = new Date(selectedAlert.action_deadline).getTime();
        setRemainingSec(Math.max(0, Math.ceil((deadline - now) / 1000)));
      }
    };

    calculateRemaining();
    const timer = setInterval(calculateRemaining, 250);
    return () => clearInterval(timer);
  }, [selectedAlert]);

  // Handle Supervisor "ACKNOWLEDGE / I'M RESPONDING"
  const handleResponding = async (alertId) => {
    if (!alertId) return;
    if (isRespondingRef.current || submitting) return;
    if (acknowledgedAlertIds.has(alertId)) return;
    if (selectedAlert && selectedAlert.id === alertId && selectedAlert.status !== 'WAITING_FOR_RESPONSE' && selectedAlert.status !== 'ESCALATED') return;

    try {
      isRespondingRef.current = true;
      setSubmitting(true);
      setErrorMsg(null);
      // Optimistically record acknowledgement immediately to lock UI against duplicates
      setAcknowledgedAlertIds(prev => new Set(prev).add(alertId));
      await respondToAlert('SUP-FIELD-01', 'Supervisor acknowledged alert and en route to zone', alertId);
    } catch (err) {
      // Rollback optimistic acknowledgement on true failure so user can retry
      setAcknowledgedAlertIds(prev => {
        const next = new Set(prev);
        next.delete(alertId);
        return next;
      });
      setErrorMsg('Failed to record response. Please check connection and retry.');
    } finally {
      setSubmitting(false);
      isRespondingRef.current = false;
    }
  };

  // Handle Supervisor "FIXED / RESOLVED"
  const handleResolved = async (alert) => {
    if (!alert || submitting || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setSubmitting(true);
      setErrorMsg(null);
      const isZone = alert?.type === 'Restricted Zone Entry';
      const defaultNote = isZone 
        ? 'Personnel evacuated from restricted zone; perimeter verified safe.' 
        : `${alert?.person_count || 1} worker(s) donned required head PPE; compliance verified.`;
      
      await resolveAlert('SUP-FIELD-01', defaultNote, alert.id);
      setResolveSuccessMsg(`✓ ${alert.type} marked RESOLVED`);
      // Return to Inbox View smoothly
      setSelectedAlertId(null);
      // Immediately refresh history so newly resolved alert appears
      loadHistory();
    } catch (err) {
      setErrorMsg('Unable to resolve alert. Check connection and retry.');
    } finally {
      setSubmitting(false);
      isRespondingRef.current = false;
    }
  };

  // Handle Supervisor "ACTION TAKEN" (Phase 4 State Machine)
  const handleMarkActionTaken = async (alert) => {
    if (!alert || submitting || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setSubmitting(true);
      setErrorMsg(null);
      await markActionTaken('SUP-FIELD-01', 'Corrective action executed on-site', 'Action Taken', alert.id);
      setResolveSuccessMsg('✓ Action marked COMPLETED — Awaiting safety verification');
    } catch (err) {
      setErrorMsg('Unable to record action. Please retry.');
    } finally {
      setSubmitting(false);
      isRespondingRef.current = false;
    }
  };

  // Handle Supervisor Formal Safety Verification (Phase 4 State Machine)
  const handleVerifyAlert = async (alert, decision = 'VERIFIED', method = 'CCTV_VERIFIED') => {
    if (!alert || submitting || isRespondingRef.current) return;
    try {
      isRespondingRef.current = true;
      setSubmitting(true);
      setErrorMsg(null);
      await verifyAlert('SUP-FIELD-01', decision, method, `Verification: ${decision}`, alert.id);
      if (decision === 'VERIFIED') {
        setResolveSuccessMsg('✓ Safety problem VERIFIED & RESOLVED');
        setSelectedAlertId(null);
        loadHistory();
      } else if (decision === 'FAILED') {
        setErrorMsg('⚠ Verification FAILED: Corrective action reopened.');
      } else {
        setResolveSuccessMsg('✓ Forwarded for HSE Audit Review');
      }
    } catch (err) {
      setErrorMsg('Unable to complete verification. Please retry.');
    } finally {
      setSubmitting(false);
      isRespondingRef.current = false;
    }
  };

  // Passport Countdown Timer
  useEffect(() => {
    if (!activePassport || !activePassport.expires_at) return;
    const updateCountdown = () => {
      const now = Date.now();
      const exp = new Date(activePassport.expires_at).getTime();
      const diff = Math.max(0, Math.floor((exp - now) / 1000));
      const mins = Math.floor(diff / 60);
      const secs = diff % 60;
      setPassportTimeLeft(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
    };
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [activePassport]);

  // Handle Mobile Passport Creation
  const handleCreatePassportMobile = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const payload = {
        ...passportFormData,
        linked_zone_name: mobileTempZoneData ? mobileTempZoneData.name : passportFormData.linked_zone_name,
        temporary_zone: mobileTempZoneData,
        zone_polygon: mobileTempZoneData?.polygon,
        zone_duration_minutes: mobileTempZoneData?.duration_minutes
      };
      await createPassport(payload);
      setIsCreatePassportModalOpen(false);
      setMobileTempZoneData(null);
      setMobileZonePoints([]);
      setResolveSuccessMsg('✓ Safety Passport requested (Awaiting HSE approval)');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create safety passport');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Mobile Supervisor Control Verification
  const handleToggleControlMobile = async (ctrlId, currentVal) => {
    if (!activePassport) return;
    if (ctrlId === 'ctrl-6') {
      setErrorMsg('🔒 HSE Verification is an HSE-only responsibility. Pending clearance by HSE Manager.');
      return;
    }
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await verifyPassportControl(activePassport.id, ctrlId, !currentVal, 'Demo Supervisor', '', 'supervisor');
      setResolveSuccessMsg('✓ Control verification updated');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to verify control');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Mobile Explicit Verification of Barrier Restoration
  const handleVerifyBarrierRestored = async (alert) => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      if (activePassport) {
        await verifyBarrierRestored(activePassport.id, 'Demo Supervisor', 'Lifting exclusion zone physically inspected clear and barrier restored');
      }
      if (alert) {
        await resolveAlert('Demo Supervisor', 'Barrier restoration verified by Demo Supervisor. Exclusion zone safe.', alert.id);
        setSelectedAlertId(null);
      }
      setResolveSuccessMsg('✓ Safety Passport REACTIVATED & Breach Resolved');
      loadHistory();
    } catch (err) {
      setErrorMsg(err.message || 'Unable to verify barrier restoration');
    } finally {
      setSubmitting(false);
    }
  };

  // Severity counts
  const criticalCount = activeAlerts.filter(a => a.priority_label === 'CRITICAL' || a.severity === 'CRITICAL').length;
  const highCount = activeAlerts.filter(a => a.priority_label === 'HIGH' || a.severity === 'HIGH').length;

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans max-w-md mx-auto shadow-2xl border-x border-slate-200 select-none pb-16">
      
      {/* ======================================================== */}
      {/* MOBILE TOP HEADER (Dark Navy Industrial Design)          */}
      {/* ======================================================== */}
      <header className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between sticky top-0 z-30 shadow-md">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <HardHat className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-black tracking-tight leading-none">SHRAMRAKSHAK</h1>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wide uppercase mt-0.5">
              Supervisor Dispatch
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Active alerts badge */}
          {activeAlerts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-extrabold animate-pulse">
              {activeAlerts.length} ACTIVE
            </span>
          )}
          {/* Network Sync Pill */}
          <div className="flex items-center space-x-1.5 px-2 py-1 rounded-full bg-slate-800 text-[10px] font-semibold text-slate-300 border border-slate-700">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
            <span>{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-4 flex flex-col space-y-3">
        {!status ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4 my-auto min-h-[300px]">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500">
              <RefreshCw className="w-7 h-7 animate-spin" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 tracking-tight">
                Connecting to ShramRakshak...
              </h2>
              <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                Establishing real-time link with CCTV intelligence and supervisor alert dispatcher
              </p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-bold rounded-lg transition-colors flex items-center space-x-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
          </div>
        ) : (
          <>
            {/* Error Notification */}
            {errorMsg && (
              <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-red-900 text-xs font-semibold flex items-center justify-between">
                <span>{errorMsg}</span>
                <button onClick={() => setErrorMsg(null)} className="text-red-700 font-bold ml-2">✕</button>
              </div>
            )}

            {/* Success Confirmation Toast */}
            {resolveSuccessMsg && (
              <div className="p-3 bg-emerald-100 border border-emerald-300 rounded-lg text-emerald-900 text-xs font-bold flex items-center space-x-2 animate-fade-in">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{resolveSuccessMsg}</span>
              </div>
            )}

        {/* ======================================================== */}
        {/* TAB 1: ALERTS INBOX OR ALERT DETAIL                      */}
        {/* ======================================================== */}
        {currentTab === 'alerts' && (
          <>
            {/* VIEW A: ALERT DETAIL SCREEN (If an alert is selected) */}
            {selectedAlert ? (
              <div className="space-y-4 flex-1 flex flex-col">
                {/* Back to Inbox Button */}
                <button
                  onClick={() => setSelectedAlertId(null)}
                  className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm w-fit"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Alerts ({activeAlerts.length})</span>
                </button>

                {/* Detail Card Header */}
                <div className={`p-4 rounded-xl border shadow-sm ${
                  selectedAlert.status === 'ESCALATED' 
                    ? 'bg-rose-50 border-rose-300' 
                    : selectedAlert.status === 'RESPONDING'
                    ? 'bg-amber-50 border-amber-300'
                    : 'bg-red-50 border-red-300'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                      selectedAlert.priority_label === 'CRITICAL' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
                    }`}>
                      {selectedAlert.priority_label || selectedAlert.severity} PRIORITY
                    </span>
                    <span className="text-[11px] font-mono text-slate-500 font-bold">
                      {selectedAlert.id}
                    </span>
                  </div>

                  <h2 className="text-xl font-black text-slate-900 mt-2 tracking-tight">
                    {selectedAlert.title || selectedAlert.type}
                  </h2>
                  <p className="text-xs font-semibold text-slate-700 mt-0.5">
                    {selectedAlert.short_summary || selectedAlert.unsafe_condition}
                  </p>
                </div>

                {/* Fact Grid: WHAT, PEOPLE, LOCATION, SOURCE */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3 text-xs">
                  <div className="border-b border-slate-100 pb-2">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">What Happened</div>
                    <div className="font-bold text-slate-800 mt-0.5">
                      {selectedAlert.type === 'SAFETY PASSPORT BREACH'
                        ? `Lifting exclusion zone breached during active ${activePassport?.task_type || 'Mechanical Lifting'}`
                        : (selectedAlert.type === 'Person–Vehicle Proximity' || selectedAlert.is_high_priority)
                        ? `Person-Vehicle Proximity Breach: ${selectedAlert.person_id || 'Person #3'} within safety perimeter of ${selectedAlert.vehicle_id || 'Vehicle #1'} (${selectedAlert.vehicle_type || 'Vehicle'})`
                        : selectedAlert.type === 'Restricted Zone Entry'
                        ? `Person detected inside restricted perimeter: ${selectedAlert.location}`
                        : `${selectedAlert.person_count} worker(s) present without safety helmet in active zone`}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 border-b border-slate-100 pb-2">
                    <div>
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        {selectedAlert.type === 'SAFETY PASSPORT BREACH' ? 'Detected Condition' : 'People Affected'}
                      </div>
                      <div className="font-bold text-slate-800 flex items-center space-x-1 mt-0.5">
                        <Users className="w-3.5 h-3.5 text-slate-500" />
                        <span>
                          {selectedAlert.type === 'SAFETY PASSPORT BREACH'
                            ? 'Person inside linked exclusion zone'
                            : `${selectedAlert.person_count} ${selectedAlert.person_count > 1 ? 'people' : 'person'}${selectedAlert.affected_person_ids?.length > 0 ? ` (${selectedAlert.affected_person_ids.join(', ')})` : ''}`}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Location</div>
                      <div className="font-bold text-slate-800 flex items-center space-x-1 mt-0.5">
                        <MapPin className="w-3.5 h-3.5 text-slate-500" />
                        <span className="truncate">{selectedAlert.location}</span>
                      </div>
                    </div>
                  </div>

                  {selectedAlert.type === 'SAFETY PASSPORT BREACH' && (
                    <div className="border-b border-slate-100 pb-2">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Potential SIF Pathway</div>
                      <div className="font-bold text-rose-700 mt-0.5">
                        Line of Fire → Struck-by / Crushing Potential
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Detection Source</div>
                    <div className="font-semibold text-slate-700 flex items-center space-x-1 mt-0.5">
                      <Video className="w-3.5 h-3.5 text-slate-500" />
                      <span>{selectedAlert.source || `AI CCTV Camera ${selectedAlert.camera}`}</span>
                    </div>
                  </div>
                </div>

                {/* CCTV Visual Evidence Frame (CHANGE 1 & CHANGE 10) */}
                {(selectedAlert.evidence_image || selectedAlert.evidence_url) && (
                  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                    <div className="bg-slate-900 text-white px-3 py-2 flex items-center justify-between">
                      <div className="flex items-center space-x-1.5">
                        <Video className="w-3.5 h-3.5 text-amber-400" />
                        <span className="text-[10px] font-black uppercase tracking-wider">CCTV Evidence Image</span>
                      </div>
                      <span className="font-mono text-slate-400 text-[9px]">
                        Camera: {selectedAlert.camera || 'C-01'} • {selectedAlert.location}
                      </span>
                    </div>
                    <div className="relative bg-slate-950 flex items-center justify-center">
                      <img
                        src={selectedAlert.evidence_image || selectedAlert.evidence_url}
                        alt="Visual Evidence of Violation"
                        className="w-full max-h-56 object-contain"
                      />
                    </div>
                    <div className="p-3 bg-slate-50 border-t border-slate-100 text-xs">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                        Detected:
                      </div>
                      <ul className="space-y-1 font-bold text-slate-800">
                        {selectedAlert.affected_person_ids && selectedAlert.affected_person_ids.length > 0 ? (
                          selectedAlert.affected_person_ids.map((pid, idx) => (
                            <li key={idx} className="flex items-center space-x-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-600 shrink-0"></span>
                              <span>
                                {pid} — {selectedAlert.type === 'Helmet/PPE Violation' ? 'No Helmet' : (selectedAlert.type === 'SAFETY PASSPORT BREACH' ? 'Inside Lifting Exclusion Zone' : 'Inside Restricted Zone')}
                              </span>
                            </li>
                          ))
                        ) : (
                          <li className="flex items-center space-x-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-600 shrink-0"></span>
                            <span>Person 01 — {selectedAlert.type === 'Helmet/PPE Violation' ? 'No Helmet' : 'Inside Zone'}</span>
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}

                {/* ==================================================== */}
                {/* PHASE 5: SIF REASONING ("WHY SIF POTENTIAL?")        */}
                {/* ==================================================== */}
                <div className="bg-slate-900 text-white rounded-xl p-3.5 shadow-sm space-y-2.5 text-xs border border-slate-800">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-base">🚨</span>
                      <span className="font-black text-rose-400 uppercase tracking-wider text-[11px]">
                        SIF POTENTIAL REASONING
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-red-600 text-white">
                      {selectedAlert.sif_level || 'HIGH'} PRIORITY
                    </span>
                  </div>

                  {/* Evidence Matrix */}
                  <div className="grid grid-cols-2 gap-2 pt-0.5">
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60 flex items-center justify-between">
                      <span className="text-slate-300 font-medium text-[11px]">Person Exposure</span>
                      <span className="text-emerald-400 font-black">✓</span>
                    </div>
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60 flex items-center justify-between">
                      <span className="text-slate-300 font-medium text-[11px]">Hazardous Activity</span>
                      <span className="text-emerald-400 font-black">✓</span>
                    </div>
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60">
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Critical Barrier</span>
                      <span className="font-bold text-amber-300 truncate block mt-0.5 text-[11px]">
                        {selectedAlert.critical_barrier || 'Exclusion Zone Barrier'}
                      </span>
                    </div>
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60">
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Barrier Condition</span>
                      <span className="font-bold text-rose-400 truncate block mt-0.5 text-[11px]">
                        {selectedAlert.barrier_condition || 'Violated'}
                      </span>
                    </div>
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60 col-span-2">
                      <span className="text-[9px] text-slate-400 uppercase font-bold block">Potential Consequence</span>
                      <span className="font-bold text-slate-100 block mt-0.5 text-[11px]">
                        {selectedAlert.potential_consequence || 'Struck-by / line-of-fire from hazard'}
                      </span>
                    </div>
                    <div className="bg-slate-800/80 p-2 rounded-lg border border-slate-700/60 col-span-2 flex items-center justify-between">
                      <div>
                        <span className="text-[9px] text-slate-400 uppercase font-bold block">Life-Saving Rule</span>
                        <span className="font-bold text-amber-300 block mt-0.5 text-[11px]">
                          {selectedAlert.life_saving_rule || 'Line of Fire'}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 font-semibold uppercase">IOGP STANDARD</span>
                    </div>
                  </div>

                  {selectedAlert.sif_why && selectedAlert.sif_why.length > 0 && (
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Why SIF Potential?
                      </span>
                      <ul className="space-y-1 text-slate-300 text-[11px]">
                        {selectedAlert.sif_why.map((w, idx) => (
                          <li key={idx} className="flex items-start space-x-1.5">
                            <span className="text-amber-400 font-bold shrink-0">•</span>
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* ==================================================== */}
                {/* PHASE 3: EVENT-SPECIFIC ACTION RECOMMENDATION LAYER   */}
                {/* ==================================================== */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-1 shadow-xs">
                    <span className="text-[10px] font-black uppercase tracking-wider text-amber-800 block">
                      IMMEDIATE ACTION
                    </span>
                    <p className="text-xs font-bold text-slate-900 leading-snug">
                      {selectedAlert.immediate_action || 'Stop/hold the hazardous activity and clear the danger zone.'}
                    </p>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 space-y-1 shadow-xs">
                    <span className="text-[10px] font-black uppercase tracking-wider text-rose-800 block">
                      IF ACTION IS NOT TAKEN
                    </span>
                    <p className="text-xs font-semibold text-slate-700 leading-snug">
                      {selectedAlert.consequence_if_not_addressed || 'Continued exposure may result in serious injury or fatality.'}
                    </p>
                  </div>
                </div>

                {/* ==================================================== */}
                {/* PHASE 4: CORRECTIVE ACTION & VERIFICATION LIFECYCLE   */}
                {/* ==================================================== */}

                {/* Stage 1: WAITING_FOR_RESPONSE (20s SLA Timer) */}
                {selectedAlert.status === 'WAITING_FOR_RESPONSE' && !acknowledgedAlertIds.has(selectedAlert.id) && (
                  <div className="bg-white rounded-xl border-2 border-red-400 p-4 shadow-sm text-center space-y-3">
                    <div className="flex items-center justify-between text-xs font-bold text-red-700 border-b border-red-100 pb-2">
                      <span className="uppercase tracking-wider">Response Required</span>
                      <span className="bg-red-100 px-2 py-0.5 rounded text-red-800 font-mono font-black">
                        ⏱ {remainingSec}s REMAINING
                      </span>
                    </div>

                    <button
                      onClick={() => handleResponding(selectedAlert.id)}
                      disabled={submitting || acknowledgedAlertIds.has(selectedAlert.id)}
                      className="w-full py-3.5 px-4 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-black text-base rounded-xl shadow-lg shadow-red-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                    >
                      <Activity className="w-5 h-5 animate-spin-slow" />
                      <span>{submitting ? 'RECORDING...' : (acknowledgedAlertIds.has(selectedAlert.id) ? 'ACKNOWLEDGED' : "ACKNOWLEDGE / I'M RESPONDING")}</span>
                    </button>
                    <p className="text-[11px] text-slate-500">
                      Acknowledge alert within 20s to satisfy Stage 1 response SLA
                    </p>
                  </div>
                )}

                {/* Stage 2: RESPONDING (In Action, not yet completed) */}
                {(selectedAlert.status === 'RESPONDING' || acknowledgedAlertIds.has(selectedAlert.id)) && selectedAlert.action_status !== 'COMPLETED' && (
                  <div className="bg-white rounded-xl border-2 border-amber-400 p-4 shadow-sm space-y-3">
                    <div className="flex items-center justify-between text-xs font-bold text-amber-800 border-b border-amber-100 pb-2">
                      <span className="uppercase tracking-wider">You Are Responding • Action Required</span>
                      <span className="bg-amber-100 px-2 py-0.5 rounded text-amber-900 font-mono font-black">
                        ⏱ {Math.floor(remainingSec / 60)}:{(remainingSec % 60).toString().padStart(2, '0')}
                      </span>
                    </div>

                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1">
                      <span className="font-bold text-amber-900 block">ACTION STATUS: IN PROGRESS</span>
                      <p className="text-[11px] text-amber-800">
                        Execute immediate control on-site. Once completed, tap below to submit for safety verification.
                      </p>
                    </div>

                    <button
                      onClick={() => handleMarkActionTaken(selectedAlert)}
                      disabled={submitting}
                      className="w-full py-3.5 px-4 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-black text-sm rounded-xl shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                    >
                      <Check className="w-5 h-5" />
                      <span>{submitting ? 'RECORDING...' : 'ACTION TAKEN / PROCEED TO VERIFICATION'}</span>
                    </button>
                    <p className="text-[11px] text-center text-slate-500">
                      Recording action taken transitions alert to Awaiting Verification
                    </p>
                  </div>
                )}

                {/* Stage 3: AWAITING VERIFICATION (Phase 4 State Machine) */}
                {(selectedAlert.verification_status === 'AWAITING_VERIFICATION' || selectedAlert.action_status === 'COMPLETED') && (
                  <div className="bg-white rounded-xl border-2 border-purple-400 p-4 shadow-sm space-y-3">
                    <div className="flex items-center justify-between text-xs font-bold text-purple-900 border-b border-purple-100 pb-2">
                      <div className="flex items-center space-x-1.5">
                        <ShieldCheck className="w-4 h-4 text-purple-600" />
                        <span className="uppercase tracking-wider">Verification Required</span>
                      </div>
                      <span className="bg-purple-100 px-2 py-0.5 rounded text-purple-800 font-mono font-black text-[10px]">
                        {selectedAlert.verification_type === 'CCTV_VERIFIABLE' ? 'CCTV VERIFIABLE' : 'FIELD HSE VERIFICATION'}
                      </span>
                    </div>

                    <div className="p-3 bg-purple-50/70 border border-purple-200 rounded-lg text-xs space-y-1">
                      <div className="flex justify-between text-slate-700">
                        <span className="font-semibold">ACTION STATUS:</span>
                        <span className="font-black text-emerald-700">Completed</span>
                      </div>
                      <div className="flex justify-between text-slate-700">
                        <span className="font-semibold">VERIFICATION:</span>
                        <span className="font-black text-purple-700">Pending Review</span>
                      </div>
                      <p className="text-[11px] text-slate-600 pt-1 border-t border-purple-100">
                        {selectedAlert.verification_type === 'CCTV_VERIFIABLE'
                          ? 'Physical clearance can be confirmed directly via live CCTV feed or supervisor inspection.'
                          : 'Procedural/isolation controls require field physical verification or documentation review.'}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {selectedAlert.verification_type === 'CCTV_VERIFIABLE' ? (
                        <button
                          onClick={() => handleVerifyAlert(selectedAlert, 'VERIFIED', 'CCTV_VERIFIED')}
                          disabled={submitting}
                          className="py-3 px-3 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-black text-xs rounded-xl shadow-sm flex items-center justify-center space-x-1.5 disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          <span>VERIFY FIX VIA CCTV</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleVerifyAlert(selectedAlert, 'VERIFIED', 'PHYSICAL_INSPECTION')}
                          disabled={submitting}
                          className="py-3 px-3 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-black text-xs rounded-xl shadow-sm flex items-center justify-center space-x-1.5 disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          <span>VERIFY ON-SITE</span>
                        </button>
                      )}

                      <button
                        onClick={() => handleVerifyAlert(selectedAlert, 'FAILED', 'PHYSICAL_INSPECTION')}
                        disabled={submitting}
                        className="py-3 px-3 bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-300 font-bold text-xs rounded-xl shadow-sm flex items-center justify-center space-x-1.5 disabled:opacity-50"
                      >
                        <X className="w-4 h-4 text-rose-600" />
                        <span>FAILED — REOPEN</span>
                      </button>
                    </div>

                    <button
                      onClick={() => handleVerifyAlert(selectedAlert, 'HSE_REVIEW_REQUIRED', 'DOCUMENTATION')}
                      disabled={submitting}
                      className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] rounded-lg transition-colors"
                    >
                      Request Formal HSE Audit / Clearance
                    </button>
                  </div>
                )}

                {/* ESCALATED: Clean Status Card (No Purple Wall of Text) */}
                {selectedAlert.status === 'ESCALATED' && (
                  <div className="bg-white rounded-xl border-2 border-slate-300 p-4 shadow-sm space-y-3">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-950 space-y-1">
                      <div className="flex items-center space-x-1.5 text-xs font-black text-red-700 uppercase tracking-wide">
                        <AlertOctagon className="w-4 h-4 text-red-600" />
                        <span>ESCALATED TO HSE CONTROL DESK / HSE MANAGER</span>
                      </div>
                      <p className="text-xs font-medium text-slate-700 mt-1">
                        Supervisor response was not received within 20 seconds. Work remains PAUSED.
                      </p>
                    </div>

                    <div className="text-xs space-y-2 text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Assigned To:</span>
                        <span className="font-bold text-slate-900">{selectedAlert.assigned_to || 'HSE CONTROL DESK'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Priority:</span>
                        <span className="font-bold text-red-600">CRITICAL</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Current Status:</span>
                        <span className="font-bold text-amber-700">OPEN — ACTION REQUIRED</span>
                      </div>
                    </div>

                    {selectedAlert.type === 'SAFETY PASSPORT BREACH' ? (
                      (activePassport?.status === 'AWAITING_RESTORATION' || !status?.zone_violation) ? (
                        <button
                          onClick={() => handleVerifyBarrierRestored(selectedAlert)}
                          disabled={submitting}
                          className="w-full py-3.5 px-4 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-black text-sm rounded-xl shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          <span>{submitting ? 'VERIFYING...' : 'VERIFY BARRIER RESTORED'}</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleResponding(selectedAlert.id)}
                          disabled={submitting || acknowledgedAlertIds.has(selectedAlert.id)}
                          className="w-full py-3.5 px-4 bg-slate-900 hover:bg-slate-800 active:bg-black text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                        >
                          <Activity className="w-4 h-4 text-amber-400" />
                          <span>{submitting ? 'RECORDING...' : (acknowledgedAlertIds.has(selectedAlert.id) ? 'ACKNOWLEDGED' : "I'M RESPONDING (LATE)")}</span>
                        </button>
                      )
                    ) : (
                      <button
                        onClick={() => handleResolved(selectedAlert)}
                        disabled={submitting}
                        className="w-full py-3.5 px-4 bg-slate-900 hover:bg-slate-800 active:bg-black text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>{submitting ? 'RESOLVING...' : 'RESOLVE ON-SITE'}</span>
                      </button>
                    )}
                    <p className="text-[11px] text-center text-slate-500">
                      Field supervisor can still verify compliance and resolve the condition on site
                    </p>
                  </div>
                )}
              </div>
            ) : (
              /* VIEW B: ALERT INBOX (Home screen for supervisor) */
              <div className="space-y-3 flex-1 flex flex-col">
                {/* Inbox Status Bar */}
                <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-black text-slate-900 uppercase tracking-tight">
                      Supervisor Alerts
                    </h2>
                    <p className="text-[11px] font-medium text-slate-500 mt-0.5">
                      {activeAlerts.length === 0 
                        ? 'No active incidents' 
                        : `${activeAlerts.length} active observation${activeAlerts.length > 1 ? 's' : ''} requiring attention`}
                    </p>
                  </div>

                  {activeAlerts.length > 0 && (
                    <div className="flex items-center space-x-1.5 text-[10px] font-black">
                      {criticalCount > 0 && (
                        <span className="px-2 py-1 rounded bg-red-100 text-red-700 border border-red-200">
                          CRITICAL: {criticalCount}
                        </span>
                      )}
                      {highCount > 0 && (
                        <span className="px-2 py-1 rounded bg-amber-100 text-amber-800 border border-amber-200">
                          HIGH: {highCount}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* List of Active Alert Cards (or Empty State) */}
                {activeAlerts.length > 0 ? (
                  <div className="space-y-2.5">
                    {activeAlerts.map((alert, idx) => {
                      const isProximity = alert.is_high_priority || alert.type === 'Person–Vehicle Proximity';
                      const isFire = alert.fire_detected || alert.type?.toLowerCase().includes('fire') || alert.title?.toLowerCase().includes('fire');
                      const isPassportBreach = alert.type === 'SAFETY PASSPORT BREACH';
                      const isZone = alert.type === 'Restricted Zone Entry';
                      const isWaiting = alert.status === 'WAITING_FOR_RESPONSE';
                      const isResponding = alert.status === 'RESPONDING';
                      const isEscalated = alert.status === 'ESCALATED';

                      const sifLevel = alert.sif_level || (alert.priority_score >= 100 ? 'HIGH' : 'MEDIUM');
                      const personCount = alert.person_count || (alert.affected_person_ids?.length || 1);
                      const isAwaitingVerification = alert.verification_status === 'AWAITING_VERIFICATION' || alert.action_status === 'COMPLETED';

                      return (
                        <div
                          key={alert.id}
                          className={`rounded-xl border-2 p-3.5 shadow-sm transition-all flex flex-col justify-between space-y-3 ${
                            sifLevel === 'CRITICAL' || isProximity || isFire
                              ? 'bg-rose-50/70 border-rose-400 ring-2 ring-rose-400/20'
                              : isEscalated 
                              ? 'border-rose-400 bg-rose-50/30' 
                              : isWaiting 
                              ? 'border-red-400 bg-red-50/30'
                              : isAwaitingVerification
                              ? 'border-purple-400 bg-purple-50/30'
                              : 'border-amber-400 bg-amber-50/20'
                          }`}
                        >
                          {/* 1. Header: SIF POTENTIAL + Priority badge */}
                          <div className="flex items-start justify-between border-b border-slate-200/80 pb-2">
                            <div className="flex items-center space-x-2">
                              <span className="text-base leading-none">🚨</span>
                              <div>
                                <div className="text-xs font-black text-rose-700 uppercase tracking-wider flex items-center space-x-1.5">
                                  <span>SIF POTENTIAL</span>
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-black uppercase text-white ${
                                    sifLevel === 'CRITICAL' || isProximity || isFire ? 'bg-red-600' : 'bg-amber-600'
                                  }`}>
                                    {sifLevel} PRIORITY
                                  </span>
                                </div>
                                <div className="text-[10px] font-mono text-slate-500 font-bold mt-0.5">
                                  {alert.location} • Camera {alert.camera || 'C-01'}
                                </div>
                              </div>
                            </div>

                            <span className="text-[10px] font-mono font-bold text-slate-500">
                              {alert.id}
                            </span>
                          </div>

                          {/* 2. EVENT Label */}
                          <div>
                            <span className="text-[9px] font-black uppercase text-slate-400 tracking-wider block">
                              EVENT
                            </span>
                            <h3 className="text-xs font-black text-slate-900 leading-snug mt-0.5">
                              {alert.title || alert.type}
                            </h3>
                          </div>

                          {/* 3. WHY SIF POTENTIAL? Compact Bullets */}
                          <div className="bg-white/90 rounded-lg p-2.5 border border-slate-200/80 space-y-1">
                            <span className="text-[9px] font-black uppercase tracking-wider text-slate-500 block">
                              WHY SIF POTENTIAL?
                            </span>
                            <ul className="text-[11px] text-slate-700 font-medium space-y-0.5">
                              <li className="flex items-start space-x-1.5">
                                <span className="text-rose-600 font-bold shrink-0">•</span>
                                <span>{personCount} person(s) exposed to active hazard activity</span>
                              </li>
                              <li className="flex items-start space-x-1.5">
                                <span className="text-rose-600 font-bold shrink-0">•</span>
                                <span>Critical exclusion barrier ({alert.critical_barrier || 'Exclusion zone'}) violated</span>
                              </li>
                              <li className="flex items-start space-x-1.5">
                                <span className="text-rose-600 font-bold shrink-0">•</span>
                                <span>{alert.potential_consequence || 'Potential line-of-fire / struck-by consequence'}</span>
                              </li>
                            </ul>
                          </div>

                          {/* 4. IMMEDIATE ACTION */}
                          <div className="bg-amber-50/80 border border-amber-200 rounded-lg p-2">
                            <span className="text-[9px] font-black uppercase tracking-wider text-amber-900 block">
                              IMMEDIATE ACTION
                            </span>
                            <p className="text-[11px] font-bold text-slate-900 mt-0.5 leading-snug">
                              {alert.immediate_action || 'Stop/hold hazardous activity and clear the danger zone.'}
                            </p>
                          </div>

                          {/* 5. IF ACTION IS NOT TAKEN */}
                          <div className="bg-rose-50/60 border border-rose-200 rounded-lg p-2">
                            <span className="text-[9px] font-black uppercase tracking-wider text-rose-900 block">
                              IF ACTION IS NOT TAKEN
                            </span>
                            <p className="text-[11px] font-medium text-slate-700 mt-0.5 leading-snug">
                              {alert.consequence_if_not_addressed || 'Continued exposure may result in serious injury or fatality.'}
                            </p>
                          </div>

                          {/* 6. RESPONSE ACTION BUTTONS & SLA */}
                          <div className="pt-1 flex items-center justify-between flex-wrap gap-2 border-t border-slate-200/60">
                            <div className="flex items-center space-x-1.5">
                              {isWaiting && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleResponding(alert.id);
                                  }}
                                  disabled={submitting || acknowledgedAlertIds.has(alert.id)}
                                  className="px-3.5 py-1.5 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white rounded-lg text-xs font-black shadow-xs transition-colors disabled:opacity-50 flex items-center space-x-1"
                                >
                                  <span>[ ACKNOWLEDGE ]</span>
                                </button>
                              )}

                              {isResponding && !isAwaitingVerification && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleMarkActionTaken(alert);
                                  }}
                                  disabled={submitting}
                                  className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 rounded-lg text-xs font-black shadow-xs transition-colors disabled:opacity-50"
                                >
                                  <span>[ ACTION TAKEN ]</span>
                                </button>
                              )}

                              {isAwaitingVerification && (
                                <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-900 border border-purple-200 text-[10px] font-black uppercase">
                                  AWAITING VERIFICATION
                                </span>
                              )}
                            </div>

                            <button
                              onClick={() => setSelectedAlertId(alert.id)}
                              className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold flex items-center space-x-1 shadow-xs ml-auto"
                            >
                              <span>[ VIEW DETAILS ]</span>
                              <ChevronRight className="w-3.5 h-3.5 text-amber-400" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  /* Zero State */
                  <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-3 my-auto shadow-sm">
                    <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto">
                      <ShieldCheck className="w-8 h-8" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-slate-900">
                        Work Zone Compliant
                      </h3>
                      <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                        No active safety hazards detected on site. All workers compliant and restricted areas clear.
                      </p>
                    </div>
                    <div className="pt-2">
                      <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-[11px] font-bold">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span>AI Vision Monitoring Active</span>
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* ======================================================== */}
        {/* TAB 2: OBSERVATION HISTORY (FULLY FUNCTIONAL REAL DATA)  */}
        {/* ======================================================== */}
        {currentTab === 'history' && (
          <div className="space-y-3 flex-1 flex flex-col">
            {selectedHistoryAlert ? (
              /* HISTORY DETAIL VIEW */
              <div className="space-y-3.5 flex-1 flex flex-col">
                <button
                  onClick={() => setSelectedHistoryAlert(null)}
                  className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm w-fit"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to History</span>
                </button>

                {/* Header Card */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                      (selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at)
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}>
                      {(selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at)
                        ? 'ESCALATED → RESOLVED'
                        : 'RESOLVED'}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 font-bold">
                      {selectedHistoryAlert.id}
                    </span>
                  </div>
                  <h2 className="text-lg font-black text-slate-900 tracking-tight">
                    {selectedHistoryAlert.title || selectedHistoryAlert.type}
                  </h2>
                  <p className="text-xs font-medium text-slate-600">
                    {selectedHistoryAlert.short_summary || selectedHistoryAlert.unsafe_condition}
                  </p>
                </div>

                {/* CCTV Visual Evidence Frame in History (CHANGE 1, CHANGE 10, CHANGE 15) */}
                {(selectedHistoryAlert.evidence_image || selectedHistoryAlert.evidence_url) && (
                  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                    <div className="bg-slate-900 text-white px-3 py-2 flex items-center justify-between">
                      <div className="flex items-center space-x-1.5">
                        <Video className="w-3.5 h-3.5 text-amber-400" />
                        <span className="text-[10px] font-black uppercase tracking-wider">CCTV Evidence Image</span>
                      </div>
                      <span className="font-mono text-slate-400 text-[9px]">
                        Camera: {selectedHistoryAlert.camera || selectedHistoryAlert.camera_id || 'C-01'} • {selectedHistoryAlert.location}
                      </span>
                    </div>
                    <div className="relative bg-slate-950 flex items-center justify-center">
                      <img
                        src={selectedHistoryAlert.evidence_image || selectedHistoryAlert.evidence_url}
                        alt="Historical Evidence"
                        className="w-full max-h-56 object-contain"
                      />
                    </div>
                  </div>
                )}

                {/* Detailed Key/Value Grid */}
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2.5 text-xs">
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 border-b border-slate-100 pb-1.5">
                    Alert History Specifications
                  </h3>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Alert Type</span>
                    <span className="font-bold text-slate-900">{selectedHistoryAlert.type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Final Status</span>
                    <span className={`font-black uppercase ${
                      (selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at)
                        ? 'text-amber-700'
                        : 'text-emerald-700'
                    }`}>
                      {(selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at)
                        ? 'ESCALATED → RESOLVED'
                        : 'RESOLVED'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Source</span>
                    <span className="font-bold text-slate-800">{selectedHistoryAlert.source || 'AI CCTV'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">People</span>
                    <span className="font-bold text-slate-800">
                      {selectedHistoryAlert.person_count || 1}
                      {selectedHistoryAlert.affected_person_ids?.length > 0 && (
                        ` (${selectedHistoryAlert.affected_person_ids.join(', ')})`
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Location</span>
                    <span className="font-bold text-slate-800">{selectedHistoryAlert.location}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Camera</span>
                    <span className="font-mono font-bold text-slate-800">
                      {selectedHistoryAlert.camera || selectedHistoryAlert.camera_id || 'C-01'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Created</span>
                    <span className="font-mono font-semibold text-slate-700">
                      {formatTime(selectedHistoryAlert.created_at)}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Responded</span>
                    <span className="font-mono font-semibold text-slate-700">
                      {selectedHistoryAlert.responded_at 
                        ? formatTime(selectedHistoryAlert.responded_at) 
                        : 'N/A (Escalated)'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Resolved</span>
                    <span className="font-mono font-semibold text-slate-700">
                      {formatTime(selectedHistoryAlert.resolved_at || selectedHistoryAlert.created_at)}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Response Time</span>
                    <span className="font-mono font-bold text-slate-900">
                      {selectedHistoryAlert.responded_at 
                        ? formatDuration(selectedHistoryAlert.created_at, selectedHistoryAlert.responded_at)
                        : 'N/A (Escalated)'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Resolution Time</span>
                    <span className="font-mono font-bold text-slate-900">
                      {formatDuration(selectedHistoryAlert.created_at, selectedHistoryAlert.resolved_at)}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Escalation</span>
                    <span className={`font-bold ${
                      (selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at)
                        ? 'text-red-600'
                        : 'text-slate-800'
                    }`}>
                      {(selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at) ? 'YES' : 'None'}
                    </span>
                  </div>
                  {(selectedHistoryAlert.was_escalated || selectedHistoryAlert.escalated_at) && (
                    <div className="flex justify-between py-1 border-b border-slate-100 bg-rose-50/60 px-2 rounded">
                      <span className="text-rose-700 font-medium">Escalated To</span>
                      <span className="font-bold text-rose-900">
                        {selectedHistoryAlert.assigned_to || 'HSE Control Desk'}
                      </span>
                    </div>
                  )}
                  {selectedHistoryAlert.notes && (
                    <div className="pt-1 text-slate-600">
                      <span className="text-[10px] font-bold uppercase text-slate-400 block mb-0.5">Resolution Notes</span>
                      <p className="bg-slate-50 p-2 rounded border border-slate-200 text-slate-700">
                        {selectedHistoryAlert.notes}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* HISTORY LIST VIEW */
              <div className="space-y-3 flex-1 flex flex-col">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <History className="w-4 h-4 text-slate-600" />
                    <h2 className="text-xs font-black uppercase tracking-wider text-slate-800">
                      Observation History
                    </h2>
                  </div>
                  <button
                    onClick={loadHistory}
                    disabled={historyLoading}
                    className="p-1 hover:text-slate-900 text-slate-400 transition-colors"
                    title="Refresh History"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${historyLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                {/* Loading State */}
                {historyLoading && historyAlerts.length === 0 && (
                  <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-2 shadow-sm my-auto">
                    <RefreshCw className="w-6 h-6 text-slate-400 animate-spin mx-auto" />
                    <p className="text-xs font-bold text-slate-600">Loading history...</p>
                  </div>
                )}

                {/* Error State */}
                {historyError && (
                  <div className="bg-white rounded-xl border border-red-200 bg-red-50/50 p-6 text-center space-y-3 shadow-sm my-auto">
                    <AlertOctagon className="w-7 h-7 text-red-500 mx-auto" />
                    <p className="text-xs font-bold text-red-900">{historyError}</p>
                    <button
                      onClick={loadHistory}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-colors inline-flex items-center space-x-1.5 shadow-sm"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>RETRY</span>
                    </button>
                  </div>
                )}

                {/* Empty State */}
                {!historyLoading && !historyError && historyAlerts.length === 0 && (
                  <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-3 my-auto shadow-sm">
                    <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto">
                      <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-slate-800">
                        ✓ NO ALERT HISTORY
                      </h3>
                      <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1">
                        Safety events that are resolved will appear here.
                      </p>
                    </div>
                  </div>
                )}

                {/* Real History Cards */}
                {historyAlerts.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 uppercase tracking-wider px-1">
                      <span>TODAY</span>
                      <span>{historyAlerts.length} {historyAlerts.length === 1 ? 'RECORD' : 'RECORDS'}</span>
                    </div>

                    {historyAlerts.map(item => {
                      const wasEsc = item.was_escalated || item.escalated_at;
                      return (
                        <div
                          key={item.id}
                          onClick={() => setSelectedHistoryAlert(item)}
                          className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm hover:border-slate-400 active:bg-slate-50 transition-all cursor-pointer space-y-2"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center space-x-2">
                              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-black shrink-0 ${
                                wasEsc ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'
                              }`}>
                                {wasEsc ? '⚠' : '✓'}
                              </span>
                              <span className="text-xs font-black uppercase tracking-tight text-slate-900">
                                {item.title || item.type}
                              </span>
                            </div>
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded border uppercase tracking-wider shrink-0 ${
                              wasEsc 
                                ? 'bg-amber-50 text-amber-800 border-amber-200' 
                                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            }`}>
                              {wasEsc ? 'ESCALATED → RESOLVED' : 'RESOLVED'}
                            </span>
                          </div>

                          <div className="text-xs font-semibold text-slate-700 line-clamp-1">
                            {item.short_summary || item.unsafe_condition || item.title}
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1.5 border-t border-slate-100">
                            <div className="flex items-center space-x-2 truncate">
                              <span className="font-semibold text-slate-800 shrink-0">
                                {item.person_count || 1} {item.person_count > 1 ? 'people' : 'person'}
                              </span>
                              <span>•</span>
                              <span className="truncate max-w-[130px] font-medium text-slate-600">
                                {item.location}
                              </span>
                              <span>•</span>
                              <span className="font-mono font-medium shrink-0">C-{item.camera || '01'}</span>
                            </div>
                            <span className="font-mono text-slate-400 font-semibold shrink-0 ml-2">
                              {formatTime(item.resolved_at || item.created_at)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 3: SAFETY PASSPORT (MOBILE PREVENTIVE CLEARANCE)       */}
        {/* ======================================================== */}
        {currentTab === 'passport' && (
          <div className="space-y-3.5 flex-1 flex flex-col text-xs">
            {/* Header / Action Bar */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-5 h-5 text-slate-800" />
                <div>
                  <h2 className="text-xs font-black uppercase tracking-tight text-slate-900">
                    Safety Passport
                  </h2>
                  <p className="text-[10px] text-slate-500 font-semibold uppercase">
                    High-Risk Work Authorization
                  </p>
                </div>
              </div>

              <button
                onClick={() => setIsCreatePassportModalOpen(true)}
                className="px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold flex items-center space-x-1 shadow-sm"
              >
                <PlusCircle className="w-3.5 h-3.5 text-amber-400" />
                <span>+ Request Task</span>
              </button>
            </div>

            {/* Active Passport Display or Empty State */}
            {activePassport ? (
              <div className="space-y-3">
                {/* ---------------------------------------------------- */}
                {/* STATE A: PAUSED OR AWAITING RESTORATION             */}
                {/* ---------------------------------------------------- */}
                {(activePassport.status === 'PAUSED' || activePassport.status === 'AWAITING_RESTORATION') && (
                  <div className={`p-4 rounded-xl border-2 shadow-sm space-y-3 ${
                    activePassport.status === 'PAUSED' ? 'bg-red-50 border-red-300' : 'bg-amber-50 border-amber-300'
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                        activePassport.status === 'PAUSED' ? 'bg-red-600 text-white animate-pulse' : 'bg-amber-500 text-white'
                      }`}>
                        {activePassport.status === 'PAUSED' ? '🔴 SAFETY PASSPORT PAUSED' : '🟡 AWAITING BARRIER RESTORATION'}
                      </span>
                      <span className="font-mono text-[11px] font-bold text-slate-500">
                        {activePassport.id}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-black text-slate-900 tracking-tight">
                        {activePassport.task_type}
                      </h3>
                      <p className="text-xs font-bold text-slate-600 mt-0.5">
                        {activePassport.location} • {activePassport.linked_zone_name}
                      </p>
                    </div>

                    {/* Breach details */}
                    <div className="p-3 bg-red-100/70 border border-red-200 rounded-lg text-red-950 space-y-1">
                      <div className="flex items-center space-x-1.5 font-bold text-xs text-red-800">
                        <AlertTriangle className="w-4 h-4 text-red-600 animate-pulse shrink-0" />
                        <span className="uppercase">Restricted Zone Breach Detected</span>
                      </div>
                      <p className="text-[11px] text-red-800">
                        {activePassport.breach_reason || 'Lifting exclusion zone entered during Mechanical Lifting'}. High-risk work is halted immediately.
                      </p>
                    </div>

                    {/* Zone condition and restoration action */}
                    {(activePassport?.status === 'AWAITING_RESTORATION' || !status?.zone_violation) ? (
                      <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-emerald-950 space-y-2">
                        <div className="flex items-center space-x-1.5 font-bold text-[11px] uppercase text-emerald-800">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                          <span>Zone is clear — human verification required</span>
                        </div>
                        <p className="text-[11px] text-emerald-700">
                          AI CCTV indicates exclusion zone is clear. Supervisor must physically inspect and verify barrier restoration to reactivate.
                        </p>
                        <button
                          onClick={() => handleVerifyBarrierRestored(null)}
                          disabled={submitting}
                          className="w-full py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-lg shadow-md flex items-center justify-center space-x-1.5 disabled:opacity-50 transition-all"
                        >
                          <Check className="w-4 h-4" />
                          <span>VERIFY BARRIER RESTORED</span>
                        </button>
                      </div>
                    ) : (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-center space-y-2">
                        <p className="text-[11px] font-bold text-red-700">
                          Exclusion zone currently occupied. Direct workers to clear the area immediately.
                        </p>
                        <button
                          disabled
                          className="w-full py-2.5 px-3 bg-slate-200 text-slate-500 font-bold text-xs rounded-lg cursor-not-allowed"
                        >
                          Awaiting Zone Clearance...
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* ---------------------------------------------------- */}
                {/* STATE B: ACTIVE PASSPORT                            */}
                {/* ---------------------------------------------------- */}
                {activePassport.status === 'ACTIVE' && (
                  <>
                    {!showPassportDetails ? (
                      /* STAGE 3: Compact Active Passport Card (CHANGE 11) */
                      <div className="p-4 rounded-xl border-2 border-emerald-300 bg-white shadow-sm space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-1.5 font-black text-xs text-emerald-800">
                            <Shield className="w-4 h-4 text-emerald-600" />
                            <span>🛡 SAFETY PASSPORT</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
                            🟢 ACTIVE
                          </span>
                        </div>

                        <div>
                          <h3 className="text-base font-black text-slate-900 tracking-tight">
                            {activePassport.task_type}
                          </h3>
                          <p className="text-xs font-bold text-slate-600 mt-0.5">
                            {activePassport.location}
                          </p>
                        </div>

                        {/* Temporary Zone & Countdown per CHANGE 11 */}
                        <div className="p-3 bg-amber-50/80 rounded-lg border border-amber-200 space-y-1">
                          <div className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
                            Temporary Zone:
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-slate-900">
                              🟠 {activePassport.linked_zone_name || 'Lifting Exclusion Zone'}
                            </span>
                            <span className="font-mono text-xs font-black text-amber-900">
                              ⏱ Expires in: {passportTimeLeft}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between px-1 text-xs">
                          <span className="text-slate-500 font-bold uppercase text-[10px]">Controls:</span>
                          <span className="font-bold text-emerald-700">
                            {activePassport.controls?.filter(c => c.verified).length || 6} / {activePassport.controls?.length || 6}
                          </span>
                        </div>

                        <div className="pt-1 flex items-center space-x-2">
                          <button
                            onClick={() => setShowPassportDetails(true)}
                            className="flex-1 py-2.5 px-3 bg-slate-900 hover:bg-slate-800 text-white font-black text-xs rounded-lg shadow-sm flex items-center justify-center space-x-1.5 transition-all"
                          >
                            <FileText className="w-4 h-4 text-amber-400" />
                            <span>VIEW DETAILS</span>
                          </button>
                          <button
                            onClick={async () => {
                              try {
                                setSubmitting(true);
                                await closePassport(activePassport.id);
                                setResolveSuccessMsg('✓ Safety Passport closed');
                              } catch (e) {
                                setErrorMsg(e.message || 'Close failed');
                              } finally {
                                setSubmitting(false);
                              }
                            }}
                            disabled={submitting}
                            className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition-colors border border-slate-200"
                          >
                            Close Task
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* STAGE 4: Full Passport Details & Audit Timeline (CHANGE 11) */
                      <div className="space-y-3">
                        <button
                          onClick={() => setShowPassportDetails(false)}
                          className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm"
                        >
                          <ArrowLeft className="w-3.5 h-3.5" />
                          <span>Back to Active Card</span>
                        </button>

                        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                            <div>
                              <span className="text-xs font-black uppercase text-slate-900">
                                {activePassport.task_type}
                              </span>
                              <p className="text-[11px] text-slate-500 font-medium">
                                {activePassport.location} • Permit: {activePassport.permit_reference || 'N/A'}
                              </p>
                            </div>
                            <span className="font-mono text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
                              ⏱ Valid: {passportTimeLeft}
                            </span>
                          </div>

                          {/* Temporary Zone Section in Details (CHANGE 11) */}
                          <div className="p-3 bg-amber-50/70 rounded-lg border border-amber-200 space-y-1 text-xs">
                            <div className="text-[10px] font-black uppercase tracking-wider text-amber-800">
                              🟠 Temporary Passport Zone
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                              <div>
                                <span className="text-slate-500 block">Name:</span>
                                <span className="font-bold text-slate-900">{activePassport.linked_zone_name || 'Lifting Exclusion Zone'}</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Camera:</span>
                                <span className="font-mono font-bold text-slate-900">{activePassport.camera_id || 'C-01'}</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Status:</span>
                                <span className="font-bold text-emerald-700">ACTIVE</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Expiry Countdown:</span>
                                <span className="font-mono font-bold text-amber-900">⏱ {passportTimeLeft}</span>
                              </div>
                            </div>
                          </div>

                          {/* Verified Controls Provenance */}
                          <div className="space-y-1.5">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                              Controls Provenance (6/6 Verified)
                            </div>
                            {activePassport.controls?.map(ctrl => (
                              <div key={ctrl.id} className="p-2 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                                <div className="min-w-0 pr-2">
                                  <div className="font-bold text-slate-800 text-[11px] truncate">{ctrl.name}</div>
                                  <div className="text-[9px] text-slate-500">
                                    {ctrl.verification_source} • {ctrl.verified_by || 'Verified'}
                                  </div>
                                </div>
                                <span className="text-[10px] font-bold text-emerald-600 shrink-0">✓ OK</span>
                              </div>
                            ))}
                          </div>

                          {/* Audit Timeline */}
                          {activePassport.events?.length > 0 && (
                            <div className="space-y-2 pt-2 border-t border-slate-100">
                              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                Audit Timeline ({activePassport.events.length} events)
                              </div>
                              <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                                {activePassport.events.slice().reverse().map(evt => (
                                  <div key={evt.id} className="text-[10px] p-2 bg-slate-50 rounded border border-slate-100">
                                    <div className="flex items-center justify-between text-slate-500 font-medium">
                                      <span>{evt.actor}</span>
                                      <span>{formatTime(evt.timestamp)}</span>
                                    </div>
                                    <p className="text-slate-800 font-semibold mt-0.5">{evt.description}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Close Button */}
                          <button
                            onClick={async () => {
                              try {
                                setSubmitting(true);
                                await closePassport(activePassport.id);
                                setResolveSuccessMsg('✓ Safety Passport closed');
                                setShowPassportDetails(false);
                              } catch (e) {
                                setErrorMsg(e.message || 'Close failed');
                              } finally {
                                setSubmitting(false);
                              }
                            }}
                            disabled={submitting}
                            className="w-full py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition-colors"
                          >
                            Close / Complete Task
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* ---------------------------------------------------- */}
                {/* STATE C: PRE-START VERIFICATION (STAGE 1)           */}
                {/* ---------------------------------------------------- */}
                {(activePassport.status === 'PENDING_VERIFICATION' || activePassport.status === 'PENDING_APPROVAL') && (
                  <div className="space-y-3">
                    {/* Header Card */}
                    <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-800 border border-slate-200">
                          {activePassport.status === 'PENDING_APPROVAL' ? '⏳ WAITING FOR HSE APPROVAL' : '📋 STAGE 1: PRE-START CHECKS'}
                        </span>
                        <span className="font-mono text-[11px] font-bold text-slate-500">
                          {activePassport.id}
                        </span>
                      </div>

                      <div>
                        <h3 className="text-base font-black text-slate-900 tracking-tight">
                          {activePassport.task_type}
                        </h3>
                        <p className="text-xs font-bold text-slate-600 mt-0.5">
                          {activePassport.location} • Camera {activePassport.camera_id} • {activePassport.linked_zone_name}
                        </p>
                      </div>
                    </div>

                    {/* Pre-Start Checklist */}
                    <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm space-y-2.5">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                        <span className="text-[11px] font-black uppercase text-slate-800 tracking-wider">
                          Pre-Start Controls Checklist
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                          {activePassport.controls?.filter(c => c.verified).length || 0} / {activePassport.controls?.length || 6} Verified
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        {activePassport.controls?.map(ctrl => {
                          const isHseControl = ctrl.id === 'ctrl-6' || (ctrl.verification_source || '').toUpperCase().includes('HSE');
                          
                          if (isHseControl) {
                            return (
                              <div 
                                key={ctrl.id}
                                onClick={() => {
                                  setErrorMsg('🔒 HSE Verification is an HSE-only responsibility. Pending approval on HSE Console.');
                                }}
                                className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50 flex items-center justify-between cursor-not-allowed opacity-90"
                              >
                                <div className="flex items-center space-x-2.5 min-w-0">
                                  <div className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold border border-amber-300 bg-amber-100 text-amber-700 shrink-0">
                                    <Lock className="w-3 h-3" />
                                  </div>
                                  <div className="min-w-0">
                                    <span className="text-xs font-bold text-slate-800 block truncate">
                                      {ctrl.name}
                                    </span>
                                    <span className="text-[9px] font-bold text-amber-800 flex items-center space-x-1">
                                      <span>🔒 HSE VERIFICATION — Pending HSE approval</span>
                                    </span>
                                  </div>
                                </div>

                                <span className="text-[10px] font-black px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 shrink-0 ml-2">
                                  LOCKED
                                </span>
                              </div>
                            );
                          }

                          return (
                            <div 
                              key={ctrl.id}
                              onClick={() => handleToggleControlMobile(ctrl.id, ctrl.verified)}
                              className={`p-2.5 rounded-lg border flex items-center justify-between transition-all cursor-pointer ${
                                ctrl.verified ? 'bg-emerald-50/50 border-emerald-200' : 'bg-slate-50 border-slate-200 hover:border-slate-400'
                              }`}
                            >
                              <div className="flex items-center space-x-2.5 min-w-0">
                                <div className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold border shrink-0 ${
                                  ctrl.verified ? 'bg-emerald-600 border-emerald-700 text-white' : 'bg-white border-slate-300'
                                }`}>
                                  {ctrl.verified ? '✓' : ''}
                                </div>
                                <div className="min-w-0">
                                  <span className="text-xs font-bold text-slate-800 block truncate">
                                    {ctrl.name}
                                  </span>
                                  <span className="text-[9px] font-bold text-slate-500 uppercase">
                                    {ctrl.verification_source}
                                  </span>
                                </div>
                              </div>

                              <span className={`text-[10px] font-bold shrink-0 ml-2 ${
                                ctrl.verified ? 'text-emerald-700' : 'text-slate-400'
                              }`}>
                                {ctrl.verified ? 'VERIFIED' : 'TAP TO VERIFY'}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Status Banner */}
                      <div className="pt-2 border-t border-slate-100">
                        {activePassport.controls?.filter(c => c.id !== 'ctrl-6').every(c => c.verified) ? (
                          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-center space-y-1">
                            <div className="flex items-center justify-center space-x-1.5 text-blue-900 font-bold">
                              <Clock className="w-4 h-4 text-blue-600" />
                              <span className="uppercase text-[11px] tracking-wide">WAITING FOR HSE VERIFICATION</span>
                            </div>
                            <p className="text-[10px] text-blue-700">
                              Supervisor checks complete. Formal permit authorization and activation must be cleared by HSE Manager on the HSE Console.
                            </p>
                          </div>
                        ) : (
                          <div className="text-center text-[10px] text-amber-800 font-bold py-1.5 bg-amber-50 rounded-lg border border-amber-200">
                            Complete all supervisor pre-start checks. Formal activation requires HSE clearance.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Close Passport Button */}
                    <button
                      onClick={async () => {
                        try {
                          setSubmitting(true);
                          await closePassport(activePassport.id);
                          setResolveSuccessMsg('✓ Safety Passport closed');
                        } catch (e) {
                          setErrorMsg(e.message || 'Close failed');
                        } finally {
                          setSubmitting(false);
                        }
                      }}
                      disabled={submitting}
                      className="w-full py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition-colors"
                    >
                      Cancel / Close Request
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* Empty Passport State */
              <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-3 my-auto shadow-sm">
                <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mx-auto">
                  <Shield className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-slate-900">
                    No Active High-Risk Task Clearance
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                    Before starting critical operations (e.g. Mechanical Lifting), create a time-bound Safety Passport.
                  </p>
                </div>
                <button
                  onClick={() => setIsCreatePassportModalOpen(true)}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all shadow-sm inline-flex items-center space-x-1.5"
                >
                  <PlusCircle className="w-3.5 h-3.5 text-amber-400" />
                  <span>+ Request Safety Passport</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 4: SYSTEM STATUS & TELEMETRY                         */}
        {/* ======================================================== */}
        {currentTab === 'status' && (
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3 flex-1 text-xs">
            <h2 className="text-sm font-black text-slate-900 uppercase tracking-tight flex items-center space-x-2">
              <Activity className="w-4 h-4 text-slate-600" />
              <span>System Health & Dispatcher Telemetry</span>
            </h2>

            <div className="space-y-2 text-slate-700">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">AI Vision Engine:</span>
                <span className="font-bold text-emerald-600">● ONLINE</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Total People Detected:</span>
                <span className="font-bold text-slate-900">{status?.person_count || (status?.person_detected ? 1 : 0)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Unhelmeted Workers:</span>
                <span className="font-bold text-slate-900">{status?.unhelmeted_count || (status?.person_detected && !status?.helmet_detected ? 1 : 0)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Restricted Zone:</span>
                <span className="font-bold text-slate-900">
                  {status?.active_zone ? `${status.active_zone.name} (${status.active_zone.zone_type.toUpperCase()})` : 'NO ACTIVE ZONE'}
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-500">LAN Host IP:</span>
                <span className="font-mono text-slate-900 font-bold">{status?.lan_ip || '127.0.0.1'}</span>
              </div>
            </div>
          </div>
        )}
        </>
      )}
      </main>

      {/* ======================================================== */}
      {/* BOTTOM NAVIGATION BAR (ALERTS, PASSPORT, HISTORY, STATUS) */}
      {/* ======================================================== */}
      <nav className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white border-t border-slate-200 z-30 shadow-lg flex items-center justify-around py-2">
        <button
          onClick={() => { setCurrentTab('alerts'); setSelectedAlertId(null); setSelectedHistoryAlert(null); }}
          className={`flex flex-col items-center space-y-0.5 text-[10px] font-bold ${
            currentTab === 'alerts' ? 'text-slate-900' : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <div className="relative">
            <ShieldAlert className="w-5 h-5" />
            {activeAlerts.length > 0 && (
              <span className="absolute -top-1 -right-2 w-4 h-4 rounded-full bg-red-600 text-white text-[9px] font-black flex items-center justify-center">
                {activeAlerts.length}
              </span>
            )}
          </div>
          <span>ALERTS</span>
        </button>

        <button
          onClick={() => { setCurrentTab('passport'); setSelectedAlertId(null); setSelectedHistoryAlert(null); }}
          className={`flex flex-col items-center space-y-0.5 text-[10px] font-bold ${
            currentTab === 'passport' ? 'text-slate-900' : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <div className="relative">
            <Shield className="w-5 h-5" />
            {activePassport && (
              <span className={`absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full ${
                activePassport.status === 'PAUSED' ? 'bg-red-600 animate-ping' :
                activePassport.status === 'ACTIVE' ? 'bg-emerald-500' :
                'bg-amber-500'
              }`}></span>
            )}
          </div>
          <span>PASSPORT</span>
        </button>

        <button
          onClick={() => { setCurrentTab('history'); setSelectedAlertId(null); setSelectedHistoryAlert(null); }}
          className={`flex flex-col items-center space-y-0.5 text-[10px] font-bold ${
            currentTab === 'history' ? 'text-slate-900' : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <History className="w-5 h-5" />
          <span>HISTORY</span>
        </button>

        <button
          onClick={() => { setCurrentTab('status'); setSelectedAlertId(null); setSelectedHistoryAlert(null); }}
          className={`flex flex-col items-center space-y-0.5 text-[10px] font-bold ${
            currentTab === 'status' ? 'text-slate-900' : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <Activity className="w-5 h-5" />
          <span>STATUS</span>
        </button>
      </nav>

      {/* MOBILE CREATE SAFETY PASSPORT MODAL (CHANGE 4 & CHANGE 13) */}
      {isCreatePassportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full overflow-hidden my-4">
            <div className="px-4 py-3 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-black uppercase tracking-wider">
                  {isMobileDesigningZone ? 'Design Temporary Exclusion Zone' : 'Request Safety Passport'}
                </span>
              </div>
              <button 
                onClick={() => {
                  setIsCreatePassportModalOpen(false);
                  setIsMobileDesigningZone(false);
                }} 
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {isMobileDesigningZone ? (
              <div className="p-4 space-y-3 text-xs">
                <div className="bg-slate-900 text-white p-2.5 rounded-lg flex items-center justify-between">
                  <div>
                    <h4 className="text-[11px] font-black uppercase text-amber-400">DRAW EXCLUSION ZONE</h4>
                    <p className="text-[9px] text-slate-300">Tap screen to set boundary polygon points</p>
                  </div>
                  <span className="font-mono text-[10px] text-amber-400 font-bold bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                    Points: {mobileZonePoints.length} (Min 3)
                  </span>
                </div>

                <div className="relative aspect-[4/3] bg-slate-950 rounded-lg overflow-hidden border border-slate-700">
                  <img
                    src="/video_feed"
                    alt="CCTV Frame"
                    className="w-full h-full object-fill pointer-events-none select-none"
                  />
                  <svg
                    ref={mobileSvgRef}
                    viewBox="0 0 640 480"
                    onClick={handleMobileSvgClick}
                    className="absolute inset-0 w-full h-full cursor-crosshair z-10 select-none"
                  >
                    <rect x="1" y="1" width="638" height="478" fill="transparent" stroke="rgba(245, 158, 11, 0.5)" strokeWidth="2" strokeDasharray="6 3" />
                    {mobileZonePoints.length > 1 && (
                      <polygon
                        points={mobileZonePoints.map(p => `${p[0]},${p[1]}`).join(' ')}
                        fill="rgba(245, 158, 11, 0.28)"
                        stroke="#f59e0b"
                        strokeWidth="3"
                      />
                    )}
                    {mobileZonePoints.map((p, idx) => (
                      <g key={idx}>
                        <circle cx={p[0]} cy={p[1]} r="7" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />
                        <text x={p[0] + 9} y={p[1] - 4} fill="#ffffff" fontSize="13" fontWeight="bold">
                          P{idx + 1}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>

                <div className="space-y-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-600 uppercase block mb-0.5">Zone Name:</label>
                    <input
                      type="text"
                      value={mobileZoneName}
                      onChange={(e) => setMobileZoneName(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded font-semibold text-slate-900 text-xs outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] font-bold text-slate-600 uppercase block mb-0.5">Zone Type:</label>
                      <div className="px-2 py-1.5 bg-amber-50 border border-amber-200 text-amber-900 font-bold rounded text-[11px]">
                        🟠 TEMPORARY ZONE
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-600 uppercase block mb-0.5">Duration:</label>
                      <select
                        value={mobileZoneDuration}
                        onChange={(e) => setMobileZoneDuration(Math.min(parseInt(e.target.value), passportFormData.duration_minutes))}
                        className="w-full px-2 py-1.5 bg-slate-50 border border-slate-300 rounded font-semibold text-slate-900 text-xs outline-none"
                      >
                        <option value={5}>5 minutes</option>
                        <option value={10}>10 minutes</option>
                        <option value={15}>15 minutes</option>
                        <option value={30}>30 minutes</option>
                        <option value={passportFormData.duration_minutes}>{passportFormData.duration_minutes} min (Match)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setMobileZonePoints([])}
                    className="px-2.5 py-1.5 bg-slate-100 text-slate-700 rounded font-bold text-xs"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsMobileDesigningZone(false)}
                    className="px-2.5 py-1.5 bg-slate-200 text-slate-700 rounded font-bold text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveMobileTempZone}
                    className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded font-black text-xs shadow-sm"
                  >
                    SAVE TEMPORARY ZONE
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreatePassportMobile} className="p-4 space-y-3 text-xs">
                <div>
                  <label className="text-[10px] font-bold text-slate-700 block mb-1">High-Risk Task:</label>
                  <select
                    value={passportFormData.task_type}
                    onChange={(e) => setPassportFormData({ ...passportFormData, task_type: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-semibold text-slate-900 text-xs"
                  >
                    <option value="Mechanical Lifting">Mechanical Lifting</option>
                    <option value="Working at Heights">Working at Heights</option>
                    <option value="Confined Space Entry">Confined Space Entry</option>
                    <option value="Hot Work / Welding">Hot Work / Welding</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] font-bold text-slate-700 block mb-1">Location:</label>
                    <input
                      type="text"
                      value={passportFormData.location}
                      onChange={(e) => setPassportFormData({ ...passportFormData, location: e.target.value })}
                      className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-700 block mb-1">Passport Duration:</label>
                    <select
                      value={passportFormData.duration_minutes}
                      onChange={(e) => {
                        const d = parseInt(e.target.value) || 15;
                        setPassportFormData({ ...passportFormData, duration_minutes: d });
                        if (mobileZoneDuration > d) setMobileZoneDuration(d);
                      }}
                      className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold text-xs"
                    >
                      <option value={5}>5 minutes</option>
                      <option value={10}>10 minutes</option>
                      <option value={15}>15 minutes</option>
                      <option value={30}>30 minutes</option>
                      <option value={60}>60 minutes</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-700 block mb-1">Linked Camera Node:</label>
                  <select
                    value={passportFormData.camera_id}
                    onChange={(e) => setPassportFormData({ ...passportFormData, camera_id: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold text-xs"
                  >
                    <option value="C-01">Camera C-01 (Demo Work Zone / Laptop Webcam)</option>
                  </select>
                </div>

                {/* TEMPORARY SAFETY ZONE (CHANGE 4 & CHANGE 13) */}
                <div className="pt-2 pb-1 border-t border-slate-200">
                  <div className="text-[10px] font-black uppercase text-slate-800 tracking-wider mb-1.5">
                    TEMPORARY SAFETY ZONE
                  </div>

                  {mobileTempZoneData ? (
                    <div className="p-2.5 bg-amber-50 border border-amber-300 rounded-lg space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1.5 font-bold text-[11px] text-slate-900">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>✓ TEMPORARY ZONE CREATED</span>
                        </div>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-amber-500 text-white uppercase">
                          🟠 Temporary
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-700 font-medium">
                        {mobileTempZoneData.name} • Valid for: {mobileTempZoneData.duration_minutes}:00
                      </div>
                      <div className="flex items-center space-x-2 pt-1 border-t border-amber-200">
                        <button
                          type="button"
                          onClick={() => {
                            setMobileZonePoints(mobileTempZoneData.polygon || []);
                            setIsMobileDesigningZone(true);
                          }}
                          className="px-2 py-0.5 bg-white border border-slate-300 text-slate-700 text-[10px] font-bold rounded"
                        >
                          EDIT ZONE
                        </button>
                        <button
                          type="button"
                          onClick={() => setMobileTempZoneData(null)}
                          className="px-2 py-0.5 bg-white border border-red-200 text-red-600 text-[10px] font-bold rounded"
                        >
                          REMOVE ZONE
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-slate-50 border border-dashed border-slate-300 rounded-lg text-center space-y-1.5">
                      <div className="text-[11px] text-slate-500 font-medium">
                        No temporary zone created yet.
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setMobileZonePoints([[150, 150], [490, 150], [490, 420], [150, 420]]);
                          setIsMobileDesigningZone(true);
                        }}
                        className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold inline-flex items-center space-x-1 shadow-sm"
                      >
                        <ShieldAlert className="w-3.5 h-3.5" />
                        <span>+ DESIGN RESTRICTED ZONE</span>
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-700 block mb-1">Permit Reference:</label>
                  <input
                    type="text"
                    value={passportFormData.permit_reference}
                    onChange={(e) => setPassportFormData({ ...passportFormData, permit_reference: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-semibold text-xs"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreatePassportModalOpen(false)}
                    className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-1.5 bg-slate-900 text-white rounded-lg font-bold shadow-sm disabled:opacity-50"
                  >
                    {submitting ? 'Submitting...' : 'Request Passport'}
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
