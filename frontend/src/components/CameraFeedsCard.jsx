import React from 'react';
import { Video, ShieldCheck, Wifi, Eye, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function CameraFeedsCard({ status, activeCamera = 'C-01', onSelectCamera }) {
  const cameraActive = status?.camera_active ?? true;

  const cameras = [
    {
      id: 'C-01',
      name: 'CAMERA C-01',
      location: 'Primary Work Zone (Laptop Webcam)',
      resolution: '640×480',
      badge: 'PHYSICAL NODE',
      active: cameraActive,
      streamUrl: '/video_feed?camera=C-01'
    }
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100 flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <Video className="w-4 h-4 text-slate-700" />
          <h3 className="text-xs font-black text-slate-900 uppercase tracking-wider">
            Site Surveillance Node
          </h3>
        </div>
        <span className="text-[11px] font-mono-timer font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
          1/1 Feed Active ({activeCamera})
        </span>
      </div>

      {/* Responsive Grid for Camera Feeds */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-3">
        {cameras.map((cam) => {
          const isSelected = (activeCamera === cam.id);
          return (
            <div
              key={cam.id}
              onClick={() => onSelectCamera && onSelectCamera(cam.id)}
              className={cn(
                "border rounded-xl p-3 transition-all cursor-pointer flex flex-col justify-between active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900",
                isSelected
                  ? "border-slate-900 bg-slate-50/80 shadow-xs ring-1 ring-slate-900/10"
                  : "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300"
              )}
            >
              {/* Snapshot Thumbnail */}
              <div className="w-full aspect-video sm:aspect-[4/3] lg:aspect-video bg-slate-950 rounded-lg border border-slate-300 overflow-hidden relative shrink-0 flex items-center justify-center mb-2.5">
                {cam.active ? (
                  <img
                    src={cam.streamUrl}
                    alt={`${cam.name} Thumbnail`}
                    className="w-full h-full object-cover select-none pointer-events-none"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                ) : (
                  <span className="text-[10px] text-slate-500 font-mono-timer font-bold">OFFLINE</span>
                )}
                
                {/* Static Live Dot (No pulse) */}
                <div className="absolute top-2 left-2 flex items-center space-x-1.5 bg-slate-950/85 backdrop-blur-xs px-2 py-0.5 rounded border border-white/10 shadow-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-safety-emerald" />
                  <span className="text-[9px] font-mono-timer font-bold text-white tracking-wider">LIVE</span>
                </div>

                {/* Selected Indicator */}
                {isSelected && (
                  <div className="absolute top-2 right-2 bg-slate-900 text-white px-2 py-0.5 rounded text-[9px] font-black tracking-wider uppercase flex items-center space-x-1 shadow-xs">
                    <CheckCircle2 className="w-3 h-3 text-safety-emerald" />
                    <span>ACTIVE NODE</span>
                  </div>
                )}
              </div>

              {/* Camera Info */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-900 tracking-tight">
                    {cam.name}
                  </span>
                  <span className="text-[9px] font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 uppercase">
                    {cam.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 truncate font-medium" title={cam.location}>
                  {cam.location}
                </p>
                <div className="flex items-center justify-between pt-1.5 border-t border-slate-100 text-[10px] text-slate-400 font-mono-timer font-bold">
                  <span>{cam.resolution}</span>
                  <span className="text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                    AI Armed
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
