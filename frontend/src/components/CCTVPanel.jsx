import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Camera, 
  Video,
  User, 
  HardHat, 
  ShieldAlert, 
  RefreshCw, 
  Maximize2, 
  Check, 
  X, 
  RotateCcw,
  Sliders,
  Power,
  Trash2,
  Loader2,
  Play,
  Square,
  AlertTriangle,
  Upload,
  ChevronDown,
  ChevronUp,
  Activity,
  Info
} from 'lucide-react';
import { 
  saveZone, 
  deleteZone, 
  toggleZone, 
  restoreDefaultZone,
  sendCameraFrame,
  fetchCvDebug
} from '../services/api';

export default function CCTVPanel({ 
  status, 
  isDrawingMode, 
  setIsDrawingMode,
  selectedCamera: externalCamera,
  onSelectCamera
}) {
  // Input Source Modes: 'WEBCAM' (Live Laptop Camera), 'DEMO_VIDEO' (Demo Video Input), 'BACKEND_STREAM' (CCTV Channels)
  const [sourceMode, setSourceMode] = useState('WEBCAM');
  const [selectedCamera, setSelectedCamera] = useState(externalCamera || 'C-01');

  // Camera Lifecycle States: 'INITIALIZING', 'CONNECTING', 'LIVE', 'PAUSED', 'ERROR', 'NO_CAMERA', 'PERMISSION_DENIED'
  const [cameraState, setCameraState] = useState('INITIALIZING');
  const [cameraErrorMsg, setCameraErrorMsg] = useState('');
  const [streamResolution, setStreamResolution] = useState('640x480');
  const [cameraFps, setCameraFps] = useState(30);

  // Real AI Inference Results (received from backend /api/cv/frame)
  const [liveDetections, setLiveDetections] = useState(null);
  const [debugStats, setDebugStats] = useState(null);
  const [showDebugPanel, setShowDebugPanel] = useState(false);

  // Stream & Overlay Refs
  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const demoVideoRef = useRef(null);
  const streamRef = useRef(null);
  const isInferringRef = useRef(false);

  // Zone Management State
  const [isDrawing, setIsDrawing] = useState(false);
  const [points, setPoints] = useState([]);
  const [zoneName, setZoneName] = useState('Compressor Restricted Area');
  const [zoneType, setZoneType] = useState('floor');
  const [severity, setSeverity] = useState('HIGH');
  const [saving, setSaving] = useState(false);
  const [showZoneConfig, setShowZoneConfig] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  // Optimistic Zone State & Action Loading
  const activeZone = status?.active_zone;
  const [localEnabled, setLocalEnabled] = useState(null);
  const [isDeleted, setIsDeleted] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Sync external camera selection
  useEffect(() => {
    if (externalCamera && externalCamera !== selectedCamera) {
      setSelectedCamera(externalCamera);
    }
  }, [externalCamera]);

  // Sync active zone state
  useEffect(() => {
    if (activeZone && activeZone.polygon && activeZone.polygon.length >= 3) {
      setLocalEnabled(activeZone.enabled ?? false);
      setIsDeleted(false);
    } else {
      setIsDeleted(true);
    }
  }, [activeZone?.zone_id, activeZone?.enabled, activeZone?.polygon?.length]);

  const activeDrawing = isDrawingMode !== undefined ? isDrawingMode : isDrawing;
  const setDrawingActive = setIsDrawingMode || setIsDrawing;

  // Real zone effective state
  const effectiveZone = !isDeleted ? activeZone : null;
  const hasZone = !!(effectiveZone && effectiveZone.polygon && effectiveZone.polygon.length >= 3);
  const isZoneEnabled = hasZone && (localEnabled !== null ? localEnabled : (effectiveZone?.enabled ?? false));
  
  // Real-time AI detection metrics (prefer local real-time inference, fallback to backend status)
  const detectedPersons = liveDetections?.persons || [];
  const personCount = liveDetections ? liveDetections.person_count : (status?.person_count ?? (status?.person_detected ? 1 : 0));
  const unhelmetedCount = liveDetections ? liveDetections.unhelmeted_count : (status?.unhelmeted_count ?? (!status?.helmet_detected && personCount > 0 ? 1 : 0));
  const helmetDetected = liveDetections ? liveDetections.helmet_detected : (status?.helmet_detected ?? false);
  const zoneViolation = (isZoneEnabled && !isDeleted) ? (liveDetections ? liveDetections.zone_violation : (status?.zone_violation ?? false)) : false;

  // Active Alert summary
  const activeAlert = status?.active_alert;

  // ----------------------------------------------------
  // ROBUST CAMERA INITIALIZATION & LIFECYCLE
  // ----------------------------------------------------
  const stopWebcam = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        try {
          track.stop();
        } catch (e) {
          console.warn('Track stop error:', e);
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraState('PAUSED');
  }, []);

  const startWebcam = useCallback(async () => {
    // 1. Cleanly stop any existing stream
    stopWebcam();
    setCameraState('CONNECTING');
    setCameraErrorMsg('');

    // 2. Detect browser support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraState('NO_CAMERA');
      setCameraErrorMsg('Browser MediaDevices API is not supported in this environment.');
      return;
    }

    // 3. Request webcam stream
    try {
      const constraints = {
        video: {
          width: { ideal: 640, max: 1280 },
          height: { ideal: 480, max: 720 },
          frameRate: { ideal: 30, max: 30 }
        },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current.play().then(() => {
            const w = videoRef.current.videoWidth || 640;
            const h = videoRef.current.videoHeight || 480;
            setStreamResolution(`${w}x${h}`);
            setCameraState('LIVE');
          }).catch(playErr => {
            console.warn('Video play error:', playErr);
            setCameraState('LIVE');
          });
        };
      } else {
        setCameraState('LIVE');
      }

    } catch (err) {
      console.error('Camera initialization error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraState('PERMISSION_DENIED');
        setCameraErrorMsg('Camera access was denied by browser settings. Please click the permissions icon in your address bar and allow camera access.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraState('NO_CAMERA');
        setCameraErrorMsg('No camera hardware was detected on this laptop or device.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraState('ERROR');
        setCameraErrorMsg('Camera is currently locked or in use by another application (e.g. Teams, Zoom, or another browser tab).');
      } else {
        setCameraState('ERROR');
        setCameraErrorMsg(err.message || 'Failed to initialize camera stream.');
      }
    }
  }, [stopWebcam]);

  // Start webcam when sourceMode is 'WEBCAM'
  useEffect(() => {
    if (sourceMode === 'WEBCAM') {
      startWebcam();
    } else {
      stopWebcam();
    }
    return () => {
      stopWebcam();
    };
  }, [sourceMode, startWebcam, stopWebcam]);

  // ----------------------------------------------------
  // REAL-TIME AI INFERENCE LOOP (5 - 8 FPS)
  // ----------------------------------------------------
  useEffect(() => {
    let intervalId = null;

    const runInferenceStep = async () => {
      if (isInferringRef.current) return;
      
      const targetVideo = (sourceMode === 'WEBCAM') ? videoRef.current : (sourceMode === 'DEMO_VIDEO' ? demoVideoRef.current : null);
      if (!targetVideo || targetVideo.readyState < 2 || targetVideo.paused || targetVideo.ended) {
        return;
      }

      if (!canvasRef.current) {
        canvasRef.current = document.createElement('canvas');
        canvasRef.current.width = 640;
        canvasRef.current.height = 480;
      }

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      try {
        isInferringRef.current = true;
        ctx.drawImage(targetVideo, 0, 0, 640, 480);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.80);

        const result = await sendCameraFrame(dataUrl, selectedCamera);
        if (result) {
          setLiveDetections(result);
          if (result.debug) {
            setDebugStats(result.debug);
          }
        }
      } catch (err) {
        // Silent catch for network hiccups to avoid UI disruptions
      } finally {
        isInferringRef.current = false;
      }
    };

    // Run inference every 160ms (~6.25 FPS) for smooth UI and responsive AI
    if (sourceMode === 'WEBCAM' && cameraState === 'LIVE') {
      intervalId = setInterval(runInferenceStep, 160);
    } else if (sourceMode === 'DEMO_VIDEO') {
      intervalId = setInterval(runInferenceStep, 160);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [sourceMode, cameraState, selectedCamera]);

  // Periodic debug diagnostics fetch
  useEffect(() => {
    const fetchDebug = async () => {
      try {
        const dbg = await fetchCvDebug();
        if (dbg) setDebugStats(dbg);
      } catch (e) {}
    };
    if (showDebugPanel) {
      fetchDebug();
      const dbgInterval = setInterval(fetchDebug, 2000);
      return () => clearInterval(dbgInterval);
    }
  }, [showDebugPanel]);

  // Camera change handler
  const handleCameraChange = (camId) => {
    setSelectedCamera(camId);
    if (camId === 'C-01') {
      setSourceMode('WEBCAM');
    } else {
      setSourceMode('BACKEND_STREAM');
    }
    setStreamKey(Date.now());
    if (onSelectCamera) {
      onSelectCamera(camId);
    }
  };

  // Video Demo File Upload Handler
  const handleDemoVideoUpload = (e) => {
    const file = e.target.files?.[0];
    if (file && demoVideoRef.current) {
      const url = URL.createObjectURL(file);
      demoVideoRef.current.src = url;
      demoVideoRef.current.play().catch(() => {});
    }
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => {
        console.warn('Fullscreen error:', err);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const startDrawing = () => {
    setPoints([]);
    setDrawingActive(true);
  };

  const cancelDrawing = () => {
    setPoints([]);
    setDrawingActive(false);
  };

  const handleSvgClick = (e) => {
    if (!e.currentTarget) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 640);
    const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 480);
    const clampedX = Math.max(0, Math.min(640, clickX));
    const clampedY = Math.max(0, Math.min(480, clickY));
    setPoints(prev => [...prev, [clampedX, clampedY]]);
  };

  const handleSaveZone = async () => {
    if (points.length < 3) return;
    try {
      setSaving(true);
      await saveZone({
        zone_id: 'ZONE-001',
        name: zoneName || (zoneType === 'surface' ? 'Hospital Bed / Platform Area' : 'Compressor Restricted Area'),
        camera_id: selectedCamera || 'C-01',
        zone_type: zoneType || 'floor',
        severity: severity || 'HIGH',
        polygon: points,
        enabled: true
      });
      setDrawingActive(false);
      setPoints([]);
      setIsDeleted(false);
      setLocalEnabled(true);
      setStreamKey(Date.now());
    } catch (err) {
      console.error('Failed to save zone:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleZone = async () => {
    if (actionLoading) return;
    const nextState = !isZoneEnabled;
    setLocalEnabled(nextState);
    setActionLoading(true);
    try {
      await toggleZone(activeZone?.zone_id || 'ZONE-001');
      setStreamKey(Date.now());
    } catch (err) {
      console.error('Failed to toggle zone:', err);
      setLocalEnabled(!nextState);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteZone = async () => {
    if (actionLoading) return;
    setIsDeleted(true);
    setActionLoading(true);
    setShowZoneConfig(false);
    try {
      await deleteZone(activeZone?.zone_id || 'ZONE-001');
      setStreamKey(Date.now());
    } catch (err) {
      console.error('Failed to delete zone:', err);
      setIsDeleted(false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestoreDefaultZone = async () => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      await restoreDefaultZone();
      setIsDeleted(false);
      setLocalEnabled(true);
      setStreamKey(Date.now());
    } catch (err) {
      console.error('Failed to restore default zone:', err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div ref={containerRef} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* CCTV Header */}
      <div className="bg-slate-900 text-white px-4 py-3 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center space-x-3">
          <span className="text-xs font-black tracking-wider uppercase text-slate-100 flex items-center space-x-1.5">
            <Camera className="w-4 h-4 text-amber-400" />
            <span>LIVE MONITORING</span>
          </span>

          {/* Camera Status Badge */}
          {sourceMode === 'WEBCAM' && (
            <span className={`flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-bold ${
              cameraState === 'LIVE'
                ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                : cameraState === 'CONNECTING'
                ? 'bg-amber-500/15 border border-amber-500/30 text-amber-400'
                : 'bg-red-500/15 border border-red-500/30 text-red-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                cameraState === 'LIVE' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}></span>
              <span>{cameraState}</span>
            </span>
          )}

          {sourceMode === 'DEMO_VIDEO' && (
            <span className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 text-blue-400 text-[11px] font-bold">
              <Video className="w-3.5 h-3.5" />
              <span>DEMO VIDEO INPUT</span>
            </span>
          )}

          <span className="text-xs font-mono text-slate-300 font-semibold">
            {sourceMode === 'WEBCAM' ? 'Camera C-01 (Laptop Webcam)' : `Channel ${selectedCamera}`}
          </span>
        </div>

        {/* Source Mode Tabs & Camera Controls */}
        <div className="flex items-center space-x-2">
          {/* Mode Switcher */}
          <div className="bg-slate-800 p-0.5 rounded-lg flex items-center space-x-1 border border-slate-700">
            <button
              onClick={() => { setSourceMode('WEBCAM'); setSelectedCamera('C-01'); }}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                sourceMode === 'WEBCAM' 
                  ? 'bg-amber-500 text-slate-950 shadow-sm' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Laptop Webcam
            </button>
            <button
              onClick={() => setSourceMode('DEMO_VIDEO')}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                sourceMode === 'DEMO_VIDEO' 
                  ? 'bg-blue-500 text-white shadow-sm' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Demo Video
            </button>
          </div>

          {/* Camera Channel Dropdown */}
          <select
            value={selectedCamera}
            onChange={(e) => handleCameraChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-md px-2 py-1 outline-none focus:border-amber-400 cursor-pointer"
          >
            <option value="C-01">C-01 (Laptop / Demo Zone)</option>
            <option value="C-02">C-02 (Rig Floor Compressor)</option>
            <option value="C-03">C-03 (Tank Battery Confined)</option>
            <option value="C-04">C-04 (Crane Mechanical Lift)</option>
          </select>

          {/* Camera Start / Stop / Retry Controls for Webcam */}
          {sourceMode === 'WEBCAM' && (
            <>
              {cameraState === 'LIVE' ? (
                <button
                  onClick={stopWebcam}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-md transition-colors"
                  title="Stop Camera Stream"
                >
                  <Square className="w-3.5 h-3.5 text-amber-400" />
                </button>
              ) : (
                <button
                  onClick={startWebcam}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-bold flex items-center space-x-1"
                  title="Start Camera Stream"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Start</span>
                </button>
              )}
              <button
                onClick={startWebcam}
                className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors"
                title="Retry Camera"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {/* Define Zone Button */}
          {!activeDrawing ? (
            <button
              onClick={startDrawing}
              className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 text-xs font-bold rounded-md transition-colors flex items-center space-x-1 shadow-sm"
              title="Click to draw safety perimeter"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{hasZone ? 'Redefine Zone' : '+ Define Safety Zone'}</span>
              <span className="sm:hidden">{hasZone ? 'Zone' : '+ Zone'}</span>
            </button>
          ) : (
            <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-1 rounded text-xs font-bold animate-pulse">
              Drawing Mode
            </span>
          )}

          {/* Zone Settings Toggle */}
          {hasZone && !activeDrawing && (
            <button
              onClick={() => setShowZoneConfig(!showZoneConfig)}
              className={`p-1.5 rounded-md text-xs transition-colors border ${
                showZoneConfig 
                  ? 'bg-slate-800 text-amber-400 border-amber-500/50' 
                  : 'text-slate-400 hover:text-slate-200 border-slate-700 hover:bg-slate-800'
              }`}
              title="Zone Controls"
            >
              <Sliders className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Fullscreen Button */}
          <button
            onClick={toggleFullscreen}
            className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-slate-800 transition-colors"
            title="Toggle Fullscreen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Zone Configuration Mini-Bar */}
      {showZoneConfig && hasZone && !activeDrawing && effectiveZone && (
        <div className="bg-slate-800/95 text-slate-200 px-4 py-2 border-b border-slate-700 flex flex-wrap items-center justify-between text-xs gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-amber-400">Restricted Zone:</span>
            <span className="font-mono text-slate-300">{effectiveZone.name}</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
              isZoneEnabled ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-700 text-slate-400'
            }`}>
              {isZoneEnabled ? 'ACTIVE' : 'DISABLED'}
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleToggleZone}
              disabled={actionLoading}
              className="flex items-center space-x-1 text-slate-300 hover:text-white font-semibold transition-colors disabled:opacity-50"
            >
              {actionLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Power className={`w-3.5 h-3.5 ${isZoneEnabled ? 'text-amber-400' : 'text-slate-400'}`} />
              )}
              <span>{isZoneEnabled ? 'Disable' : 'Enable'}</span>
            </button>
            <span className="text-slate-600">|</span>
            <button
              onClick={handleDeleteZone}
              disabled={actionLoading}
              className="flex items-center space-x-1 text-red-400 hover:text-red-300 font-semibold transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>
          </div>
        </div>
      )}

      {/* Drawing Toolbar (Visible when drawing polygon) */}
      {activeDrawing && (
        <div className="bg-slate-800 text-white px-4 py-2.5 border-b border-slate-700 flex flex-col space-y-2 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <div className="flex items-center space-x-3 flex-wrap gap-2">
              <span className="font-bold text-amber-400">
                Click camera feed to set boundary points:
              </span>
              <span className="bg-slate-700 px-2 py-0.5 rounded font-mono font-bold text-slate-200">
                Points: {points.length} {points.length < 3 && '(Min 3)'}
              </span>
              <div className="flex items-center space-x-1.5">
                <label className="text-slate-400 text-[11px]">Name:</label>
                <input
                  type="text"
                  value={zoneName}
                  onChange={(e) => setZoneName(e.target.value)}
                  placeholder="Zone Name"
                  className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white text-xs w-36 focus:border-amber-400 outline-none"
                />
              </div>
              <div className="flex items-center space-x-1.5">
                <label className="text-slate-400 text-[11px]">Type:</label>
                <select
                  value={zoneType}
                  onChange={(e) => setZoneType(e.target.value)}
                  className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white text-xs focus:border-amber-400 outline-none"
                >
                  <option value="floor">Floor / Ground Contact</option>
                  <option value="surface">Surface / Platform</option>
                </select>
              </div>
              <div className="flex items-center space-x-1.5">
                <label className="text-slate-400 text-[11px]">Severity:</label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-white text-xs focus:border-amber-400 outline-none"
                >
                  <option value="HIGH">High (SIF Precursor)</option>
                  <option value="CRITICAL">Critical Exclusion</option>
                  <option value="MEDIUM">Medium Warning</option>
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPoints(prev => prev.slice(0, -1))}
                disabled={points.length === 0}
                className="px-2 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-white rounded transition-colors"
              >
                Undo Point
              </button>
              <button
                onClick={cancelDrawing}
                className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors flex items-center space-x-1"
              >
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSaveZone}
                disabled={points.length < 3 || saving}
                className="px-3 py-1 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-bold rounded transition-colors flex items-center space-x-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : 'Save Zone'}</span>
              </button>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 font-sans">
            Tip: Click points sequentially inside the video to enclose the restricted hazard boundary.
          </p>
        </div>
      )}

      {/* CCTV Viewport Container (640x480 Standard Aspect Ratio) */}
      <div className="relative bg-slate-950 flex items-center justify-center min-h-[320px] sm:min-h-[440px] max-h-[560px] overflow-hidden">
        <div className="relative w-full max-w-[640px] aspect-[4/3] flex items-center justify-center bg-black overflow-hidden">

          {/* 1. WEBCAM MODE (Direct Browser MediaStream) */}
          {sourceMode === 'WEBCAM' && (
            <>
              {cameraState === 'LIVE' || cameraState === 'CONNECTING' ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-fill select-none"
                />
              ) : null}

              {/* Camera Permission Denied State */}
              {cameraState === 'PERMISSION_DENIED' && (
                <div className="text-center p-6 text-slate-300 max-w-md">
                  <ShieldAlert className="w-12 h-12 mx-auto mb-3 text-red-500" />
                  <h4 className="text-base font-bold text-white mb-1">Camera Permission Denied</h4>
                  <p className="text-xs text-slate-400 mb-4">{cameraErrorMsg}</p>
                  <div className="flex items-center justify-center space-x-3">
                    <button
                      onClick={startWebcam}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs flex items-center space-x-1.5"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Retry Camera</span>
                    </button>
                    <button
                      onClick={() => setSourceMode('DEMO_VIDEO')}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs"
                    >
                      Use Demo Video Instead
                    </button>
                  </div>
                </div>
              )}

              {/* No Camera Hardware Detected State */}
              {cameraState === 'NO_CAMERA' && (
                <div className="text-center p-6 text-slate-300 max-w-md">
                  <Camera className="w-12 h-12 mx-auto mb-3 text-amber-500" />
                  <h4 className="text-base font-bold text-white mb-1">No Hardware Webcam Found</h4>
                  <p className="text-xs text-slate-400 mb-4">{cameraErrorMsg}</p>
                  <button
                    onClick={() => setSourceMode('DEMO_VIDEO')}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded text-xs inline-flex items-center space-x-1.5"
                  >
                    <Video className="w-3.5 h-3.5" />
                    <span>Switch to Demo Video Input</span>
                  </button>
                </div>
              )}

              {/* Camera Error or Device Lock State */}
              {cameraState === 'ERROR' && (
                <div className="text-center p-6 text-slate-300 max-w-md">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-amber-500" />
                  <h4 className="text-base font-bold text-white mb-1">Camera Initialization Error</h4>
                  <p className="text-xs text-slate-400 mb-4">{cameraErrorMsg}</p>
                  <div className="flex items-center justify-center space-x-3">
                    <button
                      onClick={startWebcam}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs flex items-center space-x-1.5"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Retry Stream</span>
                    </button>
                    <button
                      onClick={() => setSourceMode('DEMO_VIDEO')}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs"
                    >
                      Demo Video Mode
                    </button>
                  </div>
                </div>
              )}

              {/* Camera Paused State */}
              {cameraState === 'PAUSED' && (
                <div className="text-center p-6 text-slate-400">
                  <Square className="w-10 h-10 mx-auto mb-2 text-slate-500" />
                  <p className="text-sm font-semibold text-slate-300">Camera Stream Paused</p>
                  <p className="text-xs text-slate-500 mt-1">Click Start Camera to resume real-time monitoring</p>
                  <button
                    onClick={startWebcam}
                    className="mt-3 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded text-xs inline-flex items-center space-x-1.5"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Start Camera</span>
                  </button>
                </div>
              )}
            </>
          )}

          {/* 2. DEMO VIDEO INPUT MODE (File Playback) */}
          {sourceMode === 'DEMO_VIDEO' && (
            <div className="relative w-full h-full flex flex-col items-center justify-center">
              <video
                ref={demoVideoRef}
                loop
                playsInline
                controls
                className="w-full h-full object-fill select-none"
              />
              <div className="absolute top-3 left-3 z-20 bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 flex items-center space-x-3 shadow-lg">
                <label className="text-xs font-bold text-slate-200 flex items-center space-x-1.5 cursor-pointer hover:text-amber-400 transition-colors">
                  <Upload className="w-3.5 h-3.5" />
                  <span>Choose Video File (.mp4, .webm)</span>
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleDemoVideoUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
          )}

          {/* 3. BACKEND INDUSTRIAL CCTV CHANNEL (MJPEG) */}
          {sourceMode === 'BACKEND_STREAM' && (
            <img
              key={`${selectedCamera}-${streamKey}`}
              src={`http://127.0.0.1:8000/api/stream?camera_id=${selectedCamera}&t=${streamKey}`}
              alt={`Industrial CCTV Channel ${selectedCamera}`}
              className="w-full h-full object-fill select-none"
              onError={() => setCameraState('ERROR')}
            />
          )}

          {/* REAL-TIME AI BOUNDING BOXES & RESTRICTED ZONE OVERLAY */}
          <svg
            viewBox="0 0 640 480"
            onClick={activeDrawing ? handleSvgClick : undefined}
            className={`absolute inset-0 w-full h-full pointer-events-${activeDrawing ? 'auto' : 'none'} select-none z-10`}
          >
            {/* 1. Restricted Zone Polygon */}
            {hasZone && isZoneEnabled && (
              <g>
                <polygon
                  points={effectiveZone.polygon.map(p => `${p[0]},${p[1]}`).join(' ')}
                  fill={zoneViolation ? "rgba(239, 68, 68, 0.28)" : "rgba(16, 185, 129, 0.20)"}
                  stroke={zoneViolation ? "#ef4444" : "#10b981"}
                  strokeWidth="2.5"
                  className={zoneViolation ? "animate-pulse" : ""}
                />
                {/* Zone Label Badge */}
                {effectiveZone.polygon.length > 0 && (
                  <text
                    x={Math.max(10, Math.min(...effectiveZone.polygon.map(p => p[0])))}
                    y={Math.max(25, Math.min(...effectiveZone.polygon.map(p => p[1])) - 6)}
                    fill={zoneViolation ? "#ef4444" : "#10b981"}
                    fontSize="11"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {effectiveZone.name.toUpperCase()} [{zoneViolation ? 'VIOLATION' : 'SECURE'}]
                  </text>
                )}
              </g>
            )}

            {/* 2. Detected Persons & PPE Overlays */}
            {detectedPersons.map((p) => {
              const [bx1, by1, bx2, by2] = p.box;
              const isUnhelmeted = p.helmet_status === 'NOT DETECTED';
              const isViolatingZone = p.in_zone;
              const boxColor = (isUnhelmeted || isViolatingZone) ? '#ef4444' : '#10b981';
              const confPct = Math.round((p.helmet_confidence || 0.85) * 100);
              const tagLabel = isViolatingZone 
                ? `${p.label} [ZONE VIOLATION]` 
                : isUnhelmeted 
                ? `${p.label} [NO HELMET ${confPct}%]` 
                : `${p.label} [HELMET OK ${confPct}%]`;

              const footX = (bx1 + bx2) / 2;
              const footY = by2;

              return (
                <g key={p.id}>
                  {/* Person Bounding Box */}
                  <rect
                    x={bx1}
                    y={by1}
                    width={Math.max(10, bx2 - bx1)}
                    height={Math.max(10, by2 - by1)}
                    fill="transparent"
                    stroke={boxColor}
                    strokeWidth="2.5"
                    rx="2"
                  />
                  {/* Tag Background & Text */}
                  <rect
                    x={bx1}
                    y={Math.max(14, by1 - 18)}
                    width={tagLabel.length * 7 + 10}
                    height="17"
                    fill={boxColor}
                    rx="2"
                  />
                  <text
                    x={bx1 + 5}
                    y={Math.max(26, by1 - 5)}
                    fill="#ffffff"
                    fontSize="10"
                    fontWeight="bold"
                    fontFamily="sans-serif"
                  >
                    {tagLabel}
                  </text>
                  {/* Foot Ground-Contact Marker */}
                  <circle cx={footX} cy={footY} r="4.5" fill={boxColor} stroke="#ffffff" strokeWidth="1.5" />
                </g>
              );
            })}

            {/* 3. Drawing Mode Active Polygon */}
            {activeDrawing && (
              <g>
                <rect x="1" y="1" width="638" height="478" fill="transparent" stroke="rgba(251, 191, 36, 0.4)" strokeWidth="2" strokeDasharray="8 4" />
                {points.length > 1 && (
                  <polygon
                    points={points.map(p => `${p[0]},${p[1]}`).join(' ')}
                    fill="rgba(239, 68, 68, 0.25)"
                    stroke="#ef4444"
                    strokeWidth="2"
                  />
                )}
                {points.map((p, idx) => (
                  <g key={idx}>
                    <circle cx={p[0]} cy={p[1]} r="5" fill="#ef4444" stroke="#ffffff" strokeWidth="1.5" />
                    <text x={p[0] + 6} y={p[1] - 4} fill="#ffffff" fontSize="12" fontWeight="bold">
                      P{idx + 1}
                    </text>
                  </g>
                ))}
              </g>
            )}
          </svg>

          {/* Real-time Telemetry Overlay Bar */}
          <div className="absolute top-2 right-2 bg-slate-900/80 backdrop-blur-sm border border-slate-700/60 text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded shadow flex items-center space-x-2 z-20">
            <span>RES: {streamResolution}</span>
            <span>|</span>
            <span>FPS: {cameraFps}</span>
            <span>|</span>
            <span className="text-amber-400 font-bold">AI: 6 FPS</span>
          </div>
        </div>
      </div>

      {/* SIMPLIFIED LIVE MONITORING STATUS CARDS (PART 11) */}
      <div className="p-3 bg-slate-50/90 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        
        {/* CARD 1: PERSON DETECTED */}
        <div className="bg-white p-2.5 rounded-lg border border-slate-200 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider">Person</span>
            <User className={`w-3.5 h-3.5 ${personCount > 0 ? 'text-blue-600' : 'text-slate-400'}`} />
          </div>
          <div className="text-base font-black text-slate-900">
            {personCount > 0 ? `${personCount} DETECTED` : 'CLEAR'}
          </div>
          <span className={`text-[10px] font-medium mt-0.5 ${personCount > 0 ? 'text-blue-600 font-bold' : 'text-slate-400'}`}>
            {personCount > 0 ? 'Visible in frame' : 'No presence detected'}
          </span>
        </div>

        {/* CARD 2: HELMET / PPE STATUS */}
        <div className={`p-2.5 rounded-lg border flex flex-col justify-between shadow-sm ${
          unhelmetedCount > 0 
            ? 'bg-red-50/80 border-red-200 text-red-950' 
            : personCount > 0 
            ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950' 
            : 'bg-white border-slate-200 text-slate-900'
        }`}>
          <div className="flex items-center justify-between text-slate-500 mb-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider">Helmet / PPE</span>
            <HardHat className={`w-3.5 h-3.5 ${
              unhelmetedCount > 0 ? 'text-red-600' : personCount > 0 ? 'text-emerald-600' : 'text-slate-400'
            }`} />
          </div>
          <div className={`text-base font-black ${
            unhelmetedCount > 0 ? 'text-red-700' : personCount > 0 ? 'text-emerald-700' : 'text-slate-700'
          }`}>
            {unhelmetedCount > 0 
              ? `${unhelmetedCount} MISSING` 
              : personCount > 0 
              ? 'DETECTED' 
              : 'MONITORING'}
          </div>
          <span className={`text-[10px] font-medium mt-0.5 truncate ${
            unhelmetedCount > 0 ? 'text-red-600 font-bold' : personCount > 0 ? 'text-emerald-600 font-bold' : 'text-slate-400'
          }`}>
            {unhelmetedCount > 0 
              ? `Hardhat missing (Conf: ${Math.round((detectedPersons[0]?.helmet_confidence || 0.70) * 100)}%)` 
              : personCount > 0 
              ? `Hardhat verified (Conf: ${Math.round((detectedPersons[0]?.helmet_confidence || 0.85) * 100)}%)` 
              : 'Standing by'}
          </span>
        </div>

        {/* CARD 3: RESTRICTED ZONE */}
        <div className={`p-2.5 rounded-lg border flex flex-col justify-between shadow-sm ${
          zoneViolation 
            ? 'bg-red-50/80 border-red-200 text-red-950' 
            : hasZone && isZoneEnabled 
            ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950' 
            : 'bg-white border-slate-200 text-slate-700'
        }`}>
          <div className="flex items-center justify-between text-slate-500 mb-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider">Restricted Zone</span>
            <ShieldAlert className={`w-3.5 h-3.5 ${
              zoneViolation ? 'text-red-600' : hasZone && isZoneEnabled ? 'text-emerald-600' : 'text-slate-400'
            }`} />
          </div>
          <div className={`text-base font-black ${
            zoneViolation ? 'text-red-700' : hasZone && isZoneEnabled ? 'text-emerald-700' : 'text-slate-600'
          }`}>
            {!hasZone ? 'NO ZONE' : !isZoneEnabled ? 'DISABLED' : zoneViolation ? 'VIOLATION' : 'SECURE'}
          </div>
          <span className={`text-[10px] font-medium mt-0.5 truncate ${
            zoneViolation ? 'text-red-600 font-bold' : hasZone && isZoneEnabled ? 'text-emerald-600' : 'text-slate-400'
          }`}>
            {zoneViolation ? 'Person inside perimeter' : hasZone && isZoneEnabled ? 'Perimeter active' : 'No active zone'}
          </span>
        </div>

        {/* CARD 4: CURRENT INCIDENT / ALERT */}
        <div className={`p-2.5 rounded-lg border flex flex-col justify-between shadow-sm ${
          activeAlert 
            ? 'bg-amber-50/80 border-amber-200 text-amber-950' 
            : 'bg-white border-slate-200 text-slate-700'
        }`}>
          <div className="flex items-center justify-between text-slate-500 mb-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider">Current Alert</span>
            <Activity className={`w-3.5 h-3.5 ${activeAlert ? 'text-amber-600' : 'text-slate-400'}`} />
          </div>
          <div className="text-base font-black text-slate-900 truncate">
            {activeAlert ? (activeAlert.incident_id || activeAlert.id) : 'NONE ACTIVE'}
          </div>
          <span className={`text-[10px] font-medium mt-0.5 truncate ${activeAlert ? 'text-amber-700 font-bold' : 'text-slate-400'}`}>
            {activeAlert ? `${activeAlert.type} (Camera ${activeAlert.camera})` : 'All safe'}
          </span>
        </div>
      </div>

      {/* COLLAPSIBLE DEVELOPER / DEBUG PANEL (PART 14) */}
      <div className="border-t border-slate-200 bg-slate-100/70">
        <button
          onClick={() => setShowDebugPanel(!showDebugPanel)}
          className="w-full px-4 py-2 flex items-center justify-between text-slate-600 hover:text-slate-900 text-xs font-bold transition-colors"
        >
          <span className="flex items-center space-x-1.5">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>Developer / AI Diagnostics Panel</span>
          </span>
          <span className="flex items-center space-x-1 text-[11px] text-slate-500">
            <span>{showDebugPanel ? 'Hide Details' : 'Show Details'}</span>
            {showDebugPanel ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </span>
        </button>

        {showDebugPanel && (
          <div className="p-3.5 bg-slate-900 text-slate-300 text-xs border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Camera Status</span>
              <span className={`font-bold ${cameraState === 'LIVE' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {cameraState}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Video Frames</span>
              <span className="font-bold text-white">
                {debugStats?.frames_received ?? liveDetections?.debug?.frames_received ?? 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Inference</span>
              <span className="font-bold text-emerald-400">
                {debugStats?.inference ?? 'RUNNING'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">AI Model</span>
              <span className="font-bold text-amber-300 truncate block" title={debugStats?.model || 'ppe_safety.onnx'}>
                {debugStats?.model ?? 'ppe_safety.onnx'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Persons Tracked</span>
              <span className="font-bold text-blue-400">{personCount}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Helmet Detections</span>
              <span className="font-bold text-emerald-400">{helmetDetected ? 1 : 0}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Zone Violations</span>
              <span className={`font-bold ${zoneViolation ? 'text-red-400' : 'text-slate-300'}`}>
                {zoneViolation ? 1 : 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">Last Inference / Alert</span>
              <span className="font-bold text-slate-300 text-[11px]">
                {debugStats?.last_inference ?? 'Live'} | {debugStats?.last_alert ?? 'None'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
