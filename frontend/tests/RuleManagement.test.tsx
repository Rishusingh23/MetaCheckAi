import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { RuleManagement } from '../src/pages/RuleManagement';
import * as api from '../src/services/api';

vi.mock('../src/services/api');

describe('RuleManagement Component', () => {
  it('renders statutory rule cards and allows searching and baseline seeding', async () => {
    vi.mocked(api.getRules).mockResolvedValue([
      {
        id: 'r-101',
        rule_code: 'PCR_2011_RULE_6_1_E',
        name: 'Maximum Retail Price (MRP)',
        description: 'Mandates retail sale price inclusive of all taxes.',
        legal_reference: 'Rule 6(1)(e), Legal Metrology Rules, 2011',
        is_active: true,
        versions: [
          {
            id: 'rv-101',
            rule_id: 'r-101',
            version: '1.0',
            requirement_text: 'MRP inclusive of all taxes',
            validation_type: 'FORMAT_CHECK',
            severity: 'CRITICAL',
            source_gazette_reference: 'GSR 202(E)',
          },
        ],
      },
    ]);

    vi.mocked(api.seedRuleBaseline).mockResolvedValue({
      message: 'Baseline seeded',
      seeded_count: 9,
    });

    render(<RuleManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Statutory Rules & Compliance Registry/i)).toBeInTheDocument();
      expect(screen.getByText(/PCR_2011_RULE_6_1_E/i)).toBeInTheDocument();
      expect(screen.getByText(/Maximum Retail Price \(MRP\)/i)).toBeInTheDocument();
    });

    // Test Search input
    const searchInput = screen.getByPlaceholderText(/Search by rule code/i);
    fireEvent.change(searchInput, { target: { value: 'MRP' } });
    expect(screen.getByText(/PCR_2011_RULE_6_1_E/i)).toBeInTheDocument();

    // Test Seed Baseline button
    const seedButton = screen.getByRole('button', { name: /Seed PCR 2011 Baseline/i });
    fireEvent.click(seedButton);

    await waitFor(() => {
      expect(api.seedRuleBaseline).toHaveBeenCalled();
      expect(screen.getByText(/Statutory baseline successfully verified\/seeded: 9 rules updated/i)).toBeInTheDocument();
    });
  });
});
