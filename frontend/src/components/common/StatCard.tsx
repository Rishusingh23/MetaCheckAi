import React from 'react';

export interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  icon: React.ReactNode;
  description?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  change,
  isPositive,
  icon,
  description,
}) => {
  return (
    <div className="glass-card p-5 relative overflow-hidden group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
          <p className="text-2xl font-bold text-white mt-1.5 tracking-tight">{value}</p>
          {change && (
            <div className="flex items-center gap-1 mt-2">
              <span
                className={`text-xs font-semibold ${
                  isPositive ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {change}
              </span>
              {description && <span className="text-xs text-slate-400">{description}</span>}
            </div>
          )}
        </div>
        <div className="p-2.5 rounded-xl bg-slate-800/80 text-metagov-400 border border-slate-700/60 group-hover:border-metagov-500/40 group-hover:text-metagov-300 transition-all duration-200">
          {icon}
        </div>
      </div>
    </div>
  );
};
