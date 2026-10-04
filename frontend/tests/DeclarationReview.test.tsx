import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { DeclarationReviewTable } from '../src/components/scanner/DeclarationReviewTable';
import { DeclarationItem } from '../src/types';

const mockDeclarations: DeclarationItem[] = [
  {
    id: 'decl-1',
    scan_id: 'scan-123',
    declaration_type: 'MRP',
    raw_value: 'MRP Rs. 250.00 (Incl. of all taxes)',
    normalized_value: '₹ 250.00 (Incl. of all taxes)',
    confidence: 0.94,
    source_text: 'MRP Rs. 250.00 (Incl. of all taxes)',
    bounding_box: {
      x1: 50,
      y1: 100,
      x2: 300,
      y2: 140,
      confidence_breakdown: {
        rationale: 'High confidence price detection',
      },
    },
    extraction_status: 'CONFIRMED',
  },
  {
    id: 'decl-2',
    scan_id: 'scan-123',
    declaration_type: 'NET_QUANTITY',
    raw_value: 'Net Wt. 500g',
    normalized_value: '500 g',
    confidence: 0.91,
    source_text: 'Net Wt. 500g',
    bounding_box: {
      x1: 50,
      y1: 150,
      x2: 250,
      y2: 190,
    },
    extraction_status: 'AUTO_EXTRACTED',
  },
  {
    id: 'decl-3',
    scan_id: 'scan-123',
    declaration_type: 'COUNTRY_OF_ORIGIN',
    raw_value: 'Country of Origin: India / China',
    normalized_value: 'India',
    confidence: 0.65,
    source_text: 'Country of Origin: India / China',
    bounding_box: {
      x1: 50,
      y1: 200,
      x2: 350,
      y2: 240,
      is_ambiguous: true,
      alternative_candidates: [
        {
          raw_value: 'Country of Origin: China',
          normalized_value: 'China',
          confidence: 0.62,
        },
      ],
    },
    extraction_status: 'AMBIGUOUS',
  },
];

describe('DeclarationReviewTable Component', () => {
  it('renders summary metrics, items, and confidence ratings correctly', () => {
    render(
      <DeclarationReviewTable
        declarations={mockDeclarations}
        meanConfidence={0.833}
      />
    );

    // Verify summary cards
    expect(screen.getByText(/Total Declarations/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText(/83.3%/i)).toBeInTheDocument();
    expect(screen.getByText(/Ambiguous Items/i)).toBeInTheDocument();

    // Verify declaration rows
    expect(screen.getByText(/Maximum Retail Price/i)).toBeInTheDocument();
    expect(screen.getByText(/₹ 250.00 \(Incl. of all taxes\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Net Quantity/i)).toBeInTheDocument();
    expect(screen.getByText(/500 g/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Country of Origin/i })).toBeInTheDocument();
  });

  it('filters declarations by extraction status', () => {
    render(
      <DeclarationReviewTable
        declarations={mockDeclarations}
        meanConfidence={0.833}
      />
    );

    // Click AMBIGUOUS filter
    const ambiguousBtn = screen.getByRole('button', { name: /AMBIGUOUS/i });
    fireEvent.click(ambiguousBtn);

    expect(screen.getByRole('heading', { name: /Country of Origin/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Net Quantity/i })).not.toBeInTheDocument();
  });

  it('opens manual edit modal and allows officer correction and submission', async () => {
    const onUpdateMock = vi.fn().mockResolvedValue(undefined);

    render(
      <DeclarationReviewTable
        declarations={mockDeclarations}
        meanConfidence={0.833}
        onUpdateDeclaration={onUpdateMock}
      />
    );

    // Click Edit / Verify on the first item
    const editButtons = screen.getAllByRole('button', { name: /Edit \/ Verify/i });
    fireEvent.click(editButtons[0]);

    // Verify modal is displayed
    expect(screen.getByText(/Manual Declaration Correction/i)).toBeInTheDocument();

    // Update Normalized Value & Notes using precise placeholder selectors
    const normalizedTextarea = screen.getByPlaceholderText(/Enter corrected standardized declaration value/i);
    const notesInput = screen.getByPlaceholderText(/e.g. Corrected obscured digit/i);

    fireEvent.change(normalizedTextarea, { target: { value: '₹ 260.00 (Incl. of all taxes)' } });
    fireEvent.change(notesInput, { target: { value: 'Verified against invoice' } });

    // Click Save
    const saveButton = screen.getByRole('button', { name: /Save & Update Evidence/i });
    fireEvent.click(saveButton);

    expect(onUpdateMock).toHaveBeenCalledWith(
      'decl-1',
      expect.objectContaining({
        normalized_value: '₹ 260.00 (Incl. of all taxes)',
        extraction_status: 'CONFIRMED',
      }),
      'Verified against invoice'
    );
  });
});
