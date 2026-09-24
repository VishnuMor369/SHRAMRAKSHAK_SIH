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
  Pause,
  Square,
  AlertTriangle,
  Upload,
  ChevronDown,
  ChevronUp,
  Activity,
  Info,
  FlipHorizontal,
  Truck
} from 'lucide-react';
import { 
  saveZone, 
  deleteZone, 
  toggleZone, 
  restoreDefaultZone,
  sendCameraFrame,
  fetchCvDebug,
  resetCvSession
} from '../services/api';

export default function CCTVPanel({ 
  status, 
  isDrawingMode, 
  setIsDrawingMode,
  selectedCamera: externalCamera,
  onSelectCamera,
  onSelectAlert
}) {
  // Input Source Modes: 'WEBCAM' (Live Laptop Camera), 'DEMO_VIDEO' (Demo Video Input), 'BACKEND_STREAM' (CCTV Channels)
  const [sourceMode, setSourceMode] = useState('WEBCAM');
  const [selectedCamera, setSelectedCamera] = useState(externalCamera || 'C-01');

  // Camera Mirroring State: default ON for natural webcam selfie, OFF for demo video
  const [isMirrored, setIsMirrored] = useState(true);

  // Camera Lifecycle States: 'INITIALIZING', 'CONNECTING', 'LIVE', 'PAUSED', 'ERROR', 'NO_CAMERA', 'PERMISSION_DENIED'
  const [cameraState, setCameraState] = useState('INITIALIZING');
  const [cameraErrorMsg, setCameraErrorMsg] = useState('');
  const [streamResolution, setStreamResolution] = useState('640x480');
  const [cameraFps, setCameraFps] = useState(30);

  // Demo Video State
  const [demoVideoName, setDemoVideoName] = useState('');
  const [demoVideoUrl, setDemoVideoUrl] = useState('');
  const [isVideoPaused, setIsVideoPaused] = useState(false);
  const [videoError, setVideoError] = useState('');
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [aiFps, setAiFps] = useState(12);

  // Frame sequence tracking & Dynamic FPS refs
  const frameSeqRef = useRef(0);
  const lastProcessedSeqRef = useRef(0);
  const fpsTimesRef = useRef([]);

  // Time format helper: 00:18 / 01:02
  const formatTime = (secs) => {
    if (isNaN(secs) || secs === null || secs === undefined) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Real AI Inference Results (received from backend /api/cv/frame)
  const [liveDetections, setLiveDetections] = useState(null);
  const [debugStats, setDebugStats] = useState(null);
  const [showDebugPanel, setShowDebugPanel] = useState(false);

  // Reset detection session on frontend and backend (clears stale boxes, tracks, sequence IDs)
  const resetDetectionSession = useCallback(async () => {
    setLiveDetections(null);
    frameSeqRef.current = 0;
    lastProcessedSeqRef.current = 0;
    fpsTimesRef.current = [];
    try {
      await resetCvSession();
    } catch (e) {
      console.warn('Failed to reset CV session on backend:', e);
    }
  }, []);

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

  // Sync mirror state with source mode
  useEffect(() => {
    if (sourceMode === 'WEBCAM') {
      setIsMirrored(true);
    } else {
      setIsMirrored(false);
    }
  }, [sourceMode]);

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
  
  // Demo Video State 1 Guard: When in DEMO_VIDEO mode with no video loaded, strictly clear all detection state
  const isDemoNoVideo = (sourceMode === 'DEMO_VIDEO' && !demoVideoUrl);

  // Real-time AI detection metrics (prefer local real-time inference, fallback to backend status ONLY if not in empty demo video state)
  const detectedPersons = isDemoNoVideo ? [] : (
    (liveDetections?.persons && liveDetections.persons.length > 0)
      ? liveDetections.persons
      : (status?.active_alert?.person_findings && status.active_alert.person_findings.length > 0)
      ? status.active_alert.person_findings.map(pf => ({
          id: pf.track_id,
          label: pf.person_id,
          box: pf.bbox || [0, 0, 0, 0],
          helmet_status: pf.helmet_status,
          vest_status: pf.vest_status,
          gloves_status: pf.glove_status,
          overall_ppe_status: pf.overall_ppe_status,
          violations: pf.violations || [],
          evidence_crop: pf.evidence_crop_base64 || pf.evidence_crop_url,
          in_zone: pf.in_zone
        }))
      : []
  );
  const personCount = isDemoNoVideo ? 0 : (liveDetections ? liveDetections.person_count : (status?.person_count ?? (status?.person_detected ? 1 : 0)));
  const unhelmetedCount = isDemoNoVideo ? 0 : (liveDetections ? liveDetections.unhelmeted_count : (status?.unhelmeted_count ?? (!status?.helmet_detected && personCount > 0 ? 1 : 0)));
  const helmetDetected = isDemoNoVideo ? false : (liveDetections ? liveDetections.helmet_detected : (status?.helmet_detected ?? false));
  const vestDetected = isDemoNoVideo ? false : (liveDetections ? liveDetections.vest_detected : (status?.vest_detected ?? false));
  const unvestedCount = isDemoNoVideo ? 0 : (liveDetections ? liveDetections.unvested_count : (status?.unvested_count ?? 0));
  const glovesDetected = isDemoNoVideo ? false : (liveDetections ? liveDetections.gloves_detected : (status?.gloves_detected ?? false));
  const unglovedCount = isDemoNoVideo ? 0 : (liveDetections ? liveDetections.ungloved_count : (status?.ungloved_count ?? 0));
  const zoneViolation = isDemoNoVideo ? false : ((isZoneEnabled && !isDeleted) ? (liveDetections ? liveDetections.zone_violation : (status?.zone_violation ?? false)) : false);

  // Multi-person tracking counts
  const peopleDetectedCount = isDemoNoVideo ? 0 : Math.max(personCount, detectedPersons.length);
  const peopleWithIssues = isDemoNoVideo ? [] : detectedPersons.filter(p => (p.violations && p.violations.length > 0) || p.overall_ppe_status === 'VIOLATION' || p.in_zone);
  const peopleWithIssuesCount = isDemoNoVideo ? 0 : (peopleWithIssues.length > 0 ? peopleWithIssues.length : (unhelmetedCount > 0 || unvestedCount > 0 || unglovedCount > 0 || zoneViolation ? 1 : 0));
  const totalIssuesCount = isDemoNoVideo ? 0 : (detectedPersons.reduce((acc, p) => acc + (p.violations ? p.violations.length : 0), 0) || (unhelmetedCount + unvestedCount + unglovedCount + (zoneViolation ? 1 : 0)));

  // Detected Vehicles & Proximity Events
  const detectedVehicles = isDemoNoVideo ? [] : (liveDetections?.vehicles || []);
  const proximityEvents = isDemoNoVideo ? [] : (liveDetections?.proximity_events || []);
  const isProximityActive = isDemoNoVideo ? false : ((liveDetections?.proximity_violation ?? false) || (status?.active_alert?.type === 'Person–Vehicle Proximity'));

  // Feature 3: Detected Fires & Active Fire Alert
  const detectedFires = isDemoNoVideo ? [] : (liveDetections?.fires || []);
  const isFireActive = isDemoNoVideo ? false : (
    (liveDetections?.fire_detected ?? false) ||
    (status?.fire_detected ?? false) ||
    (status?.active_alerts?.some(a => a.type?.toLowerCase().includes('fire')) ?? false) ||
    (status?.active_alert?.type?.toLowerCase().includes('fire') ?? false)
  );
  const fireConfidence = isDemoNoVideo ? 0 : (
    liveDetections?.fire_confidence ?? status?.fire_confidence ?? (detectedFires[0]?.confidence ?? 0)
  );

  // Primary detected person for PPE details
  const firstPerson = detectedPersons[0] || null;

  // Active Alert summary
  const activeAlert = isDemoNoVideo ? null : status?.active_alert;
  const activeViolations = isDemoNoVideo ? [] : (liveDetections?.violations || (activeAlert?.violations || []));

  const helmetStatus = personCount === 0 ? 'STANDBY' : (
    unhelmetedCount > 0 || firstPerson?.helmet_status === 'VIOLATION' || firstPerson?.helmet_status === 'NOT DETECTED'
      ? 'VIOLATION'
      : (helmetDetected || firstPerson?.helmet_status === 'OK' || firstPerson?.helmet_status === 'HELMET')
      ? 'OK'
      : 'UNKNOWN'
  );
  const vestStatus = personCount === 0 ? 'STANDBY' : (
    unvestedCount > 0 || firstPerson?.vest_status === 'VIOLATION' || firstPerson?.vest_status === 'NO_VEST'
      ? 'VIOLATION'
      : (vestDetected || firstPerson?.vest_status === 'OK' || firstPerson?.vest_status === 'VEST')
      ? 'OK'
      : 'UNKNOWN'
  );
  const glovesStatus = personCount === 0 ? 'STANDBY' : (
    unglovedCount > 0 || firstPerson?.gloves_status === 'VIOLATION' || firstPerson?.gloves_status === 'NO_GLOVES'
      ? 'VIOLATION'
      : (glovesDetected || firstPerson?.gloves_status === 'OK' || firstPerson?.gloves_status === 'GLOVES')
      ? 'OK'
      : 'UNKNOWN'
  );

  const missingPPEList = [];
  if (personCount > 0) {
    if (helmetStatus === 'VIOLATION') {
      missingPPEList.push('NO HELMET');
    }
    if (vestStatus === 'VIOLATION') {
      missingPPEList.push('NO SAFETY VEST');
    }
    if (glovesStatus === 'VIOLATION') {
      missingPPEList.push('NO GLOVES');
    }
  }

  const displayedViolations = [...missingPPEList];
  if (zoneViolation) {
    displayedViolations.push('RESTRICTED ZONE');
  }
  if (displayedViolations.length === 0 && activeViolations.length > 0) {
    activeViolations.forEach(v => {
      if (!displayedViolations.includes(v) && !v.includes('FALL') && !v.includes('HARNESS')) {
        displayedViolations.push(v);
      }
    });
  }
  const incidentId = activeAlert?.incident_id || activeAlert?.id || 'SR-2026-0045';

  const hasActiveBreach = !isDemoNoVideo && (zoneViolation || isProximityActive || isFireActive || !!activeAlert);
  let breachTitle = 'PERSON IN EXCLUSION ZONE';
  if (isFireActive) breachTitle = 'FIRE DETECTED IN ZONE';
  else if (isProximityActive) breachTitle = 'PERSON–VEHICLE PROXIMITY';
  else if (zoneViolation) breachTitle = 'PERSON IN EXCLUSION ZONE';
  else if (activeAlert?.title) breachTitle = activeAlert.title.toUpperCase();

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
  // REAL-TIME AI INFERENCE LOOP (10 - 12 FPS)
  // ----------------------------------------------------
  useEffect(() => {
    let intervalId = null;

    const runInferenceStep = async () => {
      if (isInferringRef.current) return;
      
      const targetVideo = (sourceMode === 'WEBCAM') ? videoRef.current : (sourceMode === 'DEMO_VIDEO' ? demoVideoRef.current : null);
      if (!targetVideo || targetVideo.readyState < 2 || targetVideo.paused || targetVideo.ended) {
        return;
      }

      // Hard guard against sending inference frames when demo video has no file or is paused
      if (sourceMode === 'DEMO_VIDEO' && (!demoVideoUrl || isVideoPaused)) {
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

        frameSeqRef.current += 1;
        const currentSeq = frameSeqRef.current;

        const result = await sendCameraFrame(dataUrl, selectedCamera, currentSeq);
        if (result) {
          // Frame sequence ordering guard: drop stale responses
          if (result.frame_seq && result.frame_seq < lastProcessedSeqRef.current) {
            return;
          }
          if (result.frame_seq) {
            lastProcessedSeqRef.current = result.frame_seq;
          }

          // Measure real AI inference FPS
          const now = performance.now();
          fpsTimesRef.current.push(now);
          fpsTimesRef.current = fpsTimesRef.current.filter(t => now - t <= 2000);
          if (fpsTimesRef.current.length > 1) {
            const calculatedFps = Math.round(((fpsTimesRef.current.length - 1) / ((now - fpsTimesRef.current[0]) / 1000)));
            setAiFps(calculatedFps);
          }

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

    // Run inference every 95ms (~10.5 - 12 FPS) for ultra-smooth tracking & 2-frame proximity confirmation
    if (sourceMode === 'WEBCAM' && cameraState === 'LIVE') {
      intervalId = setInterval(runInferenceStep, 95);
    } else if (sourceMode === 'DEMO_VIDEO' && demoVideoUrl && !isVideoPaused) {
      intervalId = setInterval(runInferenceStep, 95);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [sourceMode, cameraState, selectedCamera, isVideoPaused, demoVideoUrl]);

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
    resetDetectionSession();
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

  // Demo video cleanup on unmount
  useEffect(() => {
    return () => {
      if (demoVideoUrl) {
        URL.revokeObjectURL(demoVideoUrl);
      }
    };
  }, [demoVideoUrl]);

  // Video Demo File Upload Handler (Robust validation & local object URL)
  const handleDemoVideoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate format
    const validTypes = ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'];
    const hasValidExt = /\.(mp4|webm|ogg|mov)$/i.test(file.name);

    if (!validTypes.includes(file.type) && !hasValidExt) {
      setVideoError(`Unsupported video format: "${file.name}". Please upload a standard MP4, WebM, or MOV video.`);
      return;
    }

    // Reset previous detection tracks on new video upload
    resetDetectionSession();
    setVideoError('');
    setDemoVideoName(file.name);

    if (demoVideoUrl) {
      URL.revokeObjectURL(demoVideoUrl);
    }

    const newUrl = URL.createObjectURL(file);
    setDemoVideoUrl(newUrl);

    if (demoVideoRef.current) {
      demoVideoRef.current.src = newUrl;
      demoVideoRef.current.load();
      demoVideoRef.current.play().then(() => {
        setIsVideoPaused(false);
      }).catch(playErr => {
        console.warn('Demo video playback note:', playErr);
        setIsVideoPaused(true);
      });
    }
  };

  // Dedicated Toggle Play / Pause for Demo Video
  const togglePlayPause = () => {
    if (!demoVideoRef.current) return;
    if (demoVideoRef.current.paused) {
      demoVideoRef.current.play().then(() => {
        setIsVideoPaused(false);
      }).catch(err => {
        console.warn('Video play error:', err);
      });
    } else {
      demoVideoRef.current.pause();
      setIsVideoPaused(true);
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
    // Invert X when mirrored so backend receives natural unmirrored frame coordinates
    const backendX = isMirrored ? (640 - clampedX) : clampedX;
    setPoints(prev => [...prev, [backendX, clampedY]]);
  };

  const handleSaveZone = async () => {
    if (points.length < 3) return;
    try {
      setSaving(true);
      await saveZone({
        zone_id: 'ZONE-001',
        name: zoneName || (zoneType === 'surface' ? 'Work Platform Area' : 'Compressor Restricted Area'),
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
              onClick={() => {
                if (sourceMode !== 'WEBCAM') {
                  resetDetectionSession();
                  setSourceMode('WEBCAM');
                  setSelectedCamera('C-01');
                }
              }}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                sourceMode === 'WEBCAM' 
                  ? 'bg-amber-500 text-slate-950 shadow-sm' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Laptop Webcam
            </button>
            <button
              onClick={() => {
                if (sourceMode !== 'DEMO_VIDEO') {
                  resetDetectionSession();
                  setSourceMode('DEMO_VIDEO');
                }
              }}
              className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                sourceMode === 'DEMO_VIDEO' 
                  ? 'bg-blue-500 text-white shadow-sm' 
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Demo Video
            </button>
          </div>

          {/* Camera Channel Indicator — Single Physical Node */}
          <div className="bg-slate-800/90 border border-slate-700/90 text-slate-200 text-xs font-bold rounded-md px-2.5 py-1 flex items-center space-x-1.5 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-amber-400">CAMERA C-01</span>
            <span className="text-slate-400 text-[11px] hidden sm:inline">(Laptop Webcam)</span>
          </div>

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
              {/* Mirror Feed Toggle Button */}
              <button
                onClick={() => setIsMirrored(prev => !prev)}
                className={`px-2 py-1 rounded text-xs font-bold flex items-center space-x-1 border transition-colors ${
                  isMirrored 
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 hover:bg-amber-500/30' 
                    : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                }`}
                title="Toggle natural mirror orientation"
              >
                <FlipHorizontal className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Mirror: {isMirrored ? 'ON' : 'OFF'}</span>
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

      {/* CCTV Two-Column Monitoring Layout: 4:3 Webcam (Left) + Live Incident Monitoring (Right) */}
      <div className="p-3 bg-slate-950 grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch border-b border-slate-800">
        
        {/* LEFT COLUMN: Actual Live Webcam Feed (Preserving 4:3 Aspect Ratio) */}
        <div className="lg:col-span-7 xl:col-span-8 flex flex-col items-center justify-center">
          <div className="relative w-full aspect-[4/3] max-w-[640px] flex items-center justify-center bg-black rounded-lg overflow-hidden border border-slate-800 shadow-2xl">

            {/* 1. WEBCAM MODE (Direct Browser MediaStream) */}
            {sourceMode === 'WEBCAM' && (
              <>
                {(cameraState === 'LIVE' || cameraState === 'CONNECTING') && (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    style={{ transform: isMirrored ? 'scaleX(-1)' : 'none' }}
                    className="w-full h-full object-contain select-none"
                  />
                )}

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
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs"
                    >
                      Switch to Demo Video Mode
                    </button>
                  </div>
                )}

                {/* Camera Locked / Error State */}
                {cameraState === 'ERROR' && (
                  <div className="text-center p-6 text-slate-300 max-w-md">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-amber-400" />
                    <h4 className="text-base font-bold text-white mb-1">Camera Feed Connecting or Standby</h4>
                    <p className="text-xs text-slate-400 mb-4">
                      {cameraErrorMsg || 'Ensure camera permissions or use Demo Mode fallback.'}
                    </p>
                    <div className="flex items-center justify-center space-x-3">
                      <button
                        onClick={startWebcam}
                        className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded text-xs inline-flex items-center space-x-1"
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
              <div className="relative w-full h-full flex flex-col items-center justify-center bg-black">
                <video
                  ref={demoVideoRef}
                  loop
                  playsInline
                  onPlay={() => setIsVideoPaused(false)}
                  onPause={() => setIsVideoPaused(true)}
                  onTimeUpdate={(e) => {
                    setVideoCurrentTime(e.target.currentTime);
                    if (e.target.duration) setVideoDuration(e.target.duration);
                  }}
                  onLoadedMetadata={(e) => {
                    setVideoDuration(e.target.duration || 0);
                  }}
                  onError={() => setVideoError("Could not load or play this video. Please select a valid MP4 or WebM video file.")}
                  onEnded={() => setIsVideoPaused(true)}
                  style={{ transform: isMirrored ? 'scaleX(-1)' : 'none' }}
                  className="w-full h-full object-contain select-none"
                />

                {/* Subtle Non-overlapping Paused Badge */}
                {demoVideoUrl && isVideoPaused && (
                  <div className="absolute top-2 left-2 z-20 bg-amber-500/90 text-slate-950 font-black text-[10px] px-2 py-0.5 rounded shadow flex items-center space-x-1 pointer-events-none">
                    <Pause className="w-3 h-3 fill-current" />
                    <span>VIDEO: PAUSED</span>
                  </div>
                )}

                {/* Empty Video Upload Placeholder */}
                {!demoVideoUrl && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-auto bg-slate-950/80">
                    <Video className="w-12 h-12 mx-auto mb-2 text-blue-400 opacity-80" />
                    <h4 className="text-sm font-bold text-white mb-1">No CCTV Demo Video Loaded</h4>
                    <p className="text-xs text-slate-400 mb-3 max-w-xs">
                      Upload a local CCTV demo video file (.mp4, .webm) to test Person–Vehicle proximity and PPE monitoring.
                    </p>
                    <label className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-bold rounded-lg text-xs cursor-pointer inline-flex items-center space-x-1.5 shadow-md transition-colors">
                      <Upload className="w-3.5 h-3.5" />
                      <span>Select Local Video File</span>
                      <input
                        type="file"
                        accept="video/mp4,video/webm,video/ogg,video/quicktime,.mp4,.webm,.mov"
                        onChange={handleDemoVideoUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                )}

                {/* Error Banner */}
                {videoError && (
                  <div className="absolute bottom-3 left-3 right-3 z-30 bg-red-950/90 border border-red-500 text-red-200 text-xs p-2 rounded-lg flex items-center justify-between shadow-lg">
                    <span>{videoError}</span>
                    <button onClick={() => setVideoError('')} className="text-red-400 font-bold ml-2">✕</button>
                  </div>
                )}
              </div>
            )}

            {/* REAL-TIME AI BOUNDING BOXES & RESTRICTED ZONE OVERLAY (4:3 ViewBox) */}
            <svg
              viewBox="0 0 640 480"
              preserveAspectRatio="xMidYMid meet"
              onClick={activeDrawing ? handleSvgClick : undefined}
              className={`absolute inset-0 w-full h-full pointer-events-${activeDrawing ? 'auto' : 'none'} select-none z-10`}
            >
              {/* 1. Restricted Zone Polygon */}
              {hasZone && isZoneEnabled && (
                <g>
                  <polygon
                    points={effectiveZone.polygon.map(pt => {
                      const px = isMirrored ? (640 - pt[0]) : pt[0];
                      return `${px},${pt[1]}`;
                    }).join(' ')}
                    fill={zoneViolation ? "rgba(239, 68, 68, 0.28)" : "rgba(16, 185, 129, 0.20)"}
                    stroke={zoneViolation ? "#ef4444" : "#10b981"}
                    strokeWidth="2.5"
                    className={zoneViolation ? "animate-pulse" : ""}
                  />
                  {/* Zone Label Badge */}
                  {effectiveZone.polygon.length > 0 && (
                    <text
                      x={isMirrored 
                        ? Math.max(10, 640 - Math.max(...effectiveZone.polygon.map(p => p[0])))
                        : Math.max(10, Math.min(...effectiveZone.polygon.map(p => p[0])))}
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
                const renderBx1 = isMirrored ? (640 - bx2) : bx1;
                const renderBx2 = isMirrored ? (640 - bx1) : bx2;
                const boxWidth = Math.max(10, renderBx2 - renderBx1);
                const boxHeight = Math.max(10, by2 - by1);

                const isUnhelmeted = p.helmet_status === 'VIOLATION' || p.helmet_status === 'NOT DETECTED';
                const isUnvested = p.vest_status === 'VIOLATION' || p.vest_status === 'NO_VEST';
                const isUngloved = p.gloves_status === 'VIOLATION' || p.gloves_status === 'NO_GLOVES';
                const isViolatingZone = p.in_zone;

                const pViols = [];
                if (isUnhelmeted) pViols.push('NO HELMET');
                if (isUnvested) pViols.push('NO VEST');
                if (isUngloved) pViols.push('NO GLOVES');
                if (isViolatingZone) pViols.push('ZONE');
                if (Array.isArray(p.violations)) {
                  p.violations.forEach(v => {
                    const norm = v === 'NO SAFETY VEST' ? 'NO VEST' : v === 'RESTRICTED ZONE' ? 'ZONE' : v;
                    if (!pViols.includes(norm)) pViols.push(norm);
                  });
                }

                const hasViolation = pViols.length > 0 || p.overall_ppe_status === 'VIOLATION';
                const isOk = !hasViolation && (p.overall_ppe_status === 'OK' || (p.helmet_status === 'OK' && p.vest_status === 'OK'));
                const isUnknown = !hasViolation && !isOk;

                const boxColor = hasViolation ? '#ef4444' : isUnknown ? '#f59e0b' : '#10b981';

                // Compact two-line label — Always show actual violations first!
                let line2 = 'PPE OK';
                if (pViols.length > 0) {
                  line2 = pViols.join(' • ');
                } else if (isUnknown) {
                  line2 = 'PPE UNCONFIRMED';
                }

                const tagWidth = Math.max(92, Math.min(180, line2.length * 6.5 + 14));
                const tagY = Math.max(26, by1 - 24);
                const footX = isMirrored ? (640 - (bx1 + bx2) / 2) : ((bx1 + bx2) / 2);
                const footY = by2;

                return (
                  <g key={p.id}>
                    {/* Person Bounding Box */}
                    <rect
                      x={renderBx1}
                      y={by1}
                      width={boxWidth}
                      height={boxHeight}
                      fill="transparent"
                      stroke={boxColor}
                      strokeWidth="2.5"
                      rx="3"
                    />
                    {/* Compact Tag Background & Text */}
                    <rect
                      x={renderBx1}
                      y={tagY}
                      width={tagWidth}
                      height="22"
                      fill={boxColor}
                      rx="3"
                    />
                    <text
                      x={renderBx1 + 5}
                      y={tagY + 9}
                      fill={isUnknown ? '#0f172a' : '#ffffff'}
                      fontSize="8.5"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      {p.label}
                    </text>
                    <text
                      x={renderBx1 + 5}
                      y={tagY + 18}
                      fill={isUnknown ? '#0f172a' : '#ffffff'}
                      fontSize="8"
                      fontWeight="bold"
                      fontFamily="sans-serif"
                    >
                      {line2}
                    </text>
                    {/* Foot Ground-Contact Marker */}
                    <circle cx={footX} cy={footY} r="4" fill={boxColor} stroke="#ffffff" strokeWidth="1.5" />

                    {/* SEPARATE SMALL HAND / GLOVE BOUNDING BOXES */}
                    {p.gloves_status !== 'UNKNOWN' && p.hands && p.hands.map((h, hIdx) => {
                      const [hx1, hy1, hx2, hy2] = h.box;
                      const renderHx1 = isMirrored ? (640 - hx2) : hx1;
                      const renderHx2 = isMirrored ? (640 - hx1) : hx2;
                      const hWidth = Math.max(8, renderHx2 - renderHx1);
                      const hHeight = Math.max(8, hy2 - hy1);
                      const isHandViolation = h.type === 'NO_GLOVES';
                      const handColor = isHandViolation ? '#ef4444' : '#10b981';
                      const hTagY = Math.max(14, hy1 - 14);
                      const cleanLabel = (h.label || '').replace(/\s+\d+%/g, '');
                      const hTagText = cleanLabel || (isHandViolation ? `HAND ${p.id} — NO GLOVES` : `HAND ${p.id} — GLOVES`);
                      const hTagWidth = Math.max(75, hTagText.length * 5.8 + 10);

                      return (
                        <g key={`hand-${p.id}-${hIdx}`}>
                          <rect
                            x={renderHx1}
                            y={hy1}
                            width={hWidth}
                            height={hHeight}
                            fill="transparent"
                            stroke={handColor}
                            strokeWidth="2"
                            rx="2"
                          />
                          <rect
                            x={renderHx1}
                            y={hTagY}
                            width={hTagWidth}
                            height="13"
                            fill={handColor}
                            rx="2"
                          />
                          <text
                            x={renderHx1 + 4}
                            y={hTagY + 9.5}
                            fill="#ffffff"
                            fontSize="7.5"
                            fontWeight="bold"
                            fontFamily="monospace"
                          >
                            {hTagText}
                          </text>
                        </g>
                      );
                    })}
                  </g>
                );
              })}

              {/* 3. Detected Vehicles & Proximity Perimeter Overlay */}
              {detectedVehicles.map((v) => {
                const [vx1, vy1, vx2, vy2] = v.box || [0, 0, 0, 0];
                const renderVx1 = isMirrored ? (640 - vx2) : vx1;
                const renderVx2 = isMirrored ? (640 - vx1) : vx2;
                const vWidth = Math.max(10, renderVx2 - renderVx1);
                const vHeight = Math.max(10, vy2 - vy1);

                // Proximity zone perimeter
                const [zx1, zy1, zx2, zy2] = v.proximity_zone || [vx1, vy1, vx2, vy2];
                const renderZx1 = isMirrored ? (640 - zx2) : zx1;
                const renderZx2 = isMirrored ? (640 - zx1) : zx2;
                const zWidth = Math.max(10, renderZx2 - renderZx1);
                const zHeight = Math.max(10, zy2 - zy1);

                const activeEv = proximityEvents.find(pe => pe.vehicle_track_id === v.id || pe.vehicle_id === v.label);
                const hasProximity = !!activeEv;
                const vColor = hasProximity ? '#ef4444' : '#f59e0b';
                const vTagY = Math.max(20, vy1 - 18);
                const vLabelText = `${v.label} [${(v.class_name || 'Vehicle').toUpperCase()}]`;
                const vTagWidth = Math.max(85, vLabelText.length * 6.5 + 12);

                const zTagText = hasProximity 
                  ? `⚠ ${activeEv.person_id} ↔ ${v.label} — PROXIMITY CONFIRMED`
                  : `${v.label} PROXIMITY ZONE (MONITORING ACTIVE)`;
                const zTagWidth = Math.max(120, zTagText.length * 6.2 + 16);

                return (
                  <g key={`veh-${v.id}`}>
                    {/* Proximity Zone Perimeter */}
                    <rect
                      x={renderZx1}
                      y={zy1}
                      width={zWidth}
                      height={zHeight}
                      fill={hasProximity ? 'rgba(239, 68, 68, 0.22)' : 'rgba(245, 158, 11, 0.06)'}
                      stroke={hasProximity ? '#ef4444' : '#f59e0b'}
                      strokeWidth={hasProximity ? '2.5' : '1.8'}
                      strokeDasharray={hasProximity ? 'none' : '6 4'}
                      rx="4"
                      className={hasProximity ? 'animate-pulse' : ''}
                    />
                    {/* Zone Badge Tag */}
                    <rect
                      x={renderZx1 + 4}
                      y={zy1 + 4}
                      width={zTagWidth}
                      height="16"
                      fill={hasProximity ? '#ef4444' : '#f59e0b'}
                      rx="2"
                    />
                    <text
                      x={renderZx1 + 9}
                      y={zy1 + 15}
                      fill={hasProximity ? '#ffffff' : '#0f172a'}
                      fontSize="8.5"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {zTagText}
                    </text>

                    {/* Vehicle Bounding Box */}
                    <rect
                      x={renderVx1}
                      y={vy1}
                      width={vWidth}
                      height={vHeight}
                      fill="transparent"
                      stroke={vColor}
                      strokeWidth="2.5"
                      rx="3"
                    />

                    {/* Vehicle Tag */}
                    <rect
                      x={renderVx1}
                      y={vTagY}
                      width={vTagWidth}
                      height="16"
                      fill={vColor}
                      rx="2"
                    />
                    <text
                      x={renderVx1 + 5}
                      y={vTagY + 11.5}
                      fill={hasProximity ? '#ffffff' : '#0f172a'}
                      fontSize="9"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      {vLabelText}
                    </text>
                  </g>
                );
              })}

              {/* 4. Active Proximity Warning Conflict Lines */}
              {proximityEvents.map((pe, pIdx) => {
                const [px1, py1, px2, py2] = pe.person_box || [0, 0, 0, 0];
                const [vx1, vy1, vx2, vy2] = pe.vehicle_box || [0, 0, 0, 0];
                const pCenterX = isMirrored ? (640 - (px1 + px2) / 2) : ((px1 + px2) / 2);
                const pCenterY = (py1 + py2) / 2;
                const vCenterX = isMirrored ? (640 - (vx1 + vx2) / 2) : ((vx1 + vx2) / 2);
                const vCenterY = (vy1 + vy2) / 2;

                const midX = (pCenterX + vCenterX) / 2;
                const midY = (pCenterY + vCenterY) / 2;

                return (
                  <g key={`prox-${pIdx}`}>
                    <line
                      x1={pCenterX}
                      y1={pCenterY}
                      x2={vCenterX}
                      y2={vCenterY}
                      stroke="#ef4444"
                      strokeWidth="2.5"
                      strokeDasharray="5 3"
                      className="animate-pulse"
                    />
                    <rect
                      x={midX - 70}
                      y={midY - 10}
                      width="140"
                      height="20"
                      fill="#ef4444"
                      rx="3"
                    />
                    <text
                      x={midX}
                      y={midY + 3.5}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="8.5"
                      fontWeight="black"
                      fontFamily="monospace"
                    >
                      {pe.person_id} ↔ {pe.vehicle_id} PROXIMITY
                    </text>
                  </g>
                );
              })}

              {/* 4b. Detected Fire Bounding Boxes & Warning HUD (Feature 3) */}
              {detectedFires.map((f, fIdx) => {
                const [fx1, fy1, fx2, fy2] = f.box || [0, 0, 0, 0];
                const renderFx1 = isMirrored ? (640 - fx2) : fx1;
                const renderFx2 = isMirrored ? (640 - fx1) : fx2;
                const fWidth = Math.max(12, renderFx2 - renderFx1);
                const fHeight = Math.max(12, fy2 - fy1);
                const fConf = f.confidence ? Math.round(f.confidence * 100) : null;
                const fLabel = fConf ? `🔥 FIRE DETECTED (${fConf}%)` : `🔥 FIRE DETECTED`;
                const fTagWidth = Math.max(90, fLabel.length * 6.5 + 14);
                const fTagY = Math.max(18, fy1 - 18);

                return (
                  <g key={`fire-${fIdx}`}>
                    {/* Distinctive semi-transparent orange fill and vibrant pulsating border */}
                    <rect
                      x={renderFx1}
                      y={fy1}
                      width={fWidth}
                      height={fHeight}
                      fill="rgba(249, 115, 22, 0.22)"
                      stroke="#ea580c"
                      strokeWidth="2.8"
                      rx="3"
                      className="animate-pulse"
                    />
                    {/* Orange badge */}
                    <rect
                      x={renderFx1}
                      y={fTagY}
                      width={fTagWidth}
                      height="18"
                      fill="#ea580c"
                      rx="3"
                    />
                    <text
                      x={renderFx1 + 6}
                      y={fTagY + 13}
                      fill="#ffffff"
                      fontSize="9"
                      fontFamily="sans-serif"
                      fontWeight="bold"
                    >
                      {fLabel}
                    </text>
                  </g>
                );
              })}

              {/* 5. Drawing Mode Active Polygon */}
              {activeDrawing && (
                <g>
                  <rect x="1" y="1" width="638" height="478" fill="transparent" stroke="rgba(251, 191, 36, 0.4)" strokeWidth="2" strokeDasharray="8 4" />
                  {points.length > 1 && (
                    <polygon
                      points={points.map(pt => {
                        const px = isMirrored ? (640 - pt[0]) : pt[0];
                        return `${px},${pt[1]}`;
                      }).join(' ')}
                      fill="rgba(239, 68, 68, 0.25)"
                      stroke="#ef4444"
                      strokeWidth="2"
                    />
                  )}
                  {points.map((pt, idx) => {
                    const px = isMirrored ? (640 - pt[0]) : pt[0];
                    return (
                      <g key={idx}>
                        <circle cx={px} cy={pt[1]} r="5" fill="#ef4444" stroke="#ffffff" strokeWidth="1.5" />
                        <text x={px + 6} y={pt[1] - 4} fill="#ffffff" fontSize="12" fontWeight="bold">
                          P{idx + 1}
                        </text>
                      </g>
                    );
                  })}
                </g>
              )}
            </svg>

            {/* Minimal CCTV HUD Overlay: Top-Left Hero Status */}
            <div className="absolute top-2 left-2 z-20 flex items-center space-x-2 pointer-events-auto">
              {hasActiveBreach ? (
                <div className="bg-red-950/90 border border-red-500/80 backdrop-blur-sm text-white px-2.5 py-1 rounded shadow-lg flex items-center space-x-2 animate-pulse">
                  <span className="text-red-400 font-black text-[11px] tracking-wider">
                    🚨 SIF POTENTIAL • {breachTitle}
                  </span>
                  {activeAlert && onSelectAlert && (
                    <button
                      onClick={() => onSelectAlert(activeAlert)}
                      className="px-2 py-0.5 bg-red-600 hover:bg-red-500 text-white font-black text-[10px] rounded transition-all shadow"
                    >
                      VIEW ALERT
                    </button>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900/85 border border-slate-700/60 backdrop-blur-sm text-slate-200 px-2.5 py-1 rounded shadow flex items-center space-x-2 text-[10px] font-mono">
                  <span className="font-bold text-slate-300">
                    CAMERA {selectedCamera === 'C-01' ? '03 • LIFTING ZONE' : `${selectedCamera} • ZONE 01`}
                  </span>
                  <span className="text-slate-500">|</span>
                  <span className="text-emerald-400 font-bold flex items-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping inline-block" />
                    <span>MONITORING • ZONE STATUS SAFE</span>
                  </span>
                </div>
              )}
            </div>

            {/* Real-time Telemetry Overlay Bar */}
            <div className="absolute top-2 right-2 bg-slate-900/85 backdrop-blur-sm border border-slate-700/60 text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded shadow flex items-center space-x-2 z-20">
              <span>RES: 640×480 (4:3)</span>
              <span>|</span>
              {sourceMode === 'DEMO_VIDEO' && isVideoPaused ? (
                <span className="text-amber-400 font-bold bg-amber-500/10 px-1 rounded">AI MONITORING: PAUSED</span>
              ) : (
                <>
                  <span>FPS: {cameraFps}</span>
                  <span>|</span>
                  <span className="text-emerald-400 font-bold">AI: {aiFps || 11} FPS</span>
                </>
              )}
              <span>|</span>
              <span className={isMirrored ? "text-cyan-400 font-bold" : "text-slate-400"}>
                MIRROR: {isMirrored ? "ON" : "OFF"}
              </span>
            </div>
          </div>

          {/* DEDICATED NON-OVERLAPPING BOTTOM CONTROL BAR FOR DEMO VIDEO */}
          {sourceMode === 'DEMO_VIDEO' && (
            <div className="w-full max-w-[640px] mt-2.5 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2.5 shadow-md">
              {/* Left: Upload / Change File & Filename */}
              <div className="flex items-center space-x-2 min-w-0">
                <label className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-slate-200 hover:text-white rounded text-xs font-bold flex items-center space-x-1.5 cursor-pointer border border-slate-700 transition-colors shrink-0 shadow-sm">
                  <Upload className="w-3.5 h-3.5 text-amber-400" />
                  <span>{demoVideoName ? 'Change Video' : 'Upload Video'}</span>
                  <input
                    type="file"
                    accept="video/mp4,video/webm,video/ogg,video/quicktime,.mp4,.webm,.mov"
                    onChange={handleDemoVideoUpload}
                    className="hidden"
                  />
                </label>
                {demoVideoName ? (
                  <span className="text-xs font-mono text-amber-300 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20 truncate max-w-[170px]" title={demoVideoName}>
                    {demoVideoName}
                  </span>
                ) : (
                  <span className="text-xs text-slate-500 italic">No video selected</span>
                )}
              </div>

              {/* Right: Video Timestamp & Dedicated Pause/Resume Button */}
              <div className="flex items-center space-x-2.5 shrink-0">
                <div className="text-xs font-mono text-slate-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800 flex items-center space-x-1.5">
                  <Activity className="w-3 h-3 text-blue-400" />
                  <span>
                    {formatTime(videoCurrentTime)} / {formatTime(videoDuration)}
                  </span>
                </div>

                <button
                  onClick={togglePlayPause}
                  disabled={!demoVideoUrl}
                  className={`px-3 py-1.5 rounded-md text-xs font-black flex items-center space-x-1.5 transition-all shadow-sm ${
                    !demoVideoUrl
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                      : isVideoPaused
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/30'
                      : 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                  }`}
                  title={isVideoPaused ? "Resume Video Playback" : "Pause Video Playback"}
                >
                  {isVideoPaused ? (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>RESUME</span>
                    </>
                  ) : (
                    <>
                      <Pause className="w-3.5 h-3.5 fill-current" />
                      <span>PAUSE</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: LIVE INCIDENT MONITORING PANEL (Single Source of Live Status) */}
        <div className="lg:col-span-5 xl:col-span-4 w-full bg-slate-900 border border-slate-800 rounded-lg p-3.5 space-y-3 text-white shadow-lg flex flex-col justify-between">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-amber-400">
                  Live Incident Monitoring
                </h3>
                <div className="flex items-center space-x-2 text-[11px] font-mono mt-0.5">
                  <span className="text-slate-300">People Detected: <strong className="text-white">{peopleDetectedCount}</strong></span>
                  <span className="text-slate-600">•</span>
                  <span className={peopleWithIssuesCount > 0 ? "text-red-400 font-bold" : "text-emerald-400 font-bold"}>
                    People With Issues: {peopleWithIssuesCount}
                  </span>
                </div>
              </div>
              {sourceMode === 'DEMO_VIDEO' ? (
                !demoVideoUrl ? (
                  <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                    <span>STANDBY</span>
                  </span>
                ) : isVideoPaused ? (
                  <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>PAUSED</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/40">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                    <span>VIDEO MONITORING</span>
                  </span>
                )
              ) : (
                <span className="flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>LIVE</span>
                </span>
              )}
            </div>

            {/* MULTI-PERSON TRACKING STATUS CARDS */}
            <div className="space-y-2 max-h-[290px] overflow-y-auto pr-1">
              {detectedPersons.length === 0 ? (
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-center text-slate-400 text-xs">
                  <User className="w-5 h-5 mx-auto mb-1 text-slate-500" />
                  <span>No workers detected in active area</span>
                </div>
              ) : (
                detectedPersons.map((p, pIdx) => {
                  const pViols = Array.isArray(p.violations) ? [...p.violations] : [];
                  if ((p.helmet_status === 'VIOLATION' || p.helmet_status === 'NOT DETECTED') && !pViols.includes('NO HELMET')) pViols.push('NO HELMET');
                  if ((p.vest_status === 'VIOLATION' || p.vest_status === 'NO_VEST') && !pViols.includes('NO SAFETY VEST') && !pViols.includes('NO VEST')) pViols.push('NO SAFETY VEST');
                  if ((p.gloves_status === 'VIOLATION' || p.gloves_status === 'NO_GLOVES') && !pViols.includes('NO GLOVES')) pViols.push('NO GLOVES');
                  if (p.in_zone && !pViols.includes('RESTRICTED ZONE')) pViols.push('RESTRICTED ZONE');

                  const isViolation = p.overall_ppe_status === 'VIOLATION' || pViols.length > 0;
                  const isOk = !isViolation && (p.overall_ppe_status === 'OK' || (p.helmet_status === 'OK' && p.vest_status === 'OK'));
                  const isUnknown = !isViolation && !isOk;
                  const label = p.label || `Person #${p.id || pIdx + 1}`;

                  return (
                    <div 
                      key={p.id || pIdx}
                      className={`p-2.5 rounded-lg border transition-all ${
                        isViolation 
                          ? 'bg-red-950/40 border-red-500/50' 
                          : isOk 
                          ? 'bg-slate-950/60 border-emerald-500/30' 
                          : 'bg-slate-950/60 border-amber-500/25'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {p.evidence_crop ? (
                            <img 
                              src={p.evidence_crop} 
                              alt={label}
                              className="w-9 h-9 rounded object-cover border border-slate-700 shrink-0" 
                            />
                          ) : (
                            <div className="w-9 h-9 rounded bg-slate-800 flex items-center justify-center text-slate-400 border border-slate-700 shrink-0">
                              <User className="w-4 h-4" />
                            </div>
                          )}
                          <div>
                            <div className="text-xs font-black font-mono text-white flex items-center space-x-1.5">
                              <span>{label}</span>
                              {p.in_zone && (
                                <span className="text-[9px] font-bold text-red-400 bg-red-500/20 px-1 rounded border border-red-500/30">
                                  ZONE
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] font-bold mt-0.5">
                              {isViolation ? (
                                <span className="text-red-400 uppercase tracking-wide">
                                  {pViols.length > 0 ? pViols.join(' • ') : 'PPE VIOLATION'}
                                </span>
                              ) : isOk ? (
                                <span className="text-emerald-400 uppercase tracking-wide">
                                  PPE OK
                                </span>
                              ) : (
                                <span className="text-amber-400 uppercase tracking-wide">
                                  MONITORING — PPE UNCONFIRMED
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Overall Badge */}
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase ${
                          isViolation ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse' :
                          isOk ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' :
                          'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        }`}>
                          {isViolation ? 'VIOLATION' : isOk ? 'OK' : 'UNCONFIRMED'}
                        </span>
                      </div>

                      {/* Micro PPE Checklist Chips */}
                      <div className="grid grid-cols-3 gap-1.5 mt-2 pt-1.5 border-t border-slate-800/80 text-[10px] font-mono text-center">
                        <span className={`px-1 py-0.5 rounded border ${
                          p.helmet_status === 'OK' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' :
                          p.helmet_status === 'VIOLATION' ? 'bg-red-500/20 text-red-300 border-red-500/40' :
                          'bg-slate-900 text-amber-400/80 border-slate-800'
                        }`}>
                          H: {p.helmet_status || 'UNKNOWN'}
                        </span>
                        <span className={`px-1 py-0.5 rounded border ${
                          p.vest_status === 'OK' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' :
                          p.vest_status === 'VIOLATION' ? 'bg-red-500/20 text-red-300 border-red-500/40' :
                          'bg-slate-900 text-amber-400/80 border-slate-800'
                        }`}>
                          V: {p.vest_status || 'UNKNOWN'}
                        </span>
                        <span className={`px-1 py-0.5 rounded border ${
                          p.gloves_status === 'OK' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' :
                          p.gloves_status === 'VIOLATION' ? 'bg-red-500/20 text-red-300 border-red-500/40' :
                          'bg-slate-900 text-amber-400/80 border-slate-800'
                        }`}>
                          G: {p.gloves_status || 'UNKNOWN'}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* VEHICLES DETECTED SECTION */}
            {detectedVehicles.length > 0 && (
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-1.5 text-sky-400 font-bold">
                    <Truck className="w-3.5 h-3.5" />
                    <span>Vehicles in Frame ({detectedVehicles.length})</span>
                  </div>
                  {isProximityActive ? (
                    <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-red-600 text-white animate-pulse">
                      PROXIMITY RISK
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                      SECURE DISTANCE
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {detectedVehicles.map(v => (
                    <span key={v.id} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 flex items-center space-x-1">
                      <span>{v.label}</span>
                      <span className="text-slate-400">({v.class_name})</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Perimeter Zone Indicator */}
            <div className="flex items-center justify-between py-1.5 px-2.5 rounded bg-slate-950/60 border border-slate-800/80">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-semibold text-slate-300">Restricted Zone</span>
              </div>
              <span className={`text-[10px] font-black px-2 py-0.5 rounded flex items-center space-x-1 ${
                zoneViolation ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse' :
                hasZone && isZoneEnabled ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' :
                'bg-slate-800 text-slate-400 border border-slate-700'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${zoneViolation ? 'bg-red-400 animate-ping' : hasZone && isZoneEnabled ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                <span>{!hasZone ? 'NO ZONE' : !isZoneEnabled ? 'DISABLED' : zoneViolation ? 'VIOLATION' : 'CLEAR'}</span>
              </span>
            </div>

            {/* FIRE Monitoring Status Indicator (Feature 3) */}
            <div className="flex items-center justify-between py-1.5 px-2.5 rounded bg-slate-950/60 border border-slate-800/80">
              <div className="flex items-center space-x-2">
                <span className="text-sm leading-none">🔥</span>
                <span className="text-xs font-semibold text-slate-300">Fire Detection</span>
              </div>
              <span className={`text-[10px] font-black px-2 py-0.5 rounded flex items-center space-x-1 ${
                isFireActive 
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 animate-pulse' 
                  : 'bg-slate-800 text-slate-400 border border-slate-700'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isFireActive ? 'bg-orange-400 animate-ping' : 'bg-slate-500'}`} />
                <span>{isFireActive ? '🟠 FIRE DETECTED' : '● NO FIRE DETECTED'}</span>
              </span>
            </div>
          </div>

          {/* CURRENT EVENT Section */}
          <div className="pt-2.5 border-t border-slate-800">
            <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1.5">
              CURRENT EVENT
            </div>

            {/* High-Priority Proximity Event Highlight Banner */}
            {isProximityActive && (
              <div className="mb-2 p-2.5 rounded-lg bg-red-950/80 border-2 border-red-500 text-red-100 shadow-md space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black text-white bg-red-600 px-1.5 py-0.5 rounded animate-pulse">
                    🔴 HIGH PRIORITY
                  </span>
                  <span className="text-[9px] font-mono text-red-300">PROXIMITY CONFIRMED</span>
                </div>
                <div className="text-xs font-black text-white">
                  PERSON–VEHICLE PROXIMITY ALERT
                </div>
                <div className="text-[11px] text-red-200">
                  {proximityEvents[0] 
                    ? `${proximityEvents[0].person_id} ↔ ${proximityEvents[0].vehicle_id} (${proximityEvents[0].vehicle_type})` 
                    : 'Personnel sustained in vehicle proximity perimeter'}
                </div>
              </div>
            )}

            {/* Confirmed Fire Event Highlight Banner (Feature 3) */}
            {isFireActive && (
              <div className="mb-2 p-2.5 rounded-lg bg-orange-950/80 border-2 border-orange-500 text-orange-100 shadow-md space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black text-white bg-orange-600 px-1.5 py-0.5 rounded animate-pulse">
                    🟠 FIRE DETECTED
                  </span>
                  <span className="text-[9px] font-mono text-orange-300">
                    Camera: C-01
                  </span>
                </div>
                <div className="text-xs font-black text-white">
                  FIRE DETECTION CONFIRMED
                </div>
                <div className="text-[11px] text-orange-200 flex items-center justify-between">
                  <span>Source: {sourceMode === 'DEMO_VIDEO' ? 'Demo Video' : 'Webcam'}</span>
                  {fireConfidence > 0 && (
                    <span className="font-mono text-orange-300 font-bold">{Math.round(fireConfidence * 100)}% confidence</span>
                  )}
                </div>
              </div>
            )}

            {isDemoNoVideo ? (
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-400 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-slate-500" />
                <div>
                  <div className="text-xs font-bold text-slate-300">WAITING FOR DEMO VIDEO</div>
                  <div className="text-[10px] text-slate-500">No active monitoring event — select a video file</div>
                </div>
              </div>
            ) : (peopleWithIssuesCount > 0) ? (
              <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-500/60 text-red-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-red-400">
                    [{incidentId}]
                  </span>
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-500/30 text-red-300 border border-red-500/40">
                    ACTIVE EVENT
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-xs font-black text-red-100">
                  <span>{totalIssuesCount} Issue{totalIssuesCount > 1 ? 's' : ''}</span>
                  <span className="text-red-400">•</span>
                  <span>{peopleWithIssuesCount} People Affected</span>
                </div>
                <button
                  onClick={() => onSelectAlert?.(activeAlert || { id: incidentId, incident_id: incidentId, type: 'CCTV Safety Violation', title: displayedViolations.join(' + '), severity: 'HIGH' })}
                  className="w-full py-1.5 bg-red-600 hover:bg-red-500 active:bg-red-700 text-white font-black rounded text-[11px] uppercase tracking-wider transition-colors shadow-sm flex items-center justify-center space-x-1.5"
                >
                  <span>VIEW EVENT</span>
                </button>
              </div>
            ) : (detectedPersons.length > 0 && detectedPersons.some(p => p.overall_ppe_status === 'UNKNOWN')) ? (
              <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-500/30 text-amber-300 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <div>
                  <div className="text-xs font-bold text-amber-200">PPE MONITORING ACTIVE</div>
                  <div className="text-[10px] text-amber-400/80">Confirming worker PPE status — not yet fully verified</div>
                </div>
              </div>
            ) : (detectedPersons.length > 0 && detectedPersons.every(p => p.overall_ppe_status === 'OK')) ? (
              <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <div>
                  <div className="text-xs font-bold text-emerald-200">ALL WORKERS COMPLIANT</div>
                  <div className="text-[10px] text-emerald-400/80">All detected workers have verified PPE compliance</div>
                </div>
              </div>
            ) : !isProximityActive && !isFireActive ? (
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-400 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <div>
                  <div className="text-xs font-bold text-emerald-400">NO ACTIVE INCIDENT</div>
                  <div className="text-[10px] text-slate-500">All workers and zone parameters compliant</div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
