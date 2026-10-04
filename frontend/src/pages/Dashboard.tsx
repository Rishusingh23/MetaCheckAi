import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScanLine,
  AlertTriangle,
  FileCheck2,
  Scale,
  ArrowRight,
  Filter,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { StatCard } from '../components/common/StatCard';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { getDashboardSummary } from '../services/api';
import { DashboardSummary } from '../types';

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  MAJOR: '#f97316',
  MINOR: '#f59e0b',
  ADVISORY: '#3b82f6',
};

const CATEGORY_COLORS = [
  '#0ea5e9',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
  '#64748b',
];

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async (cat?: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await getDashboardSummary(cat ? { category: cat } : undefined);
      setData(res);
    } catch (err: any) {
      console.error('Failed to load dashboard summary:', err);
      setError(err?.response?.data?.detail || 'Failed to load operational analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData(selectedCategory);
  }, [selectedCategory]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-metagov-950 via-slate-900 to-slate-900 border border-metagov-800/60 p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant="success">Phase 6: Inspection & Enforcement Live</Badge>
              <span className="text-xs text-slate-400">PostgreSQL Live Aggregations &bull; RBAC Verified</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Legal Metrology Compliance & Inspection Dashboard
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Real-time monitoring of packaged commodity compliance across retail markets, enforcement officer reviews, and statutory advisory reports pursuant to PCR 2011.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchDashboardData(selectedCategory)}
              disabled={loading}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Link to="/scanner">
              <Button variant="primary" size="sm" leftIcon={<ScanLine className="w-4 h-4" />}>
                New Inspection
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 px-4 py-3 rounded-xl text-xs">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <Filter className="w-4 h-4 text-metagov-400" />
          <span>Operational Filters:</span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-1 focus:ring-metagov-500 outline-none"
          >
            <option value="">All Commodity Categories</option>
            {data?.category_distribution.map((c) => (
              <option key={c.category} value={c.category}>
                {c.category} ({c.count})
              </option>
            ))}
          </select>
          {selectedCategory && (
            <button
              onClick={() => setSelectedCategory('')}
              className="text-metagov-400 hover:text-metagov-300 underline text-xs"
            >
              Clear Filter
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Stat Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Inspections"
          value={data?.total_inspections?.toLocaleString() || (loading ? '...' : '0')}
          description={`${data?.inspections_today || 0} recorded today`}
          icon={<FileCheck2 className="w-5 h-5 text-metagov-400" />}
        />
        <StatCard
          label="Compliance Rate"
          value={data ? `${data.compliance_rate}%` : (loading ? '...' : '0%')}
          description="Statutory baseline conformant"
          icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
        />
        <StatCard
          label="Flagged for Review"
          value={data?.flagged_violations?.toLocaleString() || (loading ? '...' : '0')}
          description={`${data?.review_required || 0} inspections pending`}
          icon={<AlertTriangle className="w-5 h-5 text-amber-400" />}
        />
        <StatCard
          label="Officer Confirmed Violations"
          value={data?.officer_confirmed_violations?.toLocaleString() || (loading ? '...' : '0')}
          description={`${data?.dismissed_violations || 0} dismissed`}
          icon={<Scale className="w-5 h-5 text-rose-400" />}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Compliance Trend Chart */}
        <Card
          title="7-Day Inspection Volume"
          subtitle="Screening activity across registered commodities"
          className="lg:col-span-2"
        >
          <div className="h-64 w-full">
            {data?.inspection_trend && data.inspection_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.inspection_trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="total" name="Total Inspections" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="compliant" name="Compliant Screenings" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No trend data available.
              </div>
            )}
          </div>
        </Card>

        {/* Commodity Category Breakdown */}
        <Card
          title="Commodity Distribution"
          subtitle="Breakdown by product category"
        >
          <div className="h-48 w-full flex items-center justify-center">
            {data?.category_distribution && data.category_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.category_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="count"
                    nameKey="category"
                  >
                    {data.category_distribution.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '8px',
                      fontSize: '11px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-slate-500 text-xs">No commodity records yet.</div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-1.5 mt-2 pt-3 border-t border-slate-800 text-[11px]">
            {data?.category_distribution.slice(0, 6).map((item, index) => (
              <div key={item.category} className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: CATEGORY_COLORS[index % CATEGORY_COLORS.length] }}
                />
                <span className="text-slate-300 truncate" title={item.category}>
                  {item.category} ({item.count})
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Secondary Insights Row: Top Violated Rules & Workload */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Violated Rules */}
        <Card
          title="Top Flagged Rules"
          subtitle="PCR 2011 requirements with most potential non-compliances"
        >
          {data?.top_violated_rules && data.top_violated_rules.length > 0 ? (
            <div className="space-y-3">
              {data.top_violated_rules.map((rule) => (
                <div
                  key={rule.rule_code}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/80 text-xs"
                >
                  <div className="space-y-0.5">
                    <span className="font-semibold text-slate-200 font-mono">{rule.rule_code}</span>
                    <p className="text-[11px] text-slate-400">{rule.rule_name}</p>
                  </div>
                  <Badge variant="danger">{rule.count} Flagged</Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center text-slate-500 text-xs">
              No statutory violations flagged in current dataset.
            </div>
          )}
        </Card>

        {/* Violations by Severity */}
        <Card
          title="Findings by Severity Tier"
          subtitle="Statutory risk distribution of automated findings"
        >
          {data?.violations_by_severity && data.violations_by_severity.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 py-2">
              {data.violations_by_severity.map((s) => (
                <div
                  key={s.severity}
                  className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 flex items-center justify-between"
                >
                  <div>
                    <span
                      className="text-xs font-bold uppercase tracking-wider"
                      style={{ color: SEVERITY_COLORS[s.severity] || '#94a3b8' }}
                    >
                      {s.severity}
                    </span>
                    <p className="text-[10px] text-slate-400">Severity Tier</p>
                  </div>
                  <span className="text-xl font-bold text-white font-mono">{s.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center text-slate-500 text-xs">
              No severity distribution data available.
            </div>
          )}
        </Card>
      </div>

      {/* Recent Inspections Table */}
      <Card
        title="Recent Inspection Dossiers"
        subtitle="Live feed of field and portal inspection workflows"
        action={
          <Link to="/history">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
              View Full History
            </Button>
          </Link>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Inspection ID</th>
                <th className="py-3 px-4">Product & Brand</th>
                <th className="py-3 px-4">Assigned Officer</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Enforcement Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {data?.recent_inspections && data.recent_inspections.length > 0 ? (
                data.recent_inspections.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-metagov-400">
                      {item.id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-semibold text-white">{item.product_name}</p>
                      <p className="text-[11px] text-slate-400">{item.brand}</p>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{item.inspector_name}</td>
                    <td className="py-3 px-4 text-slate-400">{item.inspection_date}</td>
                    <td className="py-3 px-4">
                      {item.status === 'OFFICER_REVIEWED' ? (
                        <Badge variant="success">Officer Reviewed</Badge>
                      ) : item.status === 'REVIEW_REQUIRED' || item.violations_count > 0 ? (
                        <Badge variant="warning">Review Required ({item.violations_count})</Badge>
                      ) : (
                        <Badge variant="info">{item.status}</Badge>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link to={`/scan-result?inspection_id=${item.id}`}>
                        <Button variant="outline" size="sm">
                          Open Dossier
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No inspection records found. Create an inspection via Product Scanner.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
