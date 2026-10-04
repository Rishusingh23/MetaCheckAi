import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  XCircle,
  FileDown,
  Info,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  UserCheck,
  Download,
  MessageSquare,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Eye,
  Calculator,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import {
  ComplianceCheckItem,
  InspectionComplianceResponse,
  InspectionHistoryItem,
  ReportItem,
  ViolationItem,
} from '../types';
import {
  evaluateInspectionCompliance,
  generateInspectionReport,
  getInspectionCompliance,
  getInspectionHistory,
  getInspectionViolations,
  getReportDownloadUrl,
  listInspectionReports,
  reviewViolation,
} from '../services/api';

export const ScanResult: React.FC = () => {
  const [searchParams] = useSearchParams();
  const inspectionIdFromQuery = searchParams.get('inspection_id');

  const [inspectionId] = useState<string>(inspectionIdFromQuery || 'demo-inspection-01');
  const [complianceData, setComplianceData] = useState<InspectionComplianceResponse | null>(null);
  const [violations, setViolations] = useState<ViolationItem[]>([]);
  const [historyLogs, setHistoryLogs] = useState<InspectionHistoryItem[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState<string | null>(null);
  const [selectedCheck, setSelectedCheck] = useState<ComplianceCheckItem | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Zoomable Evidence Modal State
  const [viewingEvidence, setViewingEvidence] = useState<{
    title: string;
    imageUrl: string;
    bbox?: Record<string, any> | null;
    confidence?: number | null;
    description?: string | null;
  } | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);

  // Review Modal State
  const [reviewingViolation, setReviewingViolation] = useState<ViolationItem | null>(null);
  const [targetReviewStatus, setTargetReviewStatus] = useState<'OFFICER_CONFIRMED' | 'DISMISSED'>('OFFICER_CONFIRMED');
  const [officerComment, setOfficerComment] = useState<string>('');
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const loadInspectionData = async (id: string) => {
    try {
      const data = await getInspectionCompliance(id);
      if (data && data.checks && data.checks.length > 0) {
        setComplianceData(data);
      } else {
        const evaluated = await evaluateInspectionCompliance(id);
        setComplianceData(evaluated);
      }
    } catch (err: any) {
      console.warn('Could not fetch remote compliance dossier:', err);
    }

    try {
      const viols = await getInspectionViolations(id);
      setViolations(viols || []);
    } catch (err) {
      console.warn('Could not fetch violations:', err);
    }

    try {
      const history = await getInspectionHistory(id);
      setHistoryLogs(history || []);
    } catch (err) {
      console.warn('Could not fetch history:', err);
    }

    try {
      const reps = await listInspectionReports(id);
      setReports(reps || []);
    } catch (err) {
      console.warn('Could not fetch reports:', err);
    }
  };

  useEffect(() => {
    loadInspectionData(inspectionId);
  }, [inspectionId]);

  const handleReevaluate = async () => {
    setIsEvaluating(true);
    try {
      const result = await evaluateInspectionCompliance(inspectionId, {
        notes: 'Officer re-evaluation requested via UI',
      });
      setComplianceData(result);
      await loadInspectionData(inspectionId);
    } catch (err: any) {
      console.error('Re-evaluation error:', err);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleGenerateReport = async (format: 'PDF' | 'JSON' | 'CSV') => {
    try {
      setIsGeneratingReport(format);
      const rep = await generateInspectionReport(inspectionId, format);
      setReports((prev) => [rep, ...prev]);
      // Also refresh history
      const history = await getInspectionHistory(inspectionId);
      setHistoryLogs(history || []);
    } catch (err) {
      console.error('Failed to generate report:', err);
    } finally {
      setIsGeneratingReport(null);
    }
  };

  const handleOpenReviewModal = (v: ViolationItem, decision: 'OFFICER_CONFIRMED' | 'DISMISSED') => {
    setReviewingViolation(v);
    setTargetReviewStatus(decision);
    setOfficerComment(
      decision === 'OFFICER_CONFIRMED'
        ? `Physically verified packaging: non-compliance with ${v.violation_code} confirmed.`
        : 'Physically inspected packaging under clear illumination; statutory declaration is legible and compliant.'
    );
    setReviewError(null);
  };

  const handleSubmitReview = async () => {
    if (!reviewingViolation) return;
    if (!officerComment || officerComment.trim().length < 3) {
      setReviewError('Mandatory officer rationale of at least 3 characters is required.');
      return;
    }

    try {
      setReviewSubmitting(true);
      setReviewError(null);
      await reviewViolation(reviewingViolation.id, {
        status: targetReviewStatus,
        comment: officerComment.trim(),
      });
      setReviewingViolation(null);
      await loadInspectionData(inspectionId);
    } catch (err: any) {
      console.error('Failed to submit review:', err);
      setReviewError(err?.response?.data?.detail || 'Failed to submit review decision.');
    } finally {
      setReviewSubmitting(false);
    }
  };

  const filteredChecks = complianceData?.checks.filter((c) => {
    if (statusFilter === 'ALL') return true;
    return c.status === statusFilter;
  }) || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            PASS
          </span>
        );
      case 'FAIL':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            POTENTIAL NON-COMPLIANCE
          </span>
        );
      case 'REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
            REVIEW REQUIRED
          </span>
        );
      case 'NOT_APPLICABLE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            N/A
          </span>
        );
    }
  };

  const getOverallBanner = (overall: string) => {
    if (overall === 'COMPLIANT') {
      return {
        bg: 'bg-emerald-500/10 border-emerald-500/30',
        iconBg: 'bg-emerald-500/20 text-emerald-400',
        title: 'Compliant Packaging Verified',
        badge: <Badge variant="success">Compliant</Badge>,
        desc: 'All applicable Legal Metrology statutory requirements appear satisfied based on AI label screening.',
        icon: <CheckCircle2 className="w-6 h-6" />,
      };
    }
    if (overall === 'OFFICER_REVIEWED') {
      return {
        bg: 'bg-metagov-500/10 border-metagov-500/30',
        iconBg: 'bg-metagov-500/20 text-metagov-400',
        title: 'Enforcement Officer Review Completed',
        badge: <Badge variant="info">Officer Reviewed</Badge>,
        desc: 'All flagged statutory findings have been formally reviewed by an authorized Legal Metrology officer.',
        icon: <ShieldCheck className="w-6 h-6" />,
      };
    }
    if (overall === 'POTENTIAL_NON_COMPLIANCE') {
      return {
        bg: 'bg-rose-500/10 border-rose-500/30',
        iconBg: 'bg-rose-500/20 text-rose-400',
        title: 'Potential Non-Compliance Detected',
        badge: <Badge variant="danger">Potential Non-Compliance</Badge>,
        desc: 'One or more mandatory statutory declarations failed automated screening rules. Enforcement review required.',
        icon: <AlertTriangle className="w-6 h-6" />,
      };
    }
    return {
      bg: 'bg-amber-500/10 border-amber-500/30',
      iconBg: 'bg-amber-500/20 text-amber-400',
      title: 'Review Required',
      badge: <Badge variant="warning">Review Required</Badge>,
      desc: 'Some declarations or dimensions require officer review due to image ambiguity or physical calibration requirements.',
      icon: <HelpCircle className="w-6 h-6" />,
    };
  };

  const banner = complianceData ? getOverallBanner(complianceData.overall_status) : null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Breadcrumbs & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Link to="/history" className="hover:text-white transition-colors">
              Inspections
            </Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-slate-200 font-mono">#{inspectionId.slice(0, 8)}</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-metagov-400 font-semibold">Inspection Dossier & Review</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
            Inspection Dossier & Enforcement Review
          </h1>
        </div>

        {/* Action Controls & Report Generation Bar */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReevaluate}
            isLoading={isEvaluating}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Re-evaluate
          </Button>
          <div className="h-4 w-px bg-slate-800" />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleGenerateReport('PDF')}
            isLoading={isGeneratingReport === 'PDF'}
            leftIcon={<FileDown className="w-3.5 h-3.5 text-rose-400" />}
          >
            Generate PDF
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleGenerateReport('JSON')}
            isLoading={isGeneratingReport === 'JSON'}
            leftIcon={<Download className="w-3.5 h-3.5 text-sky-400" />}
          >
            JSON
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleGenerateReport('CSV')}
            isLoading={isGeneratingReport === 'CSV'}
            leftIcon={<Download className="w-3.5 h-3.5 text-emerald-400" />}
          >
            CSV
          </Button>
        </div>
      </div>

      {/* Top Banner: Advisory Screening Result */}
      {banner && (
        <div className={`rounded-2xl p-5 border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl ${banner.bg}`}>
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-xl shrink-0 ${banner.iconBg}`}>{banner.icon}</div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Advisory Screening Verdict
                </span>
                {banner.badge}
                <span className="text-xs font-mono text-slate-400">
                  Confidence: {((complianceData?.mean_confidence || 0.9) * 100).toFixed(1)}%
                </span>
              </div>
              <h2 className="text-lg font-bold text-white mt-1">{banner.title}</h2>
              <p className="text-xs text-slate-300 mt-0.5 max-w-3xl leading-relaxed">
                {banner.desc}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Metric Cards Grid */}
      {(() => {
        const passCount = complianceData?.pass_count ?? 0;
        const failCount = complianceData?.fail_count ?? 0;
        const reviewCount = complianceData?.review_count ?? 0;
        const totalEvaluated = passCount + failCount + reviewCount;
        const computedScore = complianceData?.screening_score ?? (totalEvaluated > 0 ? Number(((passCount / totalEvaluated) * 100).toFixed(1)) : 0);

        return (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            <div
              className="bg-slate-900/60 border border-metagov-500/30 rounded-xl p-3.5 relative group cursor-help"
              title="This indicator represents the proportion of applicable evaluated checks that passed. It is an AI-assisted screening metric and does not constitute a final legal determination."
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-metagov-400">AI-Assisted Screening Indicator</span>
                <Calculator className="w-3.5 h-3.5 text-metagov-400" />
              </div>
              <p className="text-2xl font-bold text-white mt-1">
                {computedScore}
                <span className="text-xs text-slate-400 font-normal"> %</span>
              </p>
              <span className="text-[9px] text-slate-400 block mt-0.5">
                Pass / (Pass+Fail+Review)
              </span>
              <div className="hidden group-hover:block absolute z-30 bottom-full left-0 mb-2 w-64 p-2 bg-slate-900 border border-slate-700 rounded-lg shadow-xl text-[10px] text-slate-300 leading-tight pointer-events-none">
                This indicator represents the proportion of applicable evaluated checks that passed. It is an AI-assisted screening metric and does not constitute a final legal determination.
              </div>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">Rules Evaluated</span>
              <p className="text-2xl font-bold text-white mt-1">
                {complianceData?.total_rules_evaluated ?? 0}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-emerald-500/20 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-emerald-400">Passed Checks</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">
                {complianceData?.pass_count ?? 0}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-rose-500/20 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-rose-400">Potential Violations</span>
              <p className="text-2xl font-bold text-rose-400 mt-1">
                {complianceData?.fail_count ?? 0}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-amber-500/20 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-amber-400">Review Required</span>
              <p className="text-2xl font-bold text-amber-400 mt-1">
                {complianceData?.review_count ?? 0}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-slate-400">Total Violations</span>
              <p className="text-2xl font-bold text-slate-300 mt-1">
                {violations.length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-metagov-500/20 rounded-xl p-3.5">
              <span className="text-[11px] font-medium text-metagov-400">Audit Reports</span>
              <p className="text-2xl font-bold text-metagov-400 mt-1">
                {reports.length}
              </p>
            </div>
          </div>
        );
      })()}

      {/* Enforcement Officer Violation Review Section */}
      {violations.length > 0 && (
        <Card
          title="Enforcement Officer Violation Review"
          subtitle="Mandatory officer verification on AI-flagged potential non-compliances"
        >
          <div className="space-y-4">
            {violations.map((v) => {
              const isConfirmed = v.status === 'OFFICER_CONFIRMED';
              const isDismissed = v.status === 'DISMISSED';
              const isPending = v.status === 'FLAGGED_FOR_REVIEW';

              return (
                <div
                  key={v.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isConfirmed
                      ? 'bg-rose-950/20 border-rose-500/40'
                      : isDismissed
                      ? 'bg-slate-900/50 border-slate-700/60'
                      : 'bg-amber-950/20 border-amber-500/40'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800/60">
                          {v.violation_code}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          v.severity === 'CRITICAL'
                            ? 'bg-red-500/20 text-red-300'
                            : v.severity === 'MAJOR'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-slate-800 text-slate-300'
                        }`}>
                          {v.severity}
                        </span>
                        {isConfirmed && <Badge variant="danger">Officer Confirmed</Badge>}
                        {isDismissed && <Badge variant="neutral">Dismissed by Officer</Badge>}
                        {isPending && <Badge variant="warning">Flagged for Review</Badge>}
                      </div>
                      <p className="text-xs text-slate-200 mt-1 font-medium">{v.description}</p>
                    </div>

                    {/* Review Actions */}
                    <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                      <Button
                        variant={isConfirmed ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => handleOpenReviewModal(v, 'OFFICER_CONFIRMED')}
                        leftIcon={<UserCheck className="w-3.5 h-3.5 text-rose-400" />}
                      >
                        Confirm Violation
                      </Button>
                      <Button
                        variant={isDismissed ? 'secondary' : 'outline'}
                        size="sm"
                        onClick={() => handleOpenReviewModal(v, 'DISMISSED')}
                        leftIcon={<XCircle className="w-3.5 h-3.5 text-slate-400" />}
                      >
                        Dismiss Finding
                      </Button>
                    </div>
                  </div>

                  {/* Evidences Traceability List */}
                  {v.evidences && v.evidences.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Direct Evidence Links ({v.evidences.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {v.evidences.map((ev, evIdx) => (
                          <div
                            key={ev.id || evIdx}
                            className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-2 text-xs"
                          >
                            <div className="space-y-0.5 min-w-0">
                              <span className="font-mono text-[10px] text-metagov-400 block font-semibold">
                                {ev.source_type}
                              </span>
                              <p className="text-slate-300 text-[11px] truncate">
                                {ev.description || 'Statutory OCR bounding region'}
                              </p>
                              {ev.bounding_box && (
                                <span className="text-[10px] font-mono text-slate-500 block">
                                  BBox: [{ev.bounding_box.x1},{ev.bounding_box.y1} → {ev.bounding_box.x2},{ev.bounding_box.y2}]
                                </span>
                              )}
                            </div>
                            {ev.image_url_or_path && (
                              <button
                                onClick={() => {
                                  setViewingEvidence({
                                    title: `${v.violation_code} Evidence`,
                                    imageUrl: ev.image_url_or_path!,
                                    bbox: ev.bounding_box,
                                    confidence: ev.confidence,
                                    description: ev.description,
                                  });
                                  setZoomLevel(1.0);
                                }}
                                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium flex items-center gap-1 shrink-0 transition-colors"
                              >
                                <Eye className="w-3 h-3 text-metagov-400" />
                                Inspect
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Officer Comments / Notes if already reviewed */}
                  {v.officer_comment && (
                    <div className="mt-3 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs flex items-start gap-2">
                      <MessageSquare className="w-4 h-4 text-metagov-400 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                          <strong className="text-slate-300">Officer Verification Note:</strong>
                          {v.reviewed_at && (
                            <span>
                              {new Date(v.reviewed_at).toLocaleString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>
                        <p className="text-slate-200 leading-relaxed">{v.officer_comment}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Generated Reports Subsystem Bar */}
      {reports.length > 0 && (
        <Card
          title="AI-Assisted Legal Metrology Inspection Reports"
          subtitle="Advisory compiled dossiers available for digital recordkeeping and export"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {reports.map((rep) => (
              <div
                key={rep.id}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between gap-3 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded">
                      {rep.format}
                    </span>
                    <Badge variant="success">READY</Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {new Date(rep.created_at || rep.generated_at).toLocaleString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
                <a
                  href={getReportDownloadUrl(rep.id)}
                  download
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-metagov-600 hover:bg-metagov-500 text-white text-xs font-semibold shadow transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Main Breakdown Section */}
      <Card
        title="Rule-by-Rule Statutory Compliance Breakdown"
        subtitle="Evaluated under Legal Metrology (Packaged Commodities) Rules, 2011 and Gazette Amendments"
        action={
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Filter:</span>
            {['ALL', 'PASS', 'FAIL', 'REVIEW'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
                  statusFilter === st
                    ? 'bg-metagov-600 text-white shadow-sm'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        }
      >
        <div className="space-y-3.5">
          {filteredChecks.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-sm">
              No rule findings match the selected filter.
            </div>
          ) : (
            filteredChecks.map((check) => {
              const ruleVer = check.rule_version;

              return (
                <div
                  key={check.id}
                  className={`p-4 rounded-xl border transition-all ${
                    check.status === 'FAIL'
                      ? 'bg-rose-500/5 border-rose-500/30'
                      : check.status === 'REVIEW'
                      ? 'bg-amber-500/5 border-amber-500/30'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-metagov-950/80 text-metagov-400 border border-metagov-800/60">
                        {ruleVer?.version ? `v${ruleVer.version}` : 'v1.0'}
                      </span>
                      <span className="text-xs font-bold text-white">
                        {ruleVer?.requirement_text ? ruleVer.requirement_text.split('.')[0] : 'Statutory Check'}
                      </span>
                      {ruleVer?.severity && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          ruleVer.severity === 'CRITICAL'
                            ? 'bg-red-500/20 text-red-300'
                            : ruleVer.severity === 'MAJOR'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-slate-800 text-slate-300'
                        }`}>
                          {ruleVer.severity}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      {getStatusBadge(check.status)}
                    </div>
                  </div>

                  {/* Requirements & Detected Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                    <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                      <span className="block text-[10px] uppercase tracking-wider font-semibold text-slate-400 mb-1">
                        Statutory Requirement
                      </span>
                      <p className="text-xs text-slate-200 leading-relaxed font-sans">
                        {check.expected_requirement || ruleVer?.requirement_text || 'Prescribed Legal Metrology requirement.'}
                      </p>
                      {ruleVer?.source_gazette_reference && (
                        <span className="block text-[10px] text-metagov-400/80 mt-1 font-mono">
                          Source: {ruleVer.source_gazette_reference}
                        </span>
                      )}
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
                      <span className="block text-[10px] uppercase tracking-wider font-semibold text-slate-400 mb-1">
                        Detected Declaration Value
                      </span>
                      <p className="text-xs text-slate-200 font-mono break-words">
                        {check.detected_value ? (
                          check.detected_value
                        ) : (
                          <span className="text-slate-500 italic">Not extracted / detected</span>
                        )}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                        <span>Confidence: {((check.confidence || 0.85) * 100).toFixed(1)}%</span>
                        {check.status === 'FAIL' && (
                          <span className="text-rose-400 font-medium">Potential Non-Compliance</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Explanatory Rationales */}
                  {check.explanation && (
                    <div className="mt-3 text-xs text-slate-300 flex items-start gap-2 bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/60">
                      <Info className="w-4 h-4 text-metagov-400 shrink-0 mt-0.5" />
                      <p className="leading-relaxed">{check.explanation}</p>
                    </div>
                  )}

                  <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
                    <span>Validation Type: <strong className="font-mono text-slate-300">{ruleVer?.validation_type || 'PRESENCE_CHECK'}</strong></span>
                    <button
                      onClick={() => setSelectedCheck(check)}
                      className="text-metagov-400 hover:text-metagov-300 flex items-center gap-1 font-medium transition-colors"
                    >
                      Inspect Statutory Evidence <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* Chronological Audit Trail History */}
      {historyLogs.length > 0 && (
        <Card
          title="Inspection Audit History & Action Log"
          subtitle="Immutable chronological audit trail recording transitions, reviews, and report generation"
        >
          <div className="relative border-l border-slate-800 ml-4 space-y-4 py-2">
            {historyLogs.map((log) => (
              <div key={log.id} className="relative pl-6">
                <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-metagov-500 border-2 border-slate-900" />
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-mono font-bold text-white">{log.action}</span>
                    <span className="text-[11px] text-slate-400">
                      {new Date(log.timestamp).toLocaleString('en-IN', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  {log.previous_status && log.new_status && (
                    <p className="text-slate-400 text-[11px]">
                      Status transition: <span className="text-slate-300 font-mono">{log.previous_status}</span> &rarr;{' '}
                      <span className="text-metagov-400 font-mono font-semibold">{log.new_status}</span>
                    </p>
                  )}
                  {log.change_metadata && (
                    <p className="text-slate-400 text-[11px] bg-slate-900/60 p-1.5 rounded font-mono break-words">
                      {JSON.stringify(log.change_metadata)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Statutory Advisory Disclaimer Footer */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 flex items-start gap-3 text-xs text-slate-400">
        <Info className="w-5 h-5 text-metagov-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-300 block mb-0.5">Authoritative Legal Metrology Notice:</strong>
          {complianceData?.disclaimer ||
            'MetaCheck AI operates as an automated AI screening assistant. System outcomes represent potential advisory findings and do not constitute official statutory legal verdicts. All enforcement decisions and compounding notices remain within the sole legal purview of authorized Legal Metrology Officers.'}
        </div>
      </div>

      {/* Review Submission Modal */}
      {reviewingViolation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-metagov-400" />
                <h3 className="text-base font-bold text-white">Statutory Violation Review</h3>
              </div>
              <button
                onClick={() => setReviewingViolation(null)}
                className="text-slate-400 hover:text-white text-lg font-bold p-1"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <span className="font-mono text-metagov-400 font-bold">{reviewingViolation.violation_code}</span>
                <p className="text-slate-200">{reviewingViolation.description}</p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Enforcement Decision:</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setTargetReviewStatus('OFFICER_CONFIRMED')}
                    className={`p-2.5 rounded-lg border font-semibold text-xs transition-all ${
                      targetReviewStatus === 'OFFICER_CONFIRMED'
                        ? 'bg-rose-950/60 border-rose-500 text-rose-300 shadow'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    Confirm Violation
                  </button>
                  <button
                    type="button"
                    onClick={() => setTargetReviewStatus('DISMISSED')}
                    className={`p-2.5 rounded-lg border font-semibold text-xs transition-all ${
                      targetReviewStatus === 'DISMISSED'
                        ? 'bg-slate-800 border-slate-600 text-white shadow'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    Dismiss Finding
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Officer Statutory Rationale & Evidence Comment (Mandatory):
                </label>
                <textarea
                  value={officerComment}
                  onChange={(e) => setOfficerComment(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-metagov-500"
                  placeholder="State physical inspection findings, lighting calibration, or grounds for compounding..."
                />
              </div>

              {reviewError && (
                <div className="p-2.5 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
                  {reviewError}
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setReviewingViolation(null)}
                disabled={reviewSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmitReview}
                isLoading={reviewSubmitting}
              >
                Submit Statutory Review
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Modal */}
      {selectedCheck && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-metagov-400">
                  {selectedCheck.rule_version_id}
                </span>
                <h3 className="text-base font-bold text-white">Statutory Evidence & Rule Specs</h3>
              </div>
              <button
                onClick={() => setSelectedCheck(null)}
                className="text-slate-400 hover:text-white text-lg font-bold p-1"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 uppercase font-semibold text-[10px]">Legal Source Reference</span>
                <p className="text-slate-200 mt-0.5 font-medium">
                  {selectedCheck.rule_version?.source_gazette_reference || 'Legal Metrology (Packaged Commodities) Rules, 2011'}
                </p>
              </div>

              <div>
                <span className="text-slate-400 uppercase font-semibold text-[10px]">Statutory Requirement Text</span>
                <p className="text-slate-200 mt-0.5 p-2.5 rounded bg-slate-950 border border-slate-800 font-sans leading-relaxed">
                  {selectedCheck.rule_version?.requirement_text || selectedCheck.expected_requirement}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 uppercase font-semibold text-[10px]">Screening Status</span>
                  <div className="mt-1">{getStatusBadge(selectedCheck.status)}</div>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 uppercase font-semibold text-[10px]">Confidence Level</span>
                  <p className="text-slate-200 font-mono mt-1 font-bold">
                    {((selectedCheck.confidence || 0.85) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              <div>
                <span className="text-slate-400 uppercase font-semibold text-[10px]">Finding Explanation & Notes</span>
                <p className="text-slate-300 mt-0.5 p-2.5 rounded bg-slate-950 border border-slate-800 leading-relaxed">
                  {selectedCheck.explanation}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedCheck(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Zoomable Evidence Viewer Modal */}
      {viewingEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Eye className="w-5 h-5 text-metagov-400" />
                <h3 className="text-base font-bold text-white">{viewingEvidence.title}</h3>
                {viewingEvidence.confidence && (
                  <Badge variant="info">
                    {Math.round(viewingEvidence.confidence * 100)}% Conf
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* Zoom Controls */}
                <div className="flex items-center bg-slate-950 rounded-lg border border-slate-800 p-1 gap-1">
                  <button
                    onClick={() => setZoomLevel((z) => Math.max(0.75, z - 0.25))}
                    className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <span className="font-mono text-[11px] px-2 text-slate-300">
                    {Math.round(zoomLevel * 100)}%
                  </span>
                  <button
                    onClick={() => setZoomLevel((z) => Math.min(3.0, z + 0.25))}
                    className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setZoomLevel(1.0)}
                    className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors ml-1"
                    title="Reset Zoom"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>
                <button
                  onClick={() => setViewingEvidence(null)}
                  className="text-slate-400 hover:text-white text-lg font-bold p-1 ml-2"
                >
                  &times;
                </button>
              </div>
            </div>

            {/* Canvas Area */}
            <div className="flex-1 overflow-auto bg-slate-950 rounded-xl border border-slate-800 p-4 flex items-center justify-center min-h-[380px] max-h-[550px] relative">
              <div
                className="relative transition-transform duration-150 origin-center"
                style={{ transform: `scale(${zoomLevel})` }}
              >
                <img
                  src={viewingEvidence.imageUrl}
                  alt={viewingEvidence.title}
                  className="max-h-[460px] object-contain rounded select-none shadow-lg"
                />

                {/* Spatial Coordinate Bounding Box Overlay */}
                {viewingEvidence.bbox && (
                  <div
                    className="absolute border-2 border-rose-500 bg-rose-500/20 rounded shadow-md pointer-events-none"
                    style={{
                      left: `${viewingEvidence.bbox.x1}px`,
                      top: `${viewingEvidence.bbox.y1}px`,
                      width: `${Math.max(4, viewingEvidence.bbox.x2 - viewingEvidence.bbox.x1)}px`,
                      height: `${Math.max(4, viewingEvidence.bbox.y2 - viewingEvidence.bbox.y1)}px`,
                    }}
                  >
                    <span className="absolute -top-5 left-0 bg-rose-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow whitespace-nowrap">
                      Statutory ROI
                    </span>
                  </div>
                )}
              </div>
            </div>

            {viewingEvidence.description && (
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                <strong className="text-slate-200">Evidence Annotation: </strong>
                {viewingEvidence.description}
              </p>
            )}

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setViewingEvidence(null)}>
                Close Evidence Viewer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
