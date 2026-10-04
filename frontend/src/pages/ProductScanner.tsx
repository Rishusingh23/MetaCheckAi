import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud,
  ShieldAlert,
  FileImage,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  Sliders,
  FileCheck,
  FlaskConical,
  Zap,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { DeclarationReviewTable } from '../components/scanner/DeclarationReviewTable';
import {
  analyzeImageQuality,
  uploadAndProcessScan,
  extractDeclarations,
  updateDeclaration,
  listDemoSamples,
  fetchDemoSampleFile,
  seedDemoSamples,
} from '../services/api';
import {
  DeclarationItem,
  DemoSampleInfo,
  ImageQualityMetrics,
  OCRProcessResponse,
  ScanDeclarationsResponse,
} from '../types';

export const ProductScanner: React.FC = () => {
  const [selectedPanel, setSelectedPanel] = useState('principal');
  const [selectedEngine, setSelectedEngine] = useState('auto');
  const [selectedLanguage, setSelectedLanguage] = useState('en');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [naturalDimensions, setNaturalDimensions] = useState<{ width: number; height: number }>({
    width: 0,
    height: 0,
  });

  const [isQualityAnalyzing, setIsQualityAnalyzing] = useState(false);
  const [qualityMetrics, setQualityMetrics] = useState<ImageQualityMetrics | null>(null);

  const [isProcessingOcr, setIsProcessingOcr] = useState(false);
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRProcessResponse | null>(null);
  const [activeRegionIndex, setActiveRegionIndex] = useState<number | null>(null);
  const [hoveredRegionIndex, setHoveredRegionIndex] = useState<number | null>(null);

  // Phase 4 Declaration Extraction State
  const [isExtractingDeclarations, setIsExtractingDeclarations] = useState(false);
  const [declarationsResponse, setDeclarationsResponse] = useState<ScanDeclarationsResponse | null>(null);
  const [selectedDeclarationId, setSelectedDeclarationId] = useState<string | null>(null);

  // Phase 8 Demo Samples State
  const [demoSamples, setDemoSamples] = useState<DemoSampleInfo[]>([]);
  const [isLoadingSample, setIsLoadingSample] = useState<string | null>(null);
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);
  const [seedSuccessMsg, setSeedSuccessMsg] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'declarations' | 'regions' | 'raw'>('declarations');
  const [copiedText, setCopiedText] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageElementRef = useRef<HTMLImageElement>(null);
  const regionListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load demo samples metadata on mount
    listDemoSamples()
      .then((data) => setDemoSamples(data))
      .catch((err) => console.warn('Could not load demo samples list:', err));
  }, []);

  const panels = [
    { id: 'principal', name: 'Principal Display Panel (PDP)' },
    { id: 'back', name: 'Back / Declaration Panel' },
    { id: 'side', name: 'Side Flanges / Batch Info' },
    { id: 'bottom', name: 'Base / MRP Stamp' },
  ];

  const engines = [
    { id: 'auto', name: 'Auto (Recommended)' },
    { id: 'mock', name: 'Mock OCR (Deterministic CI/Demo)' },
    { id: 'tesseract', name: 'Tesseract OCR' },
    { id: 'paddleocr', name: 'PaddleOCR (PP-OCRv4)' },
  ];

  const handleFileChange = async (file: File) => {
    setSelectedFile(file);
    setErrorMessage(null);
    setOcrResult(null);
    setCurrentScanId(null);
    setDeclarationsResponse(null);
    setSelectedDeclarationId(null);
    setActiveRegionIndex(null);

    const url = URL.createObjectURL(file);
    setImagePreviewUrl(url);

    // Run Pre-flight image quality check
    setIsQualityAnalyzing(true);
    try {
      const quality = await analyzeImageQuality(file);
      setQualityMetrics(quality);
    } catch (err: any) {
      console.warn('Pre-flight quality check warning:', err);
    } finally {
      setIsQualityAnalyzing(false);
    }
  };

    const handleLoadDemoSample = async (sample: DemoSampleInfo) => {
    setIsLoadingSample(sample.id);
    setErrorMessage(null);
    try {
      const ext = sample.id === 'sample_e' ? 'jpg' : 'png';
      const file = await fetchDemoSampleFile(sample.id, `${sample.id}_${sample.brand.toLowerCase().replace(/\s+/g, '_')}.${ext}`);
      await handleFileChange(file);
    } catch (err: any) {
      setErrorMessage(`Failed to load demo sample ${sample.name}: ${err.message}`);
    } finally {
      setIsLoadingSample(null);
    }
  };

  const handleSeedAllDemo = async () => {
    setIsSeedingDemo(true);
    setErrorMessage(null);
    setSeedSuccessMsg(null);
    try {
      const res = await seedDemoSamples();
      setSeedSuccessMsg(res.message);
      setTimeout(() => setSeedSuccessMsg(null), 6000);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to seed demo samples.');
    } finally {
      setIsSeedingDemo(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileChange(file);
    }
  };

  const handleRunOcr = async () => {
    if (!selectedFile) {
      setErrorMessage('Please select or drop an image file first.');
      return;
    }

    setIsProcessingOcr(true);
    setErrorMessage(null);
    try {
      const response = await uploadAndProcessScan(selectedFile, {
        engine: selectedEngine,
        language: selectedLanguage,
      });
      setCurrentScanId(response.scan_id);
      setOcrResult(response.ocr_result);
      if (response.ocr_result.quality_metrics) {
        setQualityMetrics(response.ocr_result.quality_metrics);
      }

      // Automatically trigger declaration extraction on scan completion
      handleRunDeclarationExtraction(response.scan_id);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err.message || 'OCR processing failed.';
      setErrorMessage(detail);
    } finally {
      setIsProcessingOcr(false);
    }
  };

  const handleRunDeclarationExtraction = async (scanIdToUse?: string) => {
    const targetScanId = scanIdToUse || currentScanId;
    if (!targetScanId) {
      setErrorMessage('Please run OCR on a scan before extracting declarations.');
      return;
    }

    setIsExtractingDeclarations(true);
    setErrorMessage(null);
    try {
      const declResponse = await extractDeclarations(targetScanId);
      setDeclarationsResponse(declResponse);
      setActiveTab('declarations');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err.message || 'Declaration extraction failed.';
      setErrorMessage(detail);
    } finally {
      setIsExtractingDeclarations(false);
    }
  };

  const handleUpdateDeclaration = async (
    declarationId: string,
    updated: Partial<DeclarationItem>,
    notes?: string
  ) => {
    try {
      const updatedItem = await updateDeclaration(declarationId, {
        normalized_value: updated.normalized_value,
        extraction_status: updated.extraction_status,
        notes: notes,
      });

      // Update local state
      if (declarationsResponse) {
        setDeclarationsResponse({
          ...declarationsResponse,
          declarations: declarationsResponse.declarations.map((d) =>
            d.id === declarationId ? updatedItem : d
          ),
        });
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err.message || 'Failed to update declaration.';
      setErrorMessage(detail);
      throw err;
    }
  };

  const handleCopyRawText = () => {
    if (!ocrResult?.full_text) return;
    navigator.clipboard.writeText(ocrResult.full_text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  // Keep selected region in view
  useEffect(() => {
    if (activeRegionIndex !== null && regionListRef.current) {
      const targetElement = document.getElementById(`region-item-${activeRegionIndex}`);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [activeRegionIndex]);

  // Find active declaration bbox if any
  const selectedDeclaration = declarationsResponse?.declarations.find(
    (d) => d.id === selectedDeclarationId
  );
  const selectedDeclarationBbox = selectedDeclaration?.bounding_box;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header & Title */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Commodity Label Optical Character Recognition & Declarations
            </h1>
            <Badge variant="info">Phase 4 Normalization</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Standardized optical text extraction, Legal Metrology declaration structuring, spatial bounding coordinate mapping, and evidence verification.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {imagePreviewUrl && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={() => {
                setSelectedFile(null);
                setImagePreviewUrl(null);
                setOcrResult(null);
                setCurrentScanId(null);
                setDeclarationsResponse(null);
                setSelectedDeclarationId(null);
                setQualityMetrics(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
            >
              Reset Scanner
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-300">Processing Error</p>
            <p className="mt-0.5 opacity-90">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Configuration Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
        {/* Panel Type */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-metagov-400" />
            Packaging Display Panel
          </label>
          <select
            value={selectedPanel}
            onChange={(e) => setSelectedPanel(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-metagov-500 focus:outline-none"
          >
            {panels.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* OCR Engine */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-metagov-400" />
            OCR Engine Provider
          </label>
          <select
            value={selectedEngine}
            onChange={(e) => setSelectedEngine(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-metagov-500 focus:outline-none"
          >
            {engines.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </div>

        {/* Language */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">
            Target OCR Language
          </label>
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-metagov-500 focus:outline-none"
          >
            <option value="en">English (en / eng)</option>
            <option value="hi">Hindi (hi / hin)</option>
          </select>
        </div>
      </div>

      {/* SIH Demonstration Controlled Test Scenarios */}
      {demoSamples.length > 0 && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-metagov-950/40 border border-metagov-800/40 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-metagov-400 shrink-0" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Controlled Demonstration Scenarios (Demo / Simulation)
                </h3>
                <Badge variant="warning">Simulation Suite</Badge>
              </div>
              <p className="text-[11px] text-slate-400">
                Pre-configured evaluation samples for demonstration testing. Not independently validated commercial products.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              isLoading={isSeedingDemo}
              leftIcon={<Zap className="w-3.5 h-3.5 text-amber-400" />}
              onClick={handleSeedAllDemo}
            >
              Seed Controlled Demo Inspections
            </Button>
          </div>

          {seedSuccessMsg && (
            <div className="p-2.5 rounded-lg bg-emerald-950/70 border border-emerald-800 text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{seedSuccessMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {demoSamples.map((sample) => (
              <button
                key={sample.id}
                onClick={() => handleLoadDemoSample(sample)}
                disabled={isLoadingSample !== null}
                className="text-left p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-metagov-500/80 hover:bg-slate-900 transition-all flex flex-col justify-between group disabled:opacity-50"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-metagov-400 font-semibold uppercase">
                      {sample.id.replace('_', ' ')}
                    </span>
                    <Badge
                      size="sm"
                      variant={
                        sample.expected_outcome === 'COMPLIANT'
                          ? 'success'
                          : sample.expected_outcome === 'REVIEW_REQUIRED'
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      {sample.expected_outcome === 'COMPLIANT'
                        ? 'Pass'
                        : sample.expected_outcome === 'REVIEW_REQUIRED'
                        ? 'Review'
                        : 'Violation'}
                    </Badge>
                  </div>
                  <p className="text-xs font-semibold text-white group-hover:text-metagov-300 transition-colors line-clamp-1">
                    {sample.brand}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2 leading-tight">
                    {sample.description}
                  </p>
                </div>
                <span className="text-[10px] text-metagov-400 mt-2 font-medium group-hover:underline flex items-center gap-1">
                  {isLoadingSample === sample.id ? (
                    'Loading sample...'
                  ) : (
                    <>
                      <span>Load Label</span> &rarr;
                    </>
                  )}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Split-Screen Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Upload / Image Canvas (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card title="Package Imagery & Spatial Bounding Overlay" className="overflow-hidden">
            {!imagePreviewUrl ? (
              /* Drag & Drop Upload State */
              <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700/80 rounded-2xl p-10 text-center bg-slate-950/40 hover:bg-slate-900/40 hover:border-metagov-500/60 transition-all flex flex-col items-center justify-center min-h-[340px] cursor-pointer"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  accept="image/jpeg,image/png,image/webp,image/tiff,image/bmp"
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
                <div className="w-16 h-16 rounded-2xl bg-metagov-600/10 border border-metagov-500/20 text-metagov-400 flex items-center justify-center mb-4 shadow-inner">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <h3 className="text-base font-semibold text-white">
                  Drag & drop package label image
                </h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm">
                  Upload high-resolution label imagery (JPEG, PNG, WebP) for Legal Metrology text extraction
                </p>

                <div className="flex items-center gap-3 mt-6">
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={<FileImage className="w-4 h-4" />}
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    Select File from Device
                  </Button>
                </div>
              </div>
            ) : (
              /* Image Canvas with Spatial Bounding Box Overlay */
              <div className="space-y-4">
                <div className="relative w-full overflow-hidden bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center min-h-[380px] max-h-[550px]">
                  <img
                    ref={imageElementRef}
                    src={imagePreviewUrl}
                    alt="Package Label"
                    className="max-w-full max-h-[520px] object-contain select-none"
                    onLoad={(e) => {
                      const img = e.currentTarget;
                      setNaturalDimensions({
                        width: img.naturalWidth,
                        height: img.naturalHeight,
                      });
                    }}
                  />

                  {/* SVG Bounding Box Coordinate Overlay */}
                  {ocrResult && naturalDimensions.width > 0 && (
                    <svg
                      viewBox={`0 0 ${naturalDimensions.width} ${naturalDimensions.height}`}
                      className="absolute inset-0 w-full h-full pointer-events-none"
                    >
                      {/* OCR Regions Bounding Boxes */}
                      {ocrResult.regions.map((region, idx) => {
                        const isSelected = activeRegionIndex === idx;
                        const isHovered = hoveredRegionIndex === idx;
                        const { x1, y1, x2, y2 } = region.bbox;
                        const width = Math.max(2, x2 - x1);
                        const height = Math.max(2, y2 - y1);

                        let strokeColor = '#0284c7'; // default cyan
                        let fillColor = 'rgba(2, 132, 199, 0.15)';
                        if (region.confidence < 0.75) {
                          strokeColor = '#f59e0b';
                          fillColor = 'rgba(245, 158, 11, 0.15)';
                        }
                        if (isSelected || isHovered) {
                          strokeColor = '#38bdf8';
                          fillColor = 'rgba(56, 189, 248, 0.35)';
                        }

                        return (
                          <g key={`ocr-${idx}`}>
                            <rect
                              x={x1}
                              y={y1}
                              width={width}
                              height={height}
                              fill={fillColor}
                              stroke={strokeColor}
                              strokeWidth={isSelected || isHovered ? 4 : 2}
                              rx={4}
                              className="pointer-events-auto cursor-pointer transition-all"
                              onClick={() => {
                                setActiveRegionIndex(idx);
                                setActiveTab('regions');
                              }}
                              onMouseEnter={() => setHoveredRegionIndex(idx)}
                              onMouseLeave={() => setHoveredRegionIndex(null)}
                            />
                            {(isSelected || isHovered) && (
                              <text
                                x={x1}
                                y={Math.max(16, y1 - 4)}
                                fill="#ffffff"
                                fontSize={Math.max(14, naturalDimensions.width * 0.02)}
                                fontWeight="bold"
                                filter="drop-shadow(0px 1px 2px rgba(0,0,0,0.8))"
                              >
                                #{idx + 1} ({Math.round(region.confidence * 100)}%)
                              </text>
                            )}
                          </g>
                        );
                      })}

                      {/* Declaration Selected Highlight Box */}
                      {selectedDeclarationBbox &&
                        selectedDeclarationBbox.x1 !== undefined && (
                          <g key="decl-active">
                            <rect
                              x={selectedDeclarationBbox.x1}
                              y={selectedDeclarationBbox.y1}
                              width={Math.max(
                                4,
                                selectedDeclarationBbox.x2 - selectedDeclarationBbox.x1
                              )}
                              height={Math.max(
                                4,
                                selectedDeclarationBbox.y2 - selectedDeclarationBbox.y1
                              )}
                              fill="rgba(16, 185, 129, 0.25)"
                              stroke="#10b981"
                              strokeWidth={4}
                              rx={6}
                              strokeDasharray="4 2"
                            />
                            <text
                              x={selectedDeclarationBbox.x1}
                              y={Math.max(20, selectedDeclarationBbox.y1 - 6)}
                              fill="#10b981"
                              fontSize={Math.max(14, naturalDimensions.width * 0.022)}
                              fontWeight="bold"
                              filter="drop-shadow(0px 1px 3px rgba(0,0,0,0.9))"
                            >
                              ✓ {selectedDeclaration?.declaration_type}
                            </text>
                          </g>
                        )}
                    </svg>
                  )}
                </div>

                {/* Extraction Button Trigger */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="text-xs text-slate-400">
                    Image: <span className="text-slate-200 font-mono">{selectedFile?.name}</span>{' '}
                    {naturalDimensions.width > 0 && (
                      <span className="text-slate-500">
                        ({naturalDimensions.width}x{naturalDimensions.height}px)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {currentScanId && (
                      <Button
                        variant="secondary"
                        size="md"
                        isLoading={isExtractingDeclarations}
                        leftIcon={<FileCheck className="w-4 h-4" />}
                        onClick={() => handleRunDeclarationExtraction()}
                      >
                        Extract Declarations
                      </Button>
                    )}

                    <Button
                      variant="primary"
                      size="md"
                      isLoading={isProcessingOcr}
                      leftIcon={<Sparkles className="w-4 h-4" />}
                      onClick={handleRunOcr}
                    >
                      {ocrResult ? 'Re-run Scan & OCR' : 'Extract Label Text (Run OCR)'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Pre-Flight Quality Metrics Panel */}
          {(qualityMetrics || isQualityAnalyzing) && (
            <Card
              title="Image Quality & Resolution Analytics"
              subtitle={isQualityAnalyzing ? 'Analyzing sharpness, contrast, and resolution...' : undefined}
              className="border-slate-800"
            >
              {isQualityAnalyzing ? (
                <div className="p-4 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-metagov-500 border-t-transparent rounded-full animate-spin" />
                  <span>Computing computer vision quality metrics...</span>
                </div>
              ) : qualityMetrics ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-3">
                    <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                      <span className="text-slate-400 block text-[11px]">Sharpness Score</span>
                      <span className="text-base font-bold text-white">
                        {qualityMetrics.sharpness_score.toFixed(1)}
                      </span>
                      <span className="text-[10px] text-slate-500 block">
                        {qualityMetrics.is_blurry ? '⚠️ Blurry' : '✓ Sharp'}
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                      <span className="text-slate-400 block text-[11px]">Luminance Mean</span>
                      <span className="text-base font-bold text-white">
                        {qualityMetrics.brightness_mean.toFixed(1)}
                        <span className="text-xs text-slate-500">/255</span>
                      </span>
                      <span className="text-[10px] text-slate-500 block">
                        {qualityMetrics.is_too_dark
                          ? '⚠️ Dark'
                          : qualityMetrics.is_too_bright
                          ? '⚠️ Bright'
                          : '✓ Balanced'}
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                      <span className="text-slate-400 block text-[11px]">Contrast Std</span>
                      <span className="text-base font-bold text-white">
                        {qualityMetrics.contrast_score.toFixed(1)}
                      </span>
                      <span className="text-[10px] text-slate-500 block">
                        {qualityMetrics.is_low_contrast ? '⚠️ Low' : '✓ Good'}
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800">
                      <span className="text-slate-400 block text-[11px]">Quality Rating</span>
                      <span className="text-base font-bold text-metagov-400">
                        {qualityMetrics.quality_score.toFixed(0)}
                        <span className="text-xs text-slate-500">/100</span>
                      </span>
                      <span className="text-[10px] text-slate-500 block">
                        {qualityMetrics.is_low_resolution ? '⚠️ Low Res' : '✓ Adequate'}
                      </span>
                    </div>
                  </div>

                  {/* Advisory Warnings */}
                  {qualityMetrics.warnings && qualityMetrics.warnings.length > 0 ? (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 space-y-1">
                      <div className="font-semibold flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span>Advisory Quality Indicators</span>
                      </div>
                      <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-300/90">
                        {qualityMetrics.warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                      <p className="text-[10px] text-amber-400/70 pt-1">
                        * Quality warnings are advisory indicators and do not invalidate inspection intake.
                      </p>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Image meets clarity, contrast, and resolution standards for legal inspection.</span>
                    </div>
                  )}
                </>
              ) : null}
            </Card>
          )}
        </div>

        {/* Right Column: Declarations Review & OCR Text (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card
            title="Legal Metrology Extraction Workspace"
            className="flex flex-col h-full min-h-[480px]"
            subtitle={
              declarationsResponse
                ? `${declarationsResponse.total_declarations} declarations structured • ${(
                    declarationsResponse.mean_confidence * 100
                  ).toFixed(0)}% mean conf`
                : ocrResult
                ? `Engine: ${ocrResult.ocr_engine} • ${ocrResult.regions.length} detected blocks`
                : 'Run extraction to inspect recognized text'
            }
          >
            {ocrResult ? (
              <div className="space-y-4 flex-1 flex flex-col">
                {/* Stats Header */}
                <div className="flex items-center justify-between p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[11px]">OCR Mean Confidence</span>
                    <span className="font-bold text-metagov-400 font-mono text-sm">
                      {(ocrResult.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Execution Time</span>
                    <span className="font-mono text-slate-200 text-xs">
                      {ocrResult.processing_time_ms.toFixed(0)} ms
                    </span>
                  </div>
                  <div>
                    <Badge variant={ocrResult.confidence_score > 0.85 ? 'success' : 'warning'}>
                      {ocrResult.status}
                    </Badge>
                  </div>
                </div>

                {/* View Tabs */}
                <div className="flex border-b border-slate-800 overflow-x-auto">
                  <button
                    onClick={() => setActiveTab('declarations')}
                    className={`px-4 py-2 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                      activeTab === 'declarations'
                        ? 'border-metagov-500 text-metagov-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Legal Declarations ({declarationsResponse?.total_declarations || 0})
                  </button>
                  <button
                    onClick={() => setActiveTab('regions')}
                    className={`px-4 py-2 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                      activeTab === 'regions'
                        ? 'border-metagov-500 text-metagov-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Spatial Regions ({ocrResult.regions.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('raw')}
                    className={`px-4 py-2 text-xs font-medium border-b-2 whitespace-nowrap transition-colors ${
                      activeTab === 'raw'
                        ? 'border-metagov-500 text-metagov-400'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Full Raw Text
                  </button>
                </div>

                {/* Tab 1: Legal Declarations Table */}
                {activeTab === 'declarations' && (
                  <div className="flex-1 flex flex-col">
                    {isExtractingDeclarations ? (
                      <div className="p-8 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-3">
                        <div className="w-6 h-6 border-2 border-metagov-500 border-t-transparent rounded-full animate-spin" />
                        <span>Extracting & Normalizing Legal Metrology Declarations...</span>
                      </div>
                    ) : declarationsResponse && declarationsResponse.declarations.length > 0 ? (
                      <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
                        <DeclarationReviewTable
                          declarations={declarationsResponse.declarations}
                          meanConfidence={declarationsResponse.mean_confidence}
                          selectedDeclarationId={selectedDeclarationId}
                          onSelectDeclaration={(decl) => {
                            setSelectedDeclarationId(decl.id);
                          }}
                          onUpdateDeclaration={handleUpdateDeclaration}
                        />
                      </div>
                    ) : (
                      <div className="p-8 text-center text-slate-500 space-y-3 bg-slate-950/40 rounded-xl border border-slate-800">
                        <FileCheck className="w-10 h-10 mx-auto text-slate-600" />
                        <p className="text-xs">
                          Click <strong>Extract Declarations</strong> to identify and structure legal packaging declarations.
                        </p>
                        <Button
                          variant="secondary"
                          size="sm"
                          leftIcon={<Sparkles className="w-3.5 h-3.5" />}
                          onClick={() => handleRunDeclarationExtraction()}
                        >
                          Run Extraction
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Spatial Regions List */}
                {activeTab === 'regions' && (
                  <div
                    ref={regionListRef}
                    className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1 flex-1 text-xs"
                  >
                    {ocrResult.regions.map((region, idx) => {
                      const isSelected = activeRegionIndex === idx;
                      const isHovered = hoveredRegionIndex === idx;

                      return (
                        <div
                          key={idx}
                          id={`region-item-${idx}`}
                          onClick={() => setActiveRegionIndex(idx)}
                          onMouseEnter={() => setHoveredRegionIndex(idx)}
                          onMouseLeave={() => setHoveredRegionIndex(null)}
                          className={`p-3 rounded-xl border transition-all cursor-pointer ${
                            isSelected || isHovered
                              ? 'bg-metagov-600/20 border-metagov-500 shadow-md ring-1 ring-metagov-500/50'
                              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="font-mono text-[11px] font-semibold text-metagov-400">
                              Block #{idx + 1}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[10px] text-slate-500">
                                [{region.bbox.x1},{region.bbox.y1}] → [{region.bbox.x2},
                                {region.bbox.y2}]
                              </span>
                              <Badge
                                size="sm"
                                variant={
                                  region.confidence >= 0.9
                                    ? 'success'
                                    : region.confidence >= 0.75
                                    ? 'warning'
                                    : 'danger'
                                }
                              >
                                {Math.round(region.confidence * 100)}%
                              </Badge>
                            </div>
                          </div>

                          <p className="font-mono text-slate-200 text-xs leading-relaxed bg-slate-900/60 p-2 rounded border border-slate-800/80">
                            {region.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Tab 3: Raw Text Stream */}
                {activeTab === 'raw' && (
                  <div className="space-y-2 flex-1 flex flex-col">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-slate-400">Full Text Buffer</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        leftIcon={copiedText ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        onClick={handleCopyRawText}
                      >
                        {copiedText ? 'Copied' : 'Copy All'}
                      </Button>
                    </div>
                    <textarea
                      readOnly
                      value={ocrResult.full_text}
                      rows={14}
                      className="w-full flex-1 bg-slate-950 font-mono text-xs text-slate-200 p-3 rounded-xl border border-slate-800 focus:outline-none resize-none"
                    />
                  </div>
                )}
              </div>
            ) : (
              /* Empty Placeholder */
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-3">
                <FileImage className="w-12 h-12 stroke-[1.2] text-slate-600" />
                <p className="text-xs max-w-xs">
                  Upload an image on the left canvas and click <strong>Extract Label Text</strong> to initiate optical character extraction.
                </p>
              </div>
            )}
          </Card>

          {/* Statutory Disclaimer Banner */}
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-300">
              <ShieldAlert className="w-3.5 h-3.5 text-metagov-400 shrink-0" />
              <span>Statutory Legal Metrology Notice</span>
            </div>
            <p className="leading-relaxed text-slate-400">
              Declaration extraction is an automated evidence extraction process. It identifies packaged commodity declarations and does not constitute a legal compliance determination.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

