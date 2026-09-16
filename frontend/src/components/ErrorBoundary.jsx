import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ShramRakshak ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-6 font-sans">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl space-y-4 text-center">
            <div className="w-12 h-12 rounded-xl bg-red-500/20 border border-red-500/40 text-red-400 mx-auto flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-tight text-white uppercase">
                ShramRakshak Dispatch
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                A runtime rendering exception occurred.
              </p>
            </div>
            <div className="p-3 bg-black/50 rounded-lg text-left overflow-auto max-h-32 text-[11px] font-mono text-red-300 border border-slate-800">
              {this.state.error?.toString() || 'Unknown runtime error'}
            </div>
            <div className="pt-2 flex flex-col space-y-2">
              <button
                onClick={this.handleReload}
                className="w-full py-2.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-black text-xs rounded-lg transition-colors flex items-center justify-center space-x-2 shadow-lg"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reload Application</span>
              </button>
              <button
                onClick={this.handleReset}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-lg transition-colors"
              >
                Attempt In-Place Recovery
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
