import React from 'react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const Settings: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">System Settings & Configuration</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Platform parameters, API integration settings, and compliance thresholds
        </p>
      </div>

      <div className="space-y-4">
        <Card title="Backend API & Health Connection" subtitle="Connection parameters to FastAPI service">
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div>
                <p className="font-semibold text-white">API Base Endpoint</p>
                <p className="text-slate-400 font-mono text-[11px]">http://localhost:8000</p>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div>
                <p className="font-semibold text-white">Database Cluster</p>
                <p className="text-slate-400 font-mono text-[11px]">PostgreSQL 16 (metacheck_db)</p>
              </div>
              <Badge variant="info">SQLAlchemy 2.0 / Alembic</Badge>
            </div>
          </div>
        </Card>

        <Card title="AI Screening Sensitivity Thresholds" subtitle="Confidence thresholds for advisory flagging">
          <div className="space-y-4 text-xs">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>OCR Text Recognition Minimum Confidence</span>
                <span className="font-mono text-metagov-400">85%</span>
              </div>
              <input type="range" min="50" max="100" defaultValue="85" className="w-full accent-metagov-500" disabled />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Mandatory Rule Strictness</span>
                <span className="font-mono text-amber-400">High (Statutory)</span>
              </div>
              <input type="range" min="1" max="3" defaultValue="3" className="w-full accent-amber-500" disabled />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
