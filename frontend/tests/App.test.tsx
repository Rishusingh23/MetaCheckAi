import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../src/App';
import * as api from '../src/services/api';

// Mock recharts responsive container for jsdom environment
vi.mock('recharts', async () => {
  const original = await vi.importActual('recharts');
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: '100%', height: '100%' }}>{children}</div>
    ),
  };
});

vi.mock('../src/services/api', async () => {
  const actual = await vi.importActual('../src/services/api');
  return {
    ...actual,
    getCurrentUser: vi.fn(),
    loginUser: vi.fn(),
    logoutUser: vi.fn(),
    getDashboardSummary: vi.fn().mockResolvedValue({
      total_inspections: 12,
      compliant_count: 8,
      non_compliant_count: 4,
      pending_review_count: 0,
      compliance_rate: 66.7,
      inspections_today: 3,
      critical_violations: 2,
      active_rules: 9,
      compliance_trend: [],
      violation_distribution: [],
      recent_inspections: [],
    }),
    getDashboardMetrics: vi.fn().mockResolvedValue({
      total_inspections: 12,
      compliant_count: 8,
      non_compliant_count: 4,
      pending_review_count: 0,
      compliance_rate: 66.7,
      inspections_today: 3,
      critical_violations: 2,
      active_rules: 9,
      compliance_trend: [],
      violation_distribution: [],
      recent_inspections: [],
    }),

  };
});

describe('MetaCheck AI Frontend Shell', () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, 'Test', '/');
    vi.clearAllMocks();
  });


  it('renders login page when unauthenticated', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText(/MetaCheck AI/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Legal Metrology Enforcement Portal/i)).toBeInTheDocument();
    });
  });


  it('renders application brand title and navigation links when authenticated', async () => {
    const mockUser = {
      id: '1',
      name: 'Inspector General',
      email: 'admin@metacheck.gov.in',
      role: 'ADMIN' as const,
      is_active: true,
    };

    localStorage.setItem('metacheck_access_token', 'mock_jwt_token');
    localStorage.setItem('metacheck_user_profile', JSON.stringify(mockUser));
    vi.mocked(api.getCurrentUser).mockResolvedValue(mockUser);

    render(<App />);

    await waitFor(() => {
      // Expect Brand Title to be present
      expect(screen.getAllByText(/MetaCheck/i).length).toBeGreaterThan(0);
      // Expect Dashboard to be rendered
      expect(screen.getByText(/Executive Compliance Dashboard/i)).toBeInTheDocument();
    });

    // Expect key navigation links
    expect(screen.getAllByText(/Product Scanner/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Inspection History/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Product Repository/i).length).toBeGreaterThan(0);
  });
});


