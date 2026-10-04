import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ScanLine,
  FileSearch,
  History,
  Boxes,
  AlertTriangle,
  FileBarChart2,
  Scale,
  Users,
  Settings as SettingsIcon,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const userRole = user?.role || 'ENFORCEMENT_OFFICER';

  const allSections = [
    {
      title: 'Inspection Core',
      items: [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, roles: ['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER'] },
        { name: 'Product Scanner', path: '/scanner', icon: ScanLine, roles: ['ADMIN', 'ENFORCEMENT_OFFICER'] },
        { name: 'Scan Results', path: '/scan-result', icon: FileSearch, roles: ['ADMIN', 'ENFORCEMENT_OFFICER'] },
      ],
    },
    {
      title: 'Records & Compliance',
      items: [
        { name: 'Inspection History', path: '/history', icon: History, roles: ['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER'] },
        { name: 'Product Repository', path: '/products', icon: Boxes, roles: ['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER'] },
        { name: 'Violations Log', path: '/violations', icon: AlertTriangle, roles: ['ADMIN', 'ENFORCEMENT_OFFICER'] },
        { name: 'Audit Reports', path: '/reports', icon: FileBarChart2, roles: ['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER'] },
      ],
    },
    {
      title: 'Administration',
      items: [
        { name: 'Rule Management', path: '/rules', icon: Scale, roles: ['ADMIN'] },
        { name: 'User Management', path: '/users', icon: Users, roles: ['ADMIN'] },
        { name: 'System Settings', path: '/settings', icon: SettingsIcon, roles: ['ADMIN'] },
      ],
    },
  ];

  // Filter sections by role
  const visibleSections = allSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.roles.includes(userRole) || item.roles.includes('*')),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col transition-transform duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Logo & Title */}
        <div className="h-16 px-5 flex items-center gap-3 border-b border-slate-800 bg-slate-900/50">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-metagov-600 to-sky-400 flex items-center justify-center text-white shadow-md shadow-metagov-600/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              MetaCheck <span className="text-metagov-400 text-xs px-1.5 py-0.5 rounded bg-metagov-950/80 border border-metagov-800 font-semibold">AI</span>
            </span>
            <p className="text-[10px] text-slate-400 font-medium">Legal Metrology Compliance</p>
          </div>
        </div>

        {/* Navigation links */}
        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
          {visibleSections.map((section) => (
            <div key={section.title}>
              <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {section.title}
              </p>
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => {
                        if (window.innerWidth < 1024) onClose();
                      }}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-metagov-600/20 text-metagov-300 border border-metagov-500/30 font-semibold shadow-inner'
                            : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="w-4 h-4" />
                        <span>{item.name}</span>
                      </div>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Legal Disclaimer Box in Sidebar */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <div className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300 flex items-center gap-1">
              <Scale className="w-3.5 h-3.5 text-amber-400" />
              Statutory Notice
            </p>
            <p className="text-[10px] leading-relaxed text-slate-400">
              AI-assisted screening tool. Final compliance requires verified inspection.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
