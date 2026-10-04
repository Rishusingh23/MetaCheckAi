import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle, UserCheck } from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, isLoading } = useAuth();

  const fromPath = (location.state as any)?.from?.pathname || '/dashboard';
  const isDemoMode = import.meta.env.VITE_ENABLE_SIH_DEMO === 'true' || import.meta.env.VITE_DEMO_MODE === 'true';

  React.useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(fromPath, { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, fromPath]);


  const [email, setEmail] = useState(isDemoMode ? 'officer@metacheck.gov.in' : '');
  const [password, setPassword] = useState(isDemoMode ? 'Officer@123' : '');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate(fromPath, { replace: true });
    } catch (err: any) {
      const detail =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        'Authentication failed. Please verify credentials.';
      setErrorMsg(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoCredentials = (roleEmail: string, rolePass: string) => {
    setEmail(roleEmail);
    setPassword(rolePass);
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
      <div className="absolute inset-0 gradient-glow opacity-60 pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-metagov-600 to-sky-400 items-center justify-center text-white shadow-xl shadow-metagov-600/30 mb-3">
            <ShieldCheck className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">MetaCheck AI</h1>
          <p className="text-xs text-slate-400 mt-1">
            Department of Consumer Affairs &bull; Legal Metrology Enforcement Portal
          </p>
        </div>

        <Card className="border-slate-800 shadow-2xl">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-white">Officer Authentication</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter official credentials or select a statutory inspection role
            </p>
          </div>

          {errorMsg && (
            <div className="mb-4 p-3 rounded-lg bg-red-950/80 border border-red-800 text-xs text-red-300 flex items-start gap-2 animate-fadeIn">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Officer Email / User ID
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-metagov-500 transition-colors"
                  placeholder="name@gov.in"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-metagov-500 transition-colors"
                  placeholder="Enter your password"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-2"
              isLoading={isSubmitting}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Sign In & Enter
            </Button>
          </form>

          {/* Quick Demo Credentials (Visible ONLY in explicit SIH Demo Mode) */}
          {isDemoMode && (
            <div className="mt-6 pt-4 border-t border-slate-800 space-y-2">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-metagov-400" />
                  SIH Demo Credentials
                </p>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-metagov-950/60 border border-metagov-800 text-metagov-400 font-medium">
                  Demo Evaluation
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setDemoCredentials('admin@metacheck.gov.in', 'Admin@123')}
                  className={`px-2 py-1.5 rounded-lg border text-left text-[11px] transition-colors ${
                    email === 'admin@metacheck.gov.in'
                      ? 'bg-metagov-950/80 border-metagov-600 text-metagov-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                  }`}
                >
                  <span className="font-semibold block text-slate-200">Admin</span>
                  <span className="text-[9px] text-slate-500">Full System</span>
                </button>

                <button
                  type="button"
                  onClick={() => setDemoCredentials('officer@metacheck.gov.in', 'Officer@123')}
                  className={`px-2 py-1.5 rounded-lg border text-left text-[11px] transition-colors ${
                    email === 'officer@metacheck.gov.in'
                      ? 'bg-metagov-950/80 border-metagov-600 text-metagov-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                  }`}
                >
                  <span className="font-semibold block text-slate-200">Officer</span>
                  <span className="text-[9px] text-slate-500">Enforcement</span>
                </button>

                <button
                  type="button"
                  onClick={() => setDemoCredentials('viewer@metacheck.gov.in', 'Viewer@123')}
                  className={`px-2 py-1.5 rounded-lg border text-left text-[11px] transition-colors ${
                    email === 'viewer@metacheck.gov.in'
                      ? 'bg-metagov-950/80 border-metagov-600 text-metagov-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                  }`}
                >
                  <span className="font-semibold block text-slate-200">Auditor</span>
                  <span className="text-[9px] text-slate-500">Read-only</span>
                </button>
              </div>
            </div>
          )}
        </Card>

        <p className="text-center text-[11px] text-slate-500 mt-6">
          Legal Metrology (Packaged Commodities) Rules, 2011 &bull; MetaCheck AI v1.0.0
        </p>
      </div>
    </div>
  );
};
