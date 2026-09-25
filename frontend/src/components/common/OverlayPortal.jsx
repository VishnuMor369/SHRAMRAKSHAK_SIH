import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

/**
 * OverlayPortal: Mounts overlays directly into document.body.
 * Guarantees that backdrops and drawers escape all ancestor stacking contexts,
 * overflow boundaries, filters, and transforms.
 */
export default function OverlayPortal({ children }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (!mounted || typeof document === 'undefined') {
    return null;
  }

  let portalRoot = document.getElementById('shramrakshak-overlay-root');
  if (!portalRoot) {
    portalRoot = document.createElement('div');
    portalRoot.id = 'shramrakshak-overlay-root';
    document.body.appendChild(portalRoot);
  }

  return createPortal(children, portalRoot);
}
