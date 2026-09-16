import React, { useState, useEffect } from 'react';
import { useRealtimeState } from './services/api';
import Dashboard from './pages/Dashboard';
import Supervisor from './pages/Supervisor';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const stateData = useRealtimeState();
  const [currentRoute, setCurrentRoute] = useState(
    window.location.pathname.startsWith('/supervisor') ? '/supervisor' : '/'
  );

  useEffect(() => {
    const handlePopState = () => {
      setCurrentRoute(
        window.location.pathname.startsWith('/supervisor') ? '/supervisor' : '/'
      );
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (path) => {
    window.history.pushState({}, '', path);
    setCurrentRoute(path);
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <ErrorBoundary>
        {/* Route Switcher */}
        {currentRoute === '/supervisor' ? (
          <div>
            <Supervisor stateData={stateData} />
            {/* Subtle desktop navigation link back to dashboard */}
            <div className="fixed bottom-2 right-2 z-40 hidden md:block">
              <button
                onClick={() => navigateTo('/')}
                className="bg-slate-800/80 hover:bg-slate-900 text-white text-[11px] px-3 py-1.5 rounded-full backdrop-blur-sm border border-slate-700 shadow transition-all"
              >
                ← Back to Main HSE Dashboard
              </button>
            </div>
          </div>
        ) : (
          <div>
            <Dashboard stateData={stateData} />
            {/* Subtle desktop link to preview mobile supervisor view in same window */}
            <div className="fixed bottom-3 right-3 z-30 hidden sm:block">
              <button
                onClick={() => navigateTo('/supervisor')}
                className="bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white text-xs font-bold px-3 py-1.5 rounded-md shadow-md border border-amber-600 transition-all flex items-center space-x-1"
              >
                <span>📱 Preview Supervisor Mobile Route</span>
              </button>
            </div>
          </div>
        )}
      </ErrorBoundary>
    </div>
  );
}
