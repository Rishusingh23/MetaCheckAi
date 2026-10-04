import React, { useEffect, useState } from 'react';
import {
  Search,
  Barcode,
  Boxes,
  ShieldCheck,
  X,
  ChevronLeft,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { getProductDossier, listProducts } from '../services/api';
import { ProductDossier, ProductRepositoryItem } from '../types';

export const ProductRepository: React.FC = () => {
  const [products, setProducts] = useState<ProductRepositoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 10;

  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Selected product dossier modal
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [dossier, setDossier] = useState<ProductDossier | null>(null);
  const [isLoadingDossier, setIsLoadingDossier] = useState(false);
  const [activeDossierTab, setActiveDossierTab] = useState<'overview' | 'inspections' | 'violations' | 'reports' | 'audit'>('overview');

  const fetchProducts = async () => {
    setIsLoading(true);
    try {
      const data = await listProducts({
        skip: page * limit,
        limit,
        search: search || undefined,
        category: category || undefined,
      });
      setProducts(data.items);
      setTotalCount(data.total);
    } catch (err) {
      console.error('Failed to load products:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [page, category]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchProducts();
  };

  const handleOpenDossier = async (productId: string) => {
    setSelectedProductId(productId);
    setIsLoadingDossier(true);
    setActiveDossierTab('overview');
    try {
      const data = await getProductDossier(productId);
      setDossier(data);
    } catch (err) {
      console.error('Failed to fetch product dossier:', err);
    } finally {
      setIsLoadingDossier(false);
    }
  };

  const totalPages = Math.ceil(totalCount / limit) || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <Boxes className="w-5 h-5 text-metagov-400" />
            Packaged Commodity Repository
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Searchable statutory commodity database with multi-inspection dossiers & compliance histories
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="p-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-96">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by GTIN/barcode, name, brand, manufacturer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-400 focus:outline-none focus:border-metagov-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-48">
              <Filter className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <select
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setPage(0);
                }}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-metagov-500"
              >
                <option value="">All Categories</option>
                <option value="Edible Oils">Edible Oils</option>
                <option value="Food Grain">Food Grain & Cereals</option>
                <option value="Beverages">Beverages & Juices</option>
                <option value="Confectionery">Confectionery & Bakery</option>
                <option value="Personal Care">Personal Care & Cosmetics</option>
                <option value="Electronics">Electronics & Hardware</option>
                <option value="Packaged Commodity">General Packaged Goods</option>
              </select>
            </div>

            <Button type="submit" variant="secondary" size="sm">
              Search
            </Button>
          </div>
        </form>
      </Card>

      {/* Products Table */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs">
            <div className="w-6 h-6 border-2 border-metagov-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Querying statutory commodity repository...
          </div>
        ) : products.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Boxes className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-300">No packaged commodities found</p>
            <p className="text-xs text-slate-500 mt-1">Try refining search query or category filter</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">GTIN / Barcode</th>
                  <th className="py-3 px-4">Commodity Name</th>
                  <th className="py-3 px-4">Brand</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Manufacturer</th>
                  <th className="py-3 px-4 text-center">Audits</th>
                  <th className="py-3 px-4">Latest Compliance Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {products.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-metagov-400 flex items-center gap-1.5">
                      <Barcode className="w-3.5 h-3.5" />
                      {p.barcode_gtin || 'UNSPECIFIED'}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      {p.name}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{p.brand}</td>
                    <td className="py-3 px-4 text-slate-400">{p.category}</td>
                    <td className="py-3 px-4 text-slate-400 truncate max-w-[150px]">
                      {p.manufacturer || '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-center text-slate-200">
                      {p.inspection_count}
                    </td>
                    <td className="py-3 px-4">
                      {p.latest_compliance_result === 'COMPLIANT' ? (
                        <Badge variant="success">Compliant</Badge>
                      ) : p.latest_compliance_result === 'POTENTIAL_NON_COMPLIANCE' ? (
                        <Badge variant="warning">Non-Compliance</Badge>
                      ) : p.latest_compliance_result === 'PENDING_VERIFICATION' ? (
                        <Badge variant="neutral">Pending Review</Badge>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Not Screened</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleOpenDossier(p.id)}
                        className="text-[11px] py-1 px-2.5"
                      >
                        View Dossier
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {totalCount > 0 && (
          <div className="p-3 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
            <span>
              Showing <strong className="text-white">{page * limit + 1}</strong> to{' '}
              <strong className="text-white">{Math.min((page + 1) * limit, totalCount)}</strong> of{' '}
              <strong className="text-white">{totalCount}</strong> commodities
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

      {/* Product Dossier Modal */}
      {selectedProductId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col animate-fadeIn">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-metagov-950 border border-metagov-700 flex items-center justify-center text-metagov-400 font-bold text-xs">
                  DOS
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    {dossier?.product.name || 'Commodity Compliance Dossier'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    GTIN: {dossier?.product.barcode_gtin || 'Unspecified'} &bull; Category: {dossier?.product.category}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedProductId(null);
                  setDossier(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Dossier Tabs */}
            <div className="flex items-center gap-2 px-4 border-b border-slate-800 bg-slate-950/30 text-xs">
              <button
                onClick={() => setActiveDossierTab('overview')}
                className={`py-2.5 px-3 border-b-2 font-medium transition-colors ${
                  activeDossierTab === 'overview'
                    ? 'border-metagov-500 text-white font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveDossierTab('inspections')}
                className={`py-2.5 px-3 border-b-2 font-medium transition-colors ${
                  activeDossierTab === 'inspections'
                    ? 'border-metagov-500 text-white font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Inspections ({dossier?.inspections.length || 0})
              </button>
              <button
                onClick={() => setActiveDossierTab('violations')}
                className={`py-2.5 px-3 border-b-2 font-medium transition-colors ${
                  activeDossierTab === 'violations'
                    ? 'border-metagov-500 text-white font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Violations ({dossier?.violations.length || 0})
              </button>
              <button
                onClick={() => setActiveDossierTab('reports')}
                className={`py-2.5 px-3 border-b-2 font-medium transition-colors ${
                  activeDossierTab === 'reports'
                    ? 'border-metagov-500 text-white font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Reports ({dossier?.reports.length || 0})
              </button>
              <button
                onClick={() => setActiveDossierTab('audit')}
                className={`py-2.5 px-3 border-b-2 font-medium transition-colors ${
                  activeDossierTab === 'audit'
                    ? 'border-metagov-500 text-white font-semibold'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                Audit Trail ({dossier?.audit_history.length || 0})
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 overflow-y-auto flex-1 text-xs">
              {isLoadingDossier ? (
                <div className="py-12 text-center text-slate-400">
                  <div className="w-6 h-6 border-2 border-metagov-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  Loading statutory product dossier...
                </div>
              ) : !dossier ? (
                <div className="py-12 text-center text-slate-500">Failed to load dossier data.</div>
              ) : (
                <>
                  {activeDossierTab === 'overview' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Brand</span>
                          <span className="font-semibold text-white mt-0.5 block">{dossier.product.brand}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Manufacturer</span>
                          <span className="font-semibold text-white mt-0.5 block">{dossier.product.manufacturer || 'Unspecified'}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Total Audits</span>
                          <span className="font-semibold text-white mt-0.5 block font-mono">{dossier.inspections.length}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Origin Country</span>
                          <span className="font-semibold text-white mt-0.5 block">{dossier.product.country_of_origin || 'India'}</span>
                        </div>
                      </div>

                      {dossier.latest_inspection && (
                        <div className="p-3.5 bg-metagov-950/40 border border-metagov-800/80 rounded-lg space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <ShieldCheck className="w-4 h-4 text-metagov-400" />
                              Latest Compliance Evaluation
                            </span>
                            <Badge variant={dossier.latest_inspection.overall_result === 'COMPLIANT' ? 'success' : 'warning'}>
                              {dossier.latest_inspection.overall_result || 'PENDING'}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-slate-300">
                            Inspected on {new Date(dossier.latest_inspection.inspection_date).toLocaleDateString()} by {dossier.latest_inspection.inspector_name}
                          </p>
                        </div>
                      )}

                      {dossier.product.images.length > 0 && (
                        <div>
                          <p className="font-semibold text-white mb-2">Registered Package Label Images</p>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {dossier.product.images.map((img) => (
                              <div key={img.id} className="border border-slate-800 rounded-lg p-2 bg-slate-950 text-center">
                                <span className="text-[10px] text-metagov-400 block mb-1 font-mono">{img.image_type}</span>
                                <span className="text-[10px] text-slate-500 truncate block">{img.image_url_or_path}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {activeDossierTab === 'inspections' && (
                    <div className="space-y-2">
                      {dossier.inspections.map((insp) => (
                        <div key={insp.id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-white block">
                              Inspection #{insp.id.slice(0, 8)}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              {new Date(insp.inspection_date).toLocaleString()} &bull; Inspector: {insp.inspector_name}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge variant={insp.overall_result === 'COMPLIANT' ? 'success' : 'warning'}>
                              {insp.overall_result || insp.status}
                            </Badge>
                            <span className="text-[11px] font-mono text-slate-400">
                              {insp.violations_count} violations
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeDossierTab === 'violations' && (
                    <div className="space-y-2">
                      {dossier.violations.length === 0 ? (
                        <div className="py-6 text-center text-slate-500">No violations flagged for this commodity.</div>
                      ) : (
                        dossier.violations.map((v) => (
                          <div key={v.id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between">
                            <div>
                              <span className="font-semibold text-red-300 font-mono block">{v.violation_code}</span>
                              <p className="text-[11px] text-slate-400 mt-0.5">{v.description}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant={v.severity === 'CRITICAL' ? 'danger' : 'warning'}>{v.severity}</Badge>
                              <Badge variant="neutral">{v.status}</Badge>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {activeDossierTab === 'reports' && (
                    <div className="space-y-2">
                      {dossier.reports.length === 0 ? (
                        <div className="py-6 text-center text-slate-500">No audit reports generated yet.</div>
                      ) : (
                        dossier.reports.map((r) => (
                          <div key={r.id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex items-center justify-between">
                            <div>
                              <span className="font-semibold text-white block">{r.report_type}</span>
                              <span className="text-[11px] text-slate-400">
                                Generated: {new Date(r.generated_at).toLocaleString()}
                              </span>
                            </div>
                            <Badge variant="neutral">{r.format}</Badge>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {activeDossierTab === 'audit' && (
                    <div className="space-y-2">
                      {dossier.audit_history.length === 0 ? (
                        <div className="py-6 text-center text-slate-500">No audit trail entries recorded.</div>
                      ) : (
                        dossier.audit_history.map((a) => (
                          <div key={a.id} className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-lg text-[11px] flex items-center justify-between">
                            <div>
                              <span className="font-semibold text-white">{a.action}</span>
                              <span className="text-slate-400 ml-2">by {a.user_name || 'System'}</span>
                            </div>
                            <span className="text-slate-500 font-mono">{new Date(a.timestamp).toLocaleString()}</span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setSelectedProductId(null);
                  setDossier(null);
                }}
              >
                Close Dossier
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
