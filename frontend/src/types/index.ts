export interface HealthStatus {
  status: string;
  project_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database_connected: boolean;
  services?: Record<string, string>;
}

export interface NavItem {
  name: string;
  path: string;
  icon: string;
  badge?: string;
  category?: 'core' | 'records' | 'admin';
}

export type ComplianceStatus = 'COMPLIANT' | 'POTENTIAL_NON_COMPLIANCE' | 'PENDING_VERIFICATION';

export interface InspectionSummary {
  id: string;
  productName: string;
  brand: string;
  category: string;
  inspectionDate: string;
  status: ComplianceStatus;
  declarationsFound: number;
  totalDeclarations: number;
  confidenceScore: number;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface OCRRegion {
  text: string;
  confidence: number;
  bbox: BoundingBox;
  polygon?: number[][];
  angle?: number;
  field_hint?: string;
}

export interface ImageQualityMetrics {
  sharpness_score: number;
  is_blurry: boolean;
  brightness_mean: number;
  is_too_dark: boolean;
  is_too_bright: boolean;
  contrast_score: number;
  is_low_contrast: boolean;
  width: number;
  height: number;
  is_low_resolution: boolean;
  quality_score: number;
  warnings: string[];
}

export interface OCRProcessResponse {
  scan_id: string;
  status: string;
  full_text: string;
  confidence_score: number;
  ocr_engine: string;
  engine_version: string;
  language: string;
  processing_time_ms: number;
  regions: OCRRegion[];
  quality_metrics: ImageQualityMetrics;
  disclaimer: string;
}

export interface ScanUploadAndProcessResponse {
  scan_id: string;
  inspection_id: string;
  image_id: string;
  image_url: string;
  ocr_result: OCRProcessResponse;
  disclaimer: string;
}

export type DeclarationType =
  | 'PRODUCT_NAME'
  | 'NET_QUANTITY'
  | 'MRP'
  | 'UNIT_SALE_PRICE'
  | 'DATE_OF_MANUFACTURE'
  | 'DATE_OF_PACKING'
  | 'MANUFACTURER_DETAILS'
  | 'PACKER_DETAILS'
  | 'IMPORTER_DETAILS'
  | 'COUNTRY_OF_ORIGIN'
  | 'CONSUMER_CARE'
  | 'GENERIC_NAME'
  | 'OTHER';

export type ExtractionStatus =
  | 'AUTO_EXTRACTED'
  | 'CONFIRMED'
  | 'REJECTED'
  | 'MANUALLY_EDITED'
  | 'AMBIGUOUS';

export interface DeclarationItem {
  id: string;
  scan_id: string;
  declaration_type: DeclarationType;
  raw_value: string;
  normalized_value?: string | null;
  confidence?: number | null;
  source_text?: string | null;
  bounding_box?: Record<string, any> | null;
  extraction_status: ExtractionStatus;
  created_at?: string | null;
}

export interface DeclarationUpdatePayload {
  normalized_value?: string | null;
  extraction_status?: ExtractionStatus | null;
  notes?: string | null;
}

export interface ScanDeclarationsResponse {
  scan_id: string;
  status: string;
  total_declarations: number;
  mean_confidence: number;
  declarations: DeclarationItem[];
  disclaimer: string;
}

export type ValidationType =
  | 'PRESENCE_CHECK'
  | 'FORMAT_CHECK'
  | 'NUMERIC_BOUNDS'
  | 'FONT_HEIGHT_RATIO'
  | 'TEXT_PATTERN';

export type Severity = 'CRITICAL' | 'MAJOR' | 'MINOR' | 'ADVISORY';

export interface RuleVersion {
  id: string;
  rule_id: string;
  version: string;
  requirement_text: string;
  validation_type: ValidationType;
  severity: Severity;
  conditions?: Record<string, any> | null;
  applicable_product_categories?: any;
  source_gazette_reference?: string | null;
  active_from?: string | null;
  active_to?: string | null;
  created_at?: string;
}

export interface RuleItem {
  id: string;
  rule_code: string;
  name: string;
  description?: string | null;
  legal_reference: string;
  is_active: boolean;
  versions?: RuleVersion[];
  created_at?: string;
  updated_at?: string;
}

export type ComplianceCheckStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'NOT_APPLICABLE';

export interface EvidenceItem {
  id: string;
  source_type: string;
  image_url_or_path?: string | null;
  bounding_box?: Record<string, any> | null;
  description?: string | null;
  confidence?: number | null;
}

export interface ViolationItem {
  id: string;
  violation_code: string;
  description?: string | null;
  severity: string;
  status: string;
  officer_comment?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  evidences?: EvidenceItem[];
}

export interface ViolationReviewPayload {
  status: 'OFFICER_CONFIRMED' | 'DISMISSED';
  comment: string;
}

export interface InspectionHistoryItem {
  id: string;
  action: string;
  previous_status?: string | null;
  new_status?: string | null;
  timestamp: string;
  user_name?: string | null;
  change_metadata?: Record<string, any> | null;
}

export interface ReportItem {
  id: string;
  inspection_id: string;
  report_type: string;
  format: 'PDF' | 'JSON' | 'CSV';
  file_path?: string | null;
  generated_by?: string | null;
  generated_at: string;
  created_at: string;
  status: string;
}

export interface CategoryStat {
  category: string;
  count: number;
}

export interface SeverityStat {
  severity: string;
  count: number;
}

export interface RuleViolationStat {
  rule_code: string;
  rule_name: string;
  count: number;
}

export interface InspectorWorkloadStat {
  inspector_id: string;
  inspector_name: string;
  inspections_count: number;
  pending_reviews: number;
}

export interface RecentInspectionSummary {
  id: string;
  product_name: string;
  brand: string;
  inspection_date: string;
  status: string;
  overall_result: string;
  violations_count: number;
  inspector_name: string;
}

export interface InspectionTrendPoint {
  date: string;
  total: number;
  compliant: number;
}

export interface DashboardSummary {
  total_inspections: number;
  inspections_today: number;
  completed_inspections: number;
  review_required: number;
  potential_non_compliance: number;
  officer_reviewed: number;
  flagged_violations: number;
  officer_confirmed_violations: number;
  dismissed_violations: number;
  compliance_rate: number;
  category_distribution: CategoryStat[];
  violations_by_severity: SeverityStat[];
  top_violated_rules: RuleViolationStat[];
  inspector_workload: InspectorWorkloadStat[];
  recent_inspections: RecentInspectionSummary[];
  inspection_trend: InspectionTrendPoint[];
}

export interface ComplianceCheckItem {
  id: string;
  inspection_id: string;
  rule_version_id: string;
  status: ComplianceCheckStatus;
  explanation?: string | null;
  detected_value?: string | null;
  expected_requirement?: string | null;
  confidence?: number | null;
  severity?: string | null;
  created_at?: string;
  rule_version?: RuleVersion | null;
  violations?: ViolationItem[];
}

export interface DemoSampleInfo {
  id: string;
  name: string;
  brand: string;
  category: string;
  expected_outcome: string;
  expected_violation?: string;
  description: string;
}

export interface InspectionComplianceResponse {
  inspection_id: string;
  overall_status: string;
  screening_score?: number;
  total_rules_evaluated: number;
  pass_count: number;
  fail_count: number;
  review_count: number;
  not_applicable_count: number;
  violations_flagged: number;
  mean_confidence: number;
  checks: ComplianceCheckItem[];
  disclaimer: string;
}

export interface UserAuth {
  id: string;
  name: string;
  email: string;
  role: 'ADMIN' | 'ENFORCEMENT_OFFICER' | 'VIEWER';
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserAuth;
}

export interface ProductRepositoryItem {
  id: string;
  name: string;
  brand: string;
  category: string;
  manufacturer?: string | null;
  packer?: string | null;
  importer?: string | null;
  barcode_gtin?: string | null;
  country_of_origin?: string | null;
  description?: string | null;
  created_at: string;
  updated_at: string;
  inspection_count: number;
  latest_inspection_id?: string | null;
  latest_inspection_status?: string | null;
  latest_compliance_result?: string | null;
  last_inspected_at?: string | null;
}

export interface ProductDossierInspectionItem {
  id: string;
  inspection_date: string;
  status: string;
  overall_result?: string | null;
  inspector_name?: string | null;
  violations_count: number;
}

export interface ProductDossierViolationItem {
  id: string;
  inspection_id: string;
  violation_code: string;
  description?: string | null;
  severity: string;
  status: string;
  created_at: string;
}

export interface ProductDossierReportItem {
  id: string;
  inspection_id: string;
  report_type: string;
  format: string;
  generated_at: string;
}

export interface ProductDossier {
  product: {
    id: string;
    name: string;
    brand: string;
    category: string;
    manufacturer?: string | null;
    packer?: string | null;
    importer?: string | null;
    barcode_gtin?: string | null;
    country_of_origin?: string | null;
    description?: string | null;
    created_at: string;
    updated_at: string;
    images: Array<{
      id: string;
      image_url_or_path: string;
      image_type: string;
      created_at: string;
    }>;
  };
  inspections: ProductDossierInspectionItem[];
  latest_inspection?: {
    id: string;
    inspection_date: string;
    status: string;
    overall_result?: string | null;
    inspector_name?: string | null;
    notes?: string | null;
  } | null;
  violations: ProductDossierViolationItem[];
  reports: ProductDossierReportItem[];
  audit_history: Array<{
    id: string;
    inspection_id?: string;
    action: string;
    previous_status?: string | null;
    new_status?: string | null;
    timestamp: string;
    user_name?: string | null;
    metadata?: Record<string, any> | null;
  }>;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

