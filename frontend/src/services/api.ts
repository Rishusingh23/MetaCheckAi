import axios from 'axios';
import {
  DeclarationItem,
  DeclarationUpdatePayload,
  HealthStatus,
  ImageQualityMetrics,
  InspectionComplianceResponse,
  OCRProcessResponse,
  PaginatedResult,
  ProductDossier,
  ProductRepositoryItem,
  RuleItem,
  RuleVersion,
  ScanDeclarationsResponse,
  ScanUploadAndProcessResponse,
  TokenResponse,
  UserAuth,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor: inject JWT Bearer Token if present
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('metacheck_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: log error & handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && window.location.pathname !== '/login') {
      console.warn('Session expired or unauthorized. Redirecting to login.');
    }
    return Promise.reject(error);
  }
);

// ==========================================
// AUTHENTICATION SERVICES
// ==========================================

export const loginUser = async (email: string, password: string): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', {
    email,
    password,
  });
  return response.data;
};

export const getCurrentUser = async (): Promise<UserAuth> => {
  const response = await apiClient.get<UserAuth>('/api/v1/auth/me');
  return response.data;
};

export const logoutUser = async (): Promise<{ message: string; success: boolean }> => {
  const response = await apiClient.post<{ message: string; success: boolean }>('/api/v1/auth/logout');
  return response.data;
};

// ==========================================
// HEALTH & OBSERVABILITY
// ==========================================

export const checkBackendHealth = async (): Promise<HealthStatus> => {
  const response = await apiClient.get<HealthStatus>('/api/v1/health');
  return response.data;
};

// ==========================================
// OCR & COMPUTER VISION PIPELINE
// ==========================================

export const uploadAndProcessScan = async (
  file: File,
  options?: {
    engine?: string;
    language?: string;
    inspectionId?: string;
    productId?: string;
  }
): Promise<ScanUploadAndProcessResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  if (options?.engine) formData.append('engine_name', options.engine);
  if (options?.language) formData.append('language', options.language);
  if (options?.inspectionId) formData.append('inspection_id', options.inspectionId);
  if (options?.productId) formData.append('product_id', options.productId);

  const response = await apiClient.post<ScanUploadAndProcessResponse>(
    '/api/v1/scans/upload-and-process',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

export const analyzeImageQuality = async (file: File): Promise<ImageQualityMetrics> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ImageQualityMetrics>(
    '/api/v1/images/analyze-quality',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

export const getScanOcrResult = async (scanId: string): Promise<OCRProcessResponse> => {
  const response = await apiClient.get<OCRProcessResponse>(`/api/v1/scans/${scanId}/ocr`);
  return response.data;
};

// ==========================================
// DECLARATIONS & NORMALIZATION
// ==========================================

export const extractDeclarations = async (scanId: string): Promise<ScanDeclarationsResponse> => {
  const response = await apiClient.post<ScanDeclarationsResponse>(
    `/api/v1/scans/${scanId}/extract-declarations`
  );
  return response.data;
};

export const getScanDeclarations = async (scanId: string): Promise<ScanDeclarationsResponse> => {
  const response = await apiClient.get<ScanDeclarationsResponse>(
    `/api/v1/scans/${scanId}/declarations`
  );
  return response.data;
};

export const updateDeclaration = async (
  declarationId: string,
  payload: DeclarationUpdatePayload
): Promise<DeclarationItem> => {
  const response = await apiClient.patch<DeclarationItem>(
    `/api/v1/declarations/${declarationId}`,
    payload
  );
  return response.data;
};

// ==========================================
// COMPLIANCE EVALUATION & RULE ENGINE
// ==========================================

export const evaluateInspectionCompliance = async (
  inspectionId: string,
  options?: { notes?: string; userId?: string }
): Promise<InspectionComplianceResponse> => {
  const response = await apiClient.post<InspectionComplianceResponse>(
    `/api/v1/inspections/${inspectionId}/evaluate`,
    {
      notes: options?.notes,
      user_id: options?.userId,
    }
  );
  return response.data;
};

export const getInspectionCompliance = async (
  inspectionId: string
): Promise<InspectionComplianceResponse> => {
  const response = await apiClient.get<InspectionComplianceResponse>(
    `/api/v1/inspections/${inspectionId}/compliance`
  );
  return response.data;
};

// ==========================================
// STATUTORY RULES & VERSIONING
// ==========================================

export const getRules = async (params?: { is_active?: boolean; skip?: number; limit?: number }): Promise<PaginatedResult<RuleItem>> => {
  const response = await apiClient.get<PaginatedResult<RuleItem>>('/api/v1/rules', { params });
  return response.data;
};

export const getRuleDetails = async (ruleId: string): Promise<RuleItem> => {
  const response = await apiClient.get<RuleItem>(`/api/v1/rules/${ruleId}`);
  return response.data;
};

export const seedRuleBaseline = async (): Promise<{ message: string; seeded_count?: number }> => {
  const response = await apiClient.post<{ message: string; seeded_count?: number }>('/api/v1/rules/seed-baseline');
  return response.data;
};

export const updateRule = async (
  ruleId: string,
  payload: { is_active?: boolean; name?: string; description?: string; legal_reference?: string }
): Promise<RuleItem> => {
  const response = await apiClient.put<RuleItem>(`/api/v1/rules/${ruleId}`, payload);
  return response.data;
};

export const publishRuleVersion = async (
  ruleId: string,
  versionData: {
    version: string;
    requirement_text: string;
    validation_type: string;
    severity: string;
    conditions?: Record<string, any>;
    source_gazette_reference?: string;
    active_from?: string;
    active_to?: string;
  }
): Promise<RuleVersion> => {
  const response = await apiClient.post<RuleVersion>(`/api/v1/rules/${ruleId}/versions`, versionData);
  return response.data;
};

// ==========================================
// PRODUCT REPOSITORY & DOSSIER
// ==========================================

export const listProducts = async (params?: {
  skip?: number;
  limit?: number;
  search?: string;
  category?: string;
  brand?: string;
  manufacturer?: string;
  barcode_gtin?: string;
}): Promise<PaginatedResult<ProductRepositoryItem>> => {
  const response = await apiClient.get<PaginatedResult<ProductRepositoryItem>>('/api/v1/products', {
    params,
  });
  return response.data;
};

export const getProductDossier = async (productId: string): Promise<ProductDossier> => {
  const response = await apiClient.get<ProductDossier>(`/api/v1/products/${productId}/dossier`);
  return response.data;
};

// ==========================================
// INSPECTION HISTORY & WORKFLOW
// ==========================================

export const listInspections = async (params?: {
  skip?: number;
  limit?: number;
  search?: string;
  category?: string;
  status?: string;
  overall_result?: string;
  inspector_id?: string;
  product_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<PaginatedResult<any>> => {
  const response = await apiClient.get<PaginatedResult<any>>('/api/v1/inspections', {
    params,
  });
  return response.data;
};

export const getInspectionDetails = async (inspectionId: string): Promise<any> => {
  const response = await apiClient.get(`/api/v1/inspections/${inspectionId}`);
  return response.data;
};

export const updateInspectionStatus = async (
  inspectionId: string,
  payload: { status: string; notes?: string; user_id?: string }
): Promise<any> => {
  const response = await apiClient.patch(`/api/v1/inspections/${inspectionId}/status`, payload);
  return response.data;
};

export const getInspectionViolations = async (
  inspectionId: string
): Promise<import('../types').ViolationItem[]> => {
  const response = await apiClient.get<import('../types').ViolationItem[]>(
    `/api/v1/inspections/${inspectionId}/violations`
  );
  return response.data;
};

export const getInspectionHistory = async (
  inspectionId: string
): Promise<import('../types').InspectionHistoryItem[]> => {
  const response = await apiClient.get<import('../types').InspectionHistoryItem[]>(
    `/api/v1/inspections/${inspectionId}/history`
  );
  return response.data;
};

// ==========================================
// VIOLATION MANAGEMENT & REVIEW
// ==========================================

export const reviewViolation = async (
  violationId: string,
  payload: import('../types').ViolationReviewPayload
): Promise<import('../types').ViolationItem> => {
  const response = await apiClient.patch<import('../types').ViolationItem>(
    `/api/v1/violations/${violationId}/review`,
    payload
  );
  return response.data;
};

// ==========================================
// REPORTS & DASHBOARD
// ==========================================

export const getDashboardSummary = async (params?: {
  category?: string;
  start_date?: string;
  end_date?: string;
}): Promise<import('../types').DashboardSummary> => {
  const response = await apiClient.get<import('../types').DashboardSummary>('/api/v1/dashboard/summary', { params });
  return response.data;
};

export const generateInspectionReport = async (
  inspectionId: string,
  format: 'PDF' | 'JSON' | 'CSV' = 'PDF',
  reportType: string = 'INSPECTION_SUMMARY'
): Promise<import('../types').ReportItem> => {
  const response = await apiClient.post<import('../types').ReportItem>(
    `/api/v1/reports/inspections/${inspectionId}/generate`,
    null,
    {
      params: { format, report_type: reportType },
    }
  );
  return response.data;
};

export const listReports = async (params?: {
  skip?: number;
  limit?: number;
  inspection_id?: string;
  format?: string;
}): Promise<PaginatedResult<import('../types').ReportItem>> => {
  const response = await apiClient.get<PaginatedResult<import('../types').ReportItem>>(
    '/api/v1/reports',
    { params }
  );
  return response.data;
};

export const listInspectionReports = async (inspectionId: string): Promise<import('../types').ReportItem[]> => {
  const result = await listReports({ inspection_id: inspectionId, limit: 100 });
  return result.items || [];
};


export const downloadReportBlob = async (reportId: string, filename: string): Promise<void> => {
  const response = await apiClient.get(`/api/v1/reports/${reportId}/download`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const getReportDownloadUrl = (reportId: string): string => {
  return `${API_BASE_URL}/api/v1/reports/${reportId}/download`;
};

// ==========================================
// DEMO & CONTROLLED SAMPLES
// ==========================================

export const listDemoSamples = async (): Promise<import('../types').DemoSampleInfo[]> => {
  const response = await apiClient.get<import('../types').DemoSampleInfo[]>('/api/v1/demo/samples');
  return response.data;
};

export const getDemoSampleImageUrl = (sampleId: string): string => {
  return `${API_BASE_URL}/api/v1/demo/samples/${sampleId}/image`;
};

export const fetchDemoSampleFile = async (sampleId: string, filename: string): Promise<File> => {
  const response = await apiClient.get(`/api/v1/demo/samples/${sampleId}/image`, {
    responseType: 'blob',
  });
  const mimeType = sampleId === 'sample_e' ? 'image/jpeg' : 'image/png';
  return new File([response.data], filename, { type: mimeType });
};

export const seedDemoSamples = async (): Promise<{ message: string; records: any[] }> => {
  const response = await apiClient.post<{ message: string; records: any[] }>('/api/v1/demo/seed-samples');
  return response.data;
};

export default apiClient;

