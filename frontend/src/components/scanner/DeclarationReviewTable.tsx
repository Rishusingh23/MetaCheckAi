import React, { useState } from 'react';
import {
  AlertCircle,
  Edit3,
  Check,
  X,
  Target,
  FileCheck2,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { DeclarationItem, DeclarationType, ExtractionStatus } from '../../types';

interface DeclarationReviewTableProps {
  declarations: DeclarationItem[];
  meanConfidence: number;
  onSelectDeclaration?: (declaration: DeclarationItem) => void;
  onUpdateDeclaration?: (declarationId: string, updated: Partial<DeclarationItem>, notes?: string) => Promise<void>;
  selectedDeclarationId?: string | null;
}

const DECLARATION_TYPE_LABELS: Record<DeclarationType, { label: string; icon: string; category: string }> = {
  PRODUCT_NAME: { label: 'Product Name', icon: '🏷️', category: 'Identity' },
  GENERIC_NAME: { label: 'Generic / Common Name', icon: '📦', category: 'Identity' },
  NET_QUANTITY: { label: 'Net Quantity', icon: '⚖️', category: 'Measurement' },
  MRP: { label: 'Maximum Retail Price (MRP)', icon: '₹', category: 'Financial' },
  UNIT_SALE_PRICE: { label: 'Unit Sale Price (USP)', icon: '🏷️', category: 'Financial' },
  DATE_OF_MANUFACTURE: { label: 'Date of Manufacture', icon: '📅', category: 'Dates' },
  DATE_OF_PACKING: { label: 'Date of Packing / Import', icon: '📆', category: 'Dates' },
  MANUFACTURER_DETAILS: { label: 'Manufacturer Details', icon: '🏭', category: 'Entity' },
  PACKER_DETAILS: { label: 'Packer Details', icon: '📦', category: 'Entity' },
  IMPORTER_DETAILS: { label: 'Importer Details', icon: '🚢', category: 'Entity' },
  COUNTRY_OF_ORIGIN: { label: 'Country of Origin', icon: '🌐', category: 'Entity' },
  CONSUMER_CARE: { label: 'Consumer Care / Helpline', icon: '📞', category: 'Support' },
  OTHER: { label: 'Other Statutory Markings', icon: '📝', category: 'Other' },
};

export const DeclarationReviewTable: React.FC<DeclarationReviewTableProps> = ({
  declarations,
  meanConfidence,
  onSelectDeclaration,
  onUpdateDeclaration,
  selectedDeclarationId,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [editingItem, setEditingItem] = useState<DeclarationItem | null>(null);
  const [editNormalizedValue, setEditNormalizedValue] = useState<string>('');
  const [editStatus, setEditStatus] = useState<ExtractionStatus>('CONFIRMED');
  const [editNotes, setEditNotes] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [expandedAlternatives, setExpandedAlternatives] = useState<Record<string, boolean>>({});

  const filteredDeclarations = declarations.filter((item) => {
    if (filterStatus === 'ALL') return true;
    if (filterStatus === 'AMBIGUOUS') return item.extraction_status === 'AMBIGUOUS';
    if (filterStatus === 'CONFIRMED') return item.extraction_status === 'CONFIRMED';
    if (filterStatus === 'MANUALLY_EDITED') return item.extraction_status === 'MANUALLY_EDITED';
    return item.extraction_status === filterStatus;
  });

  const handleStartEdit = (item: DeclarationItem) => {
    setEditingItem(item);
    setEditNormalizedValue(item.normalized_value || item.raw_value || '');
    setEditStatus((item.extraction_status as ExtractionStatus) || 'CONFIRMED');
    setEditNotes('');
  };

  const handleSaveEdit = async () => {
    if (!editingItem || !onUpdateDeclaration) return;
    setIsSaving(true);
    try {
      await onUpdateDeclaration(
        editingItem.id,
        {
          normalized_value: editNormalizedValue,
          extraction_status: editStatus,
        },
        editNotes
      );
      setEditingItem(null);
    } catch (err) {
      console.error('Failed to update declaration:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleAlternatives = (id: string) => {
    setExpandedAlternatives((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const ambiguousCount = declarations.filter((d) => d.extraction_status === 'AMBIGUOUS').length;
  const confirmedCount = declarations.filter((d) => d.extraction_status === 'CONFIRMED').length;

  return (
    <div className="space-y-4">
      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
          <span className="text-slate-400 block text-[11px]">Total Declarations</span>
          <span className="text-lg font-bold text-white font-mono">{declarations.length}</span>
          <span className="text-[10px] text-slate-500 block">Structured Items</span>
        </div>

        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
          <span className="text-slate-400 block text-[11px]">Mean Confidence</span>
          <span className="text-lg font-bold text-metagov-400 font-mono">
            {(meanConfidence * 100).toFixed(1)}%
          </span>
          <span className="text-[10px] text-slate-500 block">Multi-factor Score</span>
        </div>

        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
          <span className="text-slate-400 block text-[11px]">Ambiguous Items</span>
          <span className={`text-lg font-bold font-mono ${ambiguousCount > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
            {ambiguousCount}
          </span>
          <span className="text-[10px] text-slate-500 block">Requires Officer Review</span>
        </div>

        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
          <span className="text-slate-400 block text-[11px]">Officer Confirmed</span>
          <span className="text-lg font-bold text-emerald-400 font-mono">{confirmedCount}</span>
          <span className="text-[10px] text-slate-500 block">Verified Evidence</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex gap-2">
          {['ALL', 'AMBIGUOUS', 'CONFIRMED', 'MANUALLY_EDITED'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                filterStatus === st
                  ? 'bg-metagov-600/30 text-metagov-300 border border-metagov-500/50'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900/50 border border-transparent'
              }`}
            >
              {st === 'ALL' ? 'All Declarations' : st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Declarations List / Table */}
      <div className="space-y-3">
        {filteredDeclarations.length === 0 ? (
          <div className="p-8 text-center text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
            <FileCheck2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-xs">No declarations found for filter: {filterStatus}</p>
          </div>
        ) : (
          filteredDeclarations.map((item) => {
            const typeInfo = DECLARATION_TYPE_LABELS[item.declaration_type] || {
              label: item.declaration_type,
              icon: '📋',
              category: 'General',
            };
            const isSelected = selectedDeclarationId === item.id;
            const confidencePct = Math.round((item.confidence || 0) * 100);
            const bbox = item.bounding_box;
            const hasAlternatives =
              bbox && Array.isArray(bbox.alternative_candidates) && bbox.alternative_candidates.length > 0;
            const isAmbiguous = item.extraction_status === 'AMBIGUOUS' || bbox?.is_ambiguous;
            const isManuallyEdited = bbox?.is_manually_edited || item.extraction_status === 'MANUALLY_EDITED';

            return (
              <div
                key={item.id}
                id={`declaration-${item.id}`}
                onClick={() => onSelectDeclaration?.(item)}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-metagov-600/20 border-metagov-500 ring-1 ring-metagov-500/40 shadow-lg'
                    : 'bg-slate-950/70 border-slate-800/90 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{typeInfo.icon}</span>
                    <div>
                      <h4 className="text-xs font-bold text-white tracking-wide flex items-center gap-2">
                        {typeInfo.label}
                        <span className="text-[10px] text-slate-400 font-normal px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700">
                          {item.declaration_type}
                        </span>
                      </h4>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Status Badge */}
                    <Badge
                      size="sm"
                      variant={
                        item.extraction_status === 'CONFIRMED'
                          ? 'success'
                          : isAmbiguous
                          ? 'warning'
                          : isManuallyEdited
                          ? 'info'
                          : 'neutral'
                      }
                    >
                      {item.extraction_status}
                    </Badge>

                    {/* Confidence */}
                    <Badge
                      size="sm"
                      variant={
                        confidencePct >= 85 ? 'success' : confidencePct >= 65 ? 'warning' : 'danger'
                      }
                    >
                      {confidencePct}% conf
                    </Badge>
                  </div>
                </div>

                {/* Values Display */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 pt-2 border-t border-slate-900">
                  {/* Normalized Output */}
                  <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] font-semibold text-metagov-400 uppercase tracking-wider block mb-1 flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" />
                      Normalized Declaration Value
                    </span>
                    <p className="text-xs font-medium text-slate-100 break-words">
                      {item.normalized_value || <span className="text-slate-500 italic">Not normalized</span>}
                    </p>
                  </div>

                  {/* Raw OCR Evidence */}
                  <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/60">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                      Raw OCR Evidence (Preserved Literal)
                    </span>
                    <p className="text-xs font-mono text-slate-300 break-words line-clamp-2">
                      {item.raw_value}
                    </p>
                  </div>
                </div>

                {/* Footnote with Coordinates and Rationale */}
                <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-2 text-[11px] text-slate-400 border-t border-slate-900/60">
                  <div className="flex items-center gap-2">
                    {bbox?.x1 !== undefined && (
                      <span className="font-mono text-[10px] text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                        BBox: [{bbox.x1}, {bbox.y1}] → [{bbox.x2}, {bbox.y2}]
                      </span>
                    )}
                    {bbox?.confidence_breakdown?.rationale && (
                      <span className="text-slate-400 text-[10px] italic">
                        {bbox.confidence_breakdown.rationale}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {hasAlternatives && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAlternatives(item.id);
                        }}
                        leftIcon={
                          expandedAlternatives[item.id] ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )
                        }
                      >
                        Alternatives ({bbox.alternative_candidates.length})
                      </Button>
                    )}

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectDeclaration?.(item);
                      }}
                      leftIcon={<Target className="w-3 h-3" />}
                    >
                      Locate Box
                    </Button>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartEdit(item);
                      }}
                      leftIcon={<Edit3 className="w-3 h-3" />}
                    >
                      Edit / Verify
                    </Button>
                  </div>
                </div>

                {/* Alternative Candidates Section */}
                {hasAlternatives && expandedAlternatives[item.id] && (
                  <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg space-y-2">
                    <p className="text-[11px] font-semibold text-amber-300 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" />
                      Alternative Detected Candidates (Ambiguity Disambiguation)
                    </p>
                    <div className="space-y-1.5">
                      {bbox.alternative_candidates.map((alt: any, altIdx: number) => (
                        <div
                          key={altIdx}
                          className="flex items-center justify-between p-2 bg-slate-950/80 rounded border border-slate-800 text-xs"
                        >
                          <div>
                            <span className="text-slate-200 font-medium">{alt.raw_value}</span>
                            {alt.normalized_value && (
                              <span className="text-slate-400 text-[11px] block">
                                → {alt.normalized_value}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] text-slate-400">
                              {Math.round((alt.confidence || 0) * 100)}% conf
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onUpdateDeclaration) {
                                  onUpdateDeclaration(
                                    item.id,
                                    {
                                      normalized_value: alt.normalized_value || alt.raw_value,
                                      extraction_status: 'CONFIRMED',
                                    },
                                    `Selected alternative candidate: ${alt.raw_value}`
                                  );
                                }
                              }}
                            >
                              Choose This
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Manual Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-metagov-400" />
                <h3 className="text-sm font-bold text-white">Manual Declaration Correction</h3>
              </div>
              <button
                onClick={() => setEditingItem(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Declaration Type</label>
                <input
                  type="text"
                  readOnly
                  value={editingItem.declaration_type}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-400 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Original Raw OCR Evidence</label>
                <input
                  type="text"
                  readOnly
                  value={editingItem.raw_value}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-400 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-200 font-semibold mb-1">
                  Normalized Value (Officer Corrected)
                </label>
                <textarea
                  rows={2}
                  value={editNormalizedValue}
                  onChange={(e) => setEditNormalizedValue(e.target.value)}
                  placeholder="Enter corrected standardized declaration value..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-medium focus:ring-2 focus:ring-metagov-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-200 font-semibold mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as ExtractionStatus)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:ring-2 focus:ring-metagov-500 focus:outline-none"
                >
                  <option value="CONFIRMED">CONFIRMED (Verified accurate)</option>
                  <option value="MANUALLY_EDITED">MANUALLY_EDITED (Edited with officer note)</option>
                  <option value="REJECTED">REJECTED (Invalid / False positive)</option>
                  <option value="AUTO_EXTRACTED">AUTO_EXTRACTED</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-200 font-semibold mb-1">Officer Audit Notes</label>
                <input
                  type="text"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="e.g. Corrected obscured digit in MRP from physical packaging inspection"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white focus:ring-2 focus:ring-metagov-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <Button variant="ghost" size="sm" onClick={() => setEditingItem(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                isLoading={isSaving}
                leftIcon={<Check className="w-4 h-4" />}
                onClick={handleSaveEdit}
              >
                Save & Update Evidence
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
