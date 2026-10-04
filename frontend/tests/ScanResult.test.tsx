import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { ScanResult } from '../src/pages/ScanResult';
import * as api from '../src/services/api';

vi.mock('../src/services/api');

describe('ScanResult Component', () => {
  it('renders advisory screening banner, metric cards, violations, and statutory breakdown', async () => {
    vi.mocked(api.getInspectionCompliance).mockResolvedValue({
      inspection_id: 'insp-100',
      overall_status: 'POTENTIAL_NON_COMPLIANCE',
      total_rules_evaluated: 2,
      pass_count: 1,
      fail_count: 1,
      review_count: 0,
      not_applicable_count: 0,
      violations_flagged: 1,
      mean_confidence: 0.94,
      disclaimer: 'MetaCheck AI advisory screening disclaimer.',
      checks: [
        {
          id: 'chk-1',
          inspection_id: 'insp-100',
          rule_version_id: 'rv-1',
          status: 'PASS',
          explanation: 'Net quantity metric unit valid',
          detected_value: '500 g',
          expected_requirement: 'Net quantity in standard metric units.',
          confidence: 0.98,
          severity: 'CRITICAL',
          created_at: new Date().toISOString(),
          rule_version: {
            id: 'rv-1',
            rule_id: 'r-1',
            version: '1.0',
            requirement_text: 'Net quantity specification',
            validation_type: 'FORMAT_CHECK',
            severity: 'CRITICAL',
            source_gazette_reference: 'GSR 202(E)',
          },
        },
        {
          id: 'chk-2',
          inspection_id: 'insp-100',
          rule_version_id: 'rv-2',
          status: 'FAIL',
          explanation: 'Mandatory tax clause missing on retail price.',
          detected_value: 'MRP Rs. 100.00',
          expected_requirement: 'MRP inclusive of all taxes.',
          confidence: 0.90,
          severity: 'CRITICAL',
          created_at: new Date().toISOString(),
          rule_version: {
            id: 'rv-2',
            rule_id: 'r-2',
            version: '1.0',
            requirement_text: 'Maximum retail price declaration',
            validation_type: 'FORMAT_CHECK',
            severity: 'CRITICAL',
            source_gazette_reference: 'GSR 202(E)',
          },
        },
      ],
    });

    vi.mocked(api.getInspectionViolations).mockResolvedValue([
      {
        id: 'viol-1',
        violation_code: 'VIOL_PCR_2011_RULE_6_1_E',
        description: 'Missing inclusive of all taxes statement on retail pack.',
        severity: 'CRITICAL',
        status: 'FLAGGED_FOR_REVIEW',
      },
    ]);

    vi.mocked(api.getInspectionHistory).mockResolvedValue([
      {
        id: 'hist-1',
        action: 'INSPECTION_CREATED',
        previous_status: null,
        new_status: 'CREATED',
        timestamp: new Date().toISOString(),
      },
    ]);

    vi.mocked(api.listInspectionReports).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <ScanResult />
      </BrowserRouter>
    );

    // Verify main headings
    await waitFor(() => {
      expect(screen.getByText(/Inspection Dossier & Enforcement Review/i)).toBeInTheDocument();
      expect(screen.getByText(/Advisory Screening Verdict/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Potential Non-Compliance/i).length).toBeGreaterThan(0);
    });

    // Verify summary metric cards
    expect(screen.getByText(/Passed Checks/i)).toBeInTheDocument();
    expect(screen.getByText(/Potential Violations/i)).toBeInTheDocument();

    // Verify rule checks and violations
    expect(screen.getByText(/500 g/i)).toBeInTheDocument();
    expect(screen.getByText(/MRP Rs. 100.00/i)).toBeInTheDocument();
    expect(screen.getByText(/VIOL_PCR_2011_RULE_6_1_E/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Confirm Violation/i })).toBeInTheDocument();
  });

  it('filters rule checks by status', async () => {
    vi.mocked(api.getInspectionCompliance).mockResolvedValue({
      inspection_id: 'insp-100',
      overall_status: 'POTENTIAL_NON_COMPLIANCE',
      total_rules_evaluated: 2,
      pass_count: 1,
      fail_count: 1,
      review_count: 0,
      not_applicable_count: 0,
      violations_flagged: 1,
      mean_confidence: 0.94,
      disclaimer: 'Advisory notice.',
      checks: [
        {
          id: 'chk-1',
          inspection_id: 'insp-100',
          rule_version_id: 'rv-1',
          status: 'PASS',
          explanation: 'Net quantity metric unit valid',
          detected_value: '500 g',
          expected_requirement: 'Net quantity specification',
          confidence: 0.98,
          severity: 'CRITICAL',
          created_at: new Date().toISOString(),
          rule_version: {
            id: 'rv-1',
            rule_id: 'r-1',
            version: '1.0',
            requirement_text: 'Net quantity specification',
            validation_type: 'FORMAT_CHECK',
            severity: 'CRITICAL',
          },
        },
        {
          id: 'chk-2',
          inspection_id: 'insp-100',
          rule_version_id: 'rv-2',
          status: 'FAIL',
          explanation: 'Missing inclusive of all taxes',
          detected_value: 'MRP Rs. 100.00',
          expected_requirement: 'MRP inclusive of all taxes',
          confidence: 0.90,
          severity: 'CRITICAL',
          created_at: new Date().toISOString(),
          rule_version: {
            id: 'rv-2',
            rule_id: 'r-2',
            version: '1.0',
            requirement_text: 'MRP declaration',
            validation_type: 'FORMAT_CHECK',
            severity: 'CRITICAL',
          },
        },
      ],
    });
    vi.mocked(api.getInspectionViolations).mockResolvedValue([]);
    vi.mocked(api.getInspectionHistory).mockResolvedValue([]);
    vi.mocked(api.listInspectionReports).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <ScanResult />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/500 g/i)).toBeInTheDocument();
    });

    // Click FAIL filter button
    const failBtn = screen.getByRole('button', { name: /^FAIL$/i });
    fireEvent.click(failBtn);

    expect(screen.getByText(/MRP Rs. 100.00/i)).toBeInTheDocument();
    expect(screen.queryByText(/500 g/i)).not.toBeInTheDocument();
  });
});
