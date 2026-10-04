import React from 'react';
import { ShieldAlert, Scale } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950/60 py-4 px-6 text-xs text-slate-400">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-metagov-400 shrink-0" />
          <span>
            <strong>MetaCheck AI</strong> &mdash; AI-Powered Legal Metrology Compliance Inspection Platform
          </span>
        </div>

        <div className="flex items-center gap-2 text-slate-400 text-center md:text-right">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 inline" />
          <span className="text-[11px]">
            AI-assisted screening tool. All findings represent advisory screening indications requiring manual verification by authorized Legal Metrology officers.
          </span>
        </div>
      </div>
    </footer>
  );
};
