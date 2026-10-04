import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  FileText,
  RefreshCw,
  History,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { listInspections } from '../services/api';

export const InspectionHistory: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [inspections, setInspections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 15;

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const res = await listInspections({
        skip: page * limit,
        limit,
        search: searchTerm || undefined,
        status: statusFilter || undefined,
        overall_result: resultFilter || undefined,
        category: categoryFilter || undefined,
      });
      setInspections(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load inspection history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, statusFilter, resultFilter, categoryFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchHistory();
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-metagov-400" />
            Inspection Records & Audit Logs
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Chronological audit repository of statutory commodity screenings ({total} total records)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHistory}
            disabled={loading}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
          <Link to="/reports">
            <Button variant="primary" size="sm" leftIcon={<FileText className="w-4 h-4" />}>
              Audit Reports
            </Button>
          </Link>
        </div>
      </div>

      <Card className="p-4">
        {/* Search & Filter Bar */}
        <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row items-center justify-between gap-3">
          <div className="relative w-full lg:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by ID, product, brand, GTIN..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-400 focus:outline-none focus:border-metagov-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full lg:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-metagov-500"
            >
              <option value="">All Workflow Statuses</option>
              <option value="CREATED">CREATED</option>
              <option value="PROCESSING">PROCESSING</option>
              <option value="REVIEW_REQUIRED">REVIEW_REQUIRED</option>
              <option value="OFFICER_REVIEWED">OFFICER_REVIEWED</option>
              <option value="COMPLETED">COMPLETED</option>
            </select>

            <select
              value={resultFilter}
              onChange={(e) => {
                setResultFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-metagov-500"
            >
              <option value="">All Compliance Results</option>
              <option value="COMPLIANT">COMPLIANT</option>
              <option value="POTENTIAL_NON_COMPLIANCE">POTENTIAL_NON_COMPLIANCE</option>
              <option value="PENDING_VERIFICATION">PENDING_VERIFICATION</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-700 text-slate-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-metagov-500"
            >
              <option value="">All Categories</option>
              <option value="Edible Oils">Edible Oils</option>
              <option value="Food Grain">Food Grain</option>
              <option value="Beverages">Beverages</option>
              <option value="Confectionery">Confectionery</option>
              <option value="Personal Care">Personal Care</option>
            </select>
          </div>

          <Button type="submit" variant="secondary" size="sm">
            Apply Filters
          </Button>
        </form>
      </Card>

      <Card className="overflow-hidden">
        {/* History Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Audit ID</th>
                <th className="py-3 px-4">Date & Time</th>
                <th className="py-3 px-4">Commodity / Brand</th>
                <th className="py-3 px-4">Source Type</th>
                <th className="py-3 px-4">Workflow Status</th>
                <th className="py-3 px-4">Compliance Verdict</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    <div className="w-6 h-6 border-2 border-metagov-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading inspection audit records...
                  </td>
                </tr>
              ) : inspections.length > 0 ? (
                inspections.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-metagov-400">
                      {item.id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(item.inspection_date || item.created_at).toLocaleString('en-IN', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-semibold text-white">{item.product?.name || 'Packaged Commodity'}</p>
                      <p className="text-[11px] text-slate-400">{item.product?.brand || 'General'}</p>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{item.source_type}</td>
                    <td className="py-3 px-4">
                      {item.status === 'OFFICER_REVIEWED' ? (
                        <Badge variant="success">Officer Reviewed</Badge>
                      ) : item.status === 'REVIEW_REQUIRED' ? (
                        <Badge variant="warning">Review Required</Badge>
                      ) : item.status === 'COMPLETED' ? (
                        <Badge variant="info">Completed</Badge>
                      ) : (
                        <Badge variant="neutral">{item.status}</Badge>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {item.overall_result_placeholder === 'COMPLIANT' ? (
                        <Badge variant="success">Compliant</Badge>
                      ) : item.overall_result_placeholder === 'POTENTIAL_NON_COMPLIANCE' ? (
                        <Badge variant="warning">Non-Compliance</Badge>
                      ) : item.overall_result_placeholder === 'PENDING_VERIFICATION' ? (
                        <Badge variant="neutral">Pending Verification</Badge>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Unassessed</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link to={`/scan-result?inspection_id=${item.id}`}>
                        <Button variant="outline" size="sm" leftIcon={<FileText className="w-3 h-3" />}>
                          Open Dossier
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No inspection records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > 0 && (
          <div className="p-3 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing <strong className="text-white">{page * limit + 1}</strong> to{' '}
              <strong className="text-white">{Math.min((page + 1) * limit, total)}</strong> of{' '}
              <strong className="text-white">{total}</strong> records
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage(page - 1)}
                leftIcon={<ChevronLeft className="w-3.5 h-3.5" />}
              >
                Previous
              </Button>
              <span className="text-slate-300 font-mono text-xs">
                {page + 1} / {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage(page + 1)}
                rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
