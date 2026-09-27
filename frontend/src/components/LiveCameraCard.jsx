import React, { useState } from 'react';
import { Video, Maximize2, RefreshCw, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LiveCameraCard({ status, activeCamera = 'C-01', onOpenLiveMonitoring }) {
  const [streamKey, setStreamKey] = useState(Date.now());
  const [streamError, setStreamError] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const personCount = status?.person_count ?? (status?.person_detected ? 1 : 0);
  const unhelmetedCount = status?.unhelmeted_count ?? (!status?.helmet_detected && personCount > 0 ? 1 : 0);
  const zoneViolation = status?.zone_violation ?? false;

  const handleRefresh = (e) => {
    e.stopPropagation();
    setIsRefreshing(true);
    setStreamError(false);
    setStreamKey(Date.now());
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100 flex-wrap gap-2">
        <div className="flex items-center space-x-2 min-w-0">
          <Video className="w-4 h-4 text-slate-700 shrink-0" />
          <h2 className="text-xs font-black tracking-wider text-slate-900 uppercase truncate">
            Live Monitoring • Camera {activeCamera}
          </h2>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-safety-emerald" />
            <span className="tracking-wide">LIVE</span>
          </span>
          <button
            onClick={handleRefresh}
            className="p-1.5 text-slate-400 hover:text-slate-700 active:scale-95 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            title="Refresh stream"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", isRefreshing && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Video Feed Window with Responsive Container */}
      <div className="relative rounded-lg overflow-hidden bg-slate-950 aspect-[4/3] sm:aspect-video lg:aspect-[4/3] w-full max-h-72 border border-slate-300 group flex items-center justify-center">
        {!streamError ? (
          <img
            key={`${activeCamera}-${streamKey}`}
            src={`/video_feed?camera=${activeCamera}&t=${streamKey}`}
            alt={`Live CCTV Stream ${activeCamera}`}
            className="w-full h-full object-contain"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center p-4 text-slate-400 space-y-2">
            <Eye className="w-8 h-8 text-slate-500" />
            <p className="text-xs font-bold text-slate-300">Live AI Feed Connecting</p>
            <button
              onClick={handleRefresh}
              className="text-[11px] font-bold text-amber-400 hover:underline active:scale-95 transition-transform"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Real-time overlay bar at bottom of stream */}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between pointer-events-none flex-wrap gap-1.5">
          <div className="flex items-center flex-wrap gap-1.5">
            <span className="bg-slate-950/85 backdrop-blur-xs text-white px-2 py-0.5 rounded text-[10px] font-mono-timer font-bold border border-white/15 shadow-xs">
              {personCount} {personCount === 1 ? 'Worker' : 'Workers'}
            </span>
            {unhelmetedCount > 0 && (
              <span className="bg-safety-amber text-slate-950 px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tight shadow-xs">
                {unhelmetedCount} No Helmet
              </span>
            )}
            {zoneViolation && (
              <span className="bg-safety-crimson text-white px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider shadow-xs">
                Zone Breach
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-slate-100 flex-wrap gap-2 text-xs">
        <span className="text-[11px] font-mono-timer text-slate-500">
          Edge: ONNX PPE + YOLOv8
        </span>
        {onOpenLiveMonitoring && (
          <button
            onClick={onOpenLiveMonitoring}
            className="text-xs font-black text-slate-900 hover:text-amber-600 active:scale-[0.98] inline-flex items-center space-x-1.5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <span>Full Live View</span>
            <span className="text-amber-500 font-black">→</span>
          </button>
        )}
      </div>
    </div>
  );
}
