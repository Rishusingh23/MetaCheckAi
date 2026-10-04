import React, { useEffect, useState } from 'react';
import { Download, RefreshCw, Filter } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { getReportDownloadUrl, listReports } from '../services/api';
import { ReportItem } from '../types';

export const Reports: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [formatFilter, setFormatFilter] = useState<string>('');
  const [total, setTotal] = useState(0);

  const fetchReports = async () => {
    try {
      setLoading(true);
      const res = await listReports({
        format: formatFilter || undefined,
        limit: 50,
      });
      setReports(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [formatFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">AI-Assisted Legal Metrology Inspection Reports</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Advisory screening dossiers ({total} total) generated for inspection review and verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchReports}
            disabled={loading}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800 px-4 py-3 rounded-xl text-xs">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <Filter className="w-4 h-4 text-metagov-400" />
          <span>Filter Format:</span>
        </div>
        <div className="flex items-center gap-2">
          {['', 'PDF', 'JSON', 'CSV'].map((fmt) => (
            <button
              key={fmt}
              onClick={() => setFormatFilter(fmt)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                formatFilter === fmt
                  ? 'bg-metagov-600 text-white shadow'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {fmt || 'All Formats'}
            </button>
          ))}
        </div>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-3 text-center py-12 text-slate-500 text-xs">
            Loading generated reports...
          </div>
        ) : reports.length > 0 ? (
          reports.map((r) => (
            <Card key={r.id} className="flex flex-col justify-between h-full bg-slate-900/70 border-slate-800 hover:border-slate-700 transition-colors">
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded">
                    {r.format}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {new Date(r.created_at || r.generated_at).toLocaleString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white mb-1 leading-snug">
                  AI-Assisted Inspection Report
                </h3>
                <p className="text-xs text-slate-400 font-mono">
                  Inspection ID: #{r.inspection_id.slice(0, 8)}...
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                <Badge variant="success">{r.status}</Badge>
                <a
                  href={getReportDownloadUrl(r.id)}
                  download
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-metagov-600 hover:bg-metagov-500 text-white text-xs font-semibold transition-colors shadow"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download {r.format}
                </a>
              </div>
            </Card>
          ))
        ) : (
          <div className="col-span-3 text-center py-12 text-slate-500 text-xs bg-slate-900/30 rounded-2xl border border-slate-800/60">
            No generated reports found. Open any Inspection Dossier to generate an advisory PDF, JSON, or CSV report.
          </div>
        )}
      </div>
    </div>
  );
};
