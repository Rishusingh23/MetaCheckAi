import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../common/Button';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-metagov-600 to-sky-400 flex items-center justify-center text-white shadow-xl shadow-metagov-600/30 mb-4 animate-pulse">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <p className="text-sm text-slate-400 font-medium">Verifying Officer Session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && user) {
    const isPermitted = allowedRoles.includes(user.role) || allowedRoles.includes('*');
    if (!isPermitted) {
      return (
        <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-950/80 border border-red-800/80 flex items-center justify-center text-red-400 shadow-xl shadow-red-950/50 mb-4">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Restricted Statutory Access
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-md">
            Your current role (<span className="text-amber-400 font-mono font-semibold">{user.role}</span>) does not have authorization to access this administrative module.
          </p>
          <div className="mt-6 flex items-center gap-3">
            <Link to="/dashboard">
              <Button variant="primary" size="sm">
                Return to Dashboard
              </Button>
            </Link>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};
