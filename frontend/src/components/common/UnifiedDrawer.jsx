import React from 'react';
import OverlayPortal from './OverlayPortal';
import { useOverlayLock } from './useOverlayLock';

/**
 * UnifiedDrawer: Enterprise standard right-side sliding drawer.
 * Renders via React Portal at document root with a separate full-viewport backdrop,
 * body scroll lock, Escape key dismiss, and responsive width.
 */
export default function UnifiedDrawer({
  isOpen,
  onClose,
  children,
  widthClass = 'w-full sm:w-[85vw] sm:max-w-md lg:w-[42vw] lg:min-w-[440px] lg:max-w-[620px]',
  className = ''
}) {
  useOverlayLock(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <OverlayPortal>
      {/* 1. SEPARATE FULL-VIEWPORT BACKDROP */}
      <div
        className="fixed inset-0 z-[60] bg-slate-950/50 backdrop-blur-[2px] animate-overlay-fade"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 2. RIGHT-SIDE SLIDING DRAWER CONTAINER */}
      <aside
        className={`fixed top-0 right-0 bottom-0 h-full z-[70] bg-white shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden animate-drawer-slide ${widthClass} ${className}`}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </aside>
    </OverlayPortal>
  );
}
