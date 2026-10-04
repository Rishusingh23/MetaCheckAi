import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const Violations: React.FC = () => {
  const flags = [
    {
      id: 'FLG-2026-0312',
      product: 'Almond Crunch Cookies 200g',
      brand: 'NutriBites Ltd',
      infraction: 'Unit Sale Price (USP) font height below statutory minimum requirement under Rule 6(1)(ea).',
      rule: 'Rule 6(1)(ea)',
      severity: 'Medium',
      date: '2026-09-14',
      status: 'Pending Physical Audit',
    },
    {
      id: 'FLG-2026-0311',
      product: 'Organic Basmati Rice 5kg',
      brand: 'Heritage Grains',
      infraction: 'Consumer Care email domain unresolved or missing valid contact telephone number under Rule 6(1)(g).',
      rule: 'Rule 6(1)(g)',
      severity: 'High',
      date: '2026-09-13',
      status: 'Notice Issued',
    },
    {
      id: 'FLG-2026-0310',
      product: 'Imported Belgian Chocolate 100g',
      brand: 'ChocoArtisan',
      infraction: 'Country of Origin missing in principal display panel under Rule 6(1)(f).',
      rule: 'Rule 6(1)(f)',
      severity: 'High',
      date: '2026-09-12',
      status: 'Review In Progress',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Potential Non-Compliance Tracking</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Advisory queue of flagged packaged goods awaiting manual verification and statutory action
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {flags.map((item) => (
          <Card key={item.id} className="border-amber-500/20 bg-slate-900/60">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold text-amber-400">{item.id}</span>
                  <Badge variant="warning">{item.rule}</Badge>
                  <span className="text-xs text-slate-400">&bull; Flagged on {item.date}</span>
                  <span className="text-xs font-semibold text-rose-400">[{item.severity} Priority]</span>
                </div>
                <h3 className="text-base font-bold text-white">
                  {item.product} &mdash; <span className="text-slate-400 font-normal">{item.brand}</span>
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  {item.infraction}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 shrink-0">
                <div className="text-right sm:mr-3">
                  <p className="text-[11px] text-slate-400">Current Workflow State</p>
                  <span className="text-xs font-semibold text-amber-300">{item.status}</span>
                </div>
                <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                  Review Dossier
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
