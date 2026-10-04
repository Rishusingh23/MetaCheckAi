import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { ProductScanner } from '../src/pages/ProductScanner';

// Mock API calls
vi.mock('../src/services/api', () => ({
  analyzeImageQuality: vi.fn().mockResolvedValue({
    sharpness_score: 250.0,
    is_blurry: false,
    brightness_mean: 140.0,
    is_too_dark: false,
    is_too_bright: false,
    contrast_score: 45.0,
    is_low_contrast: false,
    width: 800,
    height: 600,
    is_low_resolution: false,
    quality_score: 88.0,
    warnings: [],
  }),
  uploadAndProcessScan: vi.fn(),
  checkBackendHealth: vi.fn(),
  listDemoSamples: vi.fn().mockResolvedValue([
    {
      id: 'sample_a',
      scenario_name: 'Sample A: Compliant Potato Wafers',
      brand: 'Desi Crunch',
      commodity_name: 'Potato Wafers - Tangy Tomato',
      barcode: '8901234567890',
      description: 'Controlled compliant packaged commodity label.',
      expected_result: 'COMPLIANT',
      statutory_focus: 'All mandatory Rule 6 declarations present.',
    },
  ]),
  getDemoSampleImageBlob: vi.fn().mockResolvedValue(new Blob(['test'], { type: 'image/png' })),
  seedDemoSamples: vi.fn().mockResolvedValue({ status: 'success', total_seeded: 5, records: [] }),
}));

describe('ProductScanner OCR View', () => {
  it('renders package scanner header, engine selection, and drag-drop zone', () => {
    render(
      <MemoryRouter>
        <ProductScanner />
      </MemoryRouter>
    );

    // Verify header title
    expect(screen.getByText(/Commodity Label Optical Character Recognition/i)).toBeInTheDocument();

    // Verify Packaging Display Panel options
    expect(screen.getByText(/Packaging Display Panel/i)).toBeInTheDocument();
    expect(screen.getByText(/Principal Display Panel/i)).toBeInTheDocument();

    // Verify OCR Engine selection
    expect(screen.getByText(/OCR Engine Provider/i)).toBeInTheDocument();
    expect(screen.getByText(/Mock OCR/i)).toBeInTheDocument();

    // Verify Drag & drop area
    expect(screen.getByText(/Drag & drop package label image/i)).toBeInTheDocument();

    // Verify Statutory Disclaimer
    expect(screen.getByText(/Statutory Legal Metrology Notice/i)).toBeInTheDocument();
    expect(screen.getByText(/Declaration extraction is an automated evidence extraction process/i)).toBeInTheDocument();
  });
});
