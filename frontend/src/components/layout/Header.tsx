import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Menu, Activity, LogOut } from 'lucide-react';
import { checkBackendHealth } from '../../services/api';

import { HealthStatus } from '../../types';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const fetchHealth = async () => {
    setIsChecking(true);
    try {
      const data = await checkBackendHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const getPageTitle = (pathname: string) => {
    switch (pathname) {
      case '/':
      case '/dashboard':
        return 'Executive Compliance Dashboard';
      case '/scanner':
        return 'Product Label Scanner';
      case '/scan-result':
        return 'Inspection Analysis & Findings';
      case '/history':
        return 'Inspection Records & Audit Logs';
      case '/products':
        return 'Packaged Commodity Repository';
      case '/violations':
        return 'Potential Non-Compliance Tracking';
      case '/reports':
        return 'Legal Metrology Audit Reports';
      case '/rules':
        return 'Statutory Rules & Regulations';
      case '/users':
        return 'Inspector & Role Management';
      case '/settings':
        return 'System Configuration';
      case '/login':
        return 'Inspector Authentication';
      default:
        return 'MetaCheck AI Portal';
    }
  };

  const getInitials = (name?: string) => {
    if (!name) return 'LMO';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
          aria-label="Toggle Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h1 className="text-sm sm:text-base font-semibold text-white tracking-tight">
            {getPageTitle(location.pathname)}
          </h1>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Legal Metrology (Packaged Commodities) Rules, 2011 Automated Screening
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Backend API Health Status Chip */}
        <div
          onClick={fetchHealth}
          className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 cursor-pointer hover:border-slate-600 transition-colors text-xs"
          title="Click to refresh backend health check"
        >
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                health?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </span>
          <span className="text-[11px] font-medium text-slate-300 hidden md:inline">
            API: {health?.status === 'healthy' ? 'Connected (v1.0)' : isChecking ? 'Checking...' : 'Degraded'}
          </span>
          <Activity className="w-3.5 h-3.5 text-slate-400" />
        </div>

        {/* Authenticated User Profile */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800 text-xs font-medium text-slate-300">
          <div className="w-7 h-7 rounded-full bg-metagov-950 border border-metagov-700/80 flex items-center justify-center text-metagov-400 font-bold text-[11px]">
            {getInitials(user?.name)}
          </div>
          <div className="hidden sm:block leading-tight text-left">
            <span className="text-white block font-semibold text-xs truncate max-w-[140px]">
              {user?.name || 'Officer'}
            </span>
            <span className="text-[10px] text-metagov-400 font-mono font-semibold">
              {user?.role || 'ENFORCEMENT_OFFICER'}
            </span>
          </div>

          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800/80 transition-colors ml-1"
            aria-label="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
