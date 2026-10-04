import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldQuestion, ArrowLeft } from 'lucide-react';
import { Button } from '../components/common/Button';

export const NotFound: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
      <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 mb-4">
        <ShieldQuestion className="w-8 h-8" />
      </div>
      <h2 className="text-xl font-bold text-white">Resource or Page Not Found</h2>
      <p className="text-xs text-slate-400 max-w-sm mt-1 mb-6">
        The requested module or inspection path does not exist in the current MetaCheck AI portal registry.
      </p>
      <Link to="/dashboard">
        <Button variant="primary" size="md" leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Return to Dashboard
        </Button>
      </Link>
    </div>
  );
};
