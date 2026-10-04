import React from 'react';
import { UserPlus, Shield } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';

export const UserManagement: React.FC = () => {
  const users = [
    { name: 'Dr. S. K. Verma', email: 'sk.verma@gov.in', role: 'Chief Enforcement Officer', zone: 'North Zone', status: 'Active' },
    { name: 'Rajesh Kumar', email: 'rajesh.k@gov.in', role: 'Legal Metrology Officer (LMO)', zone: 'Delhi Central', status: 'Active' },
    { name: 'Anita Desai', email: 'anita.d@gov.in', role: 'Legal Metrology Officer (LMO)', zone: 'Mumbai South', status: 'Active' },
    { name: 'P. Menon', email: 'p.menon@gov.in', role: 'Compliance Data Analyst', zone: 'HQ Directorate', status: 'Active' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Inspector & User Management</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Role-Based Access Control (RBAC) for field inspectors, verifying officers, and administrators
          </p>
        </div>
        <Button variant="primary" size="sm" leftIcon={<UserPlus className="w-4 h-4" />}>
          Add Officer Account
        </Button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Officer Name</th>
                <th className="py-3 px-4">Official Email</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Jurisdiction Zone</th>
                <th className="py-3 px-4">Account Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {users.map((u, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 font-semibold text-white">{u.name}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1.5 text-metagov-400">
                      <Shield className="w-3.5 h-3.5" />
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-300">{u.zone}</td>
                  <td className="py-3 px-4">
                    <Badge variant="success">{u.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
