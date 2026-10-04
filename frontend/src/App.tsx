import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';

// Pages
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { ProductScanner } from './pages/ProductScanner';
import { ScanResult } from './pages/ScanResult';
import { InspectionHistory } from './pages/InspectionHistory';
import { ProductRepository } from './pages/ProductRepository';
import { Violations } from './pages/Violations';
import { Reports } from './pages/Reports';
import { RuleManagement } from './pages/RuleManagement';
import { UserManagement } from './pages/UserManagement';
import { Settings } from './pages/Settings';
import { NotFound } from './pages/NotFound';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public authentication route */}
          <Route path="/login" element={<Login />} />

          {/* Application Shell routes protected by authentication & RBAC */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />

            {/* Dashboard: All roles */}
            <Route
              path="dashboard"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER']}>
                  <Dashboard />
                </ProtectedRoute>
              }
            />

            {/* Scanner: Admin and Enforcement Officer */}
            <Route
              path="scanner"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER']}>
                  <ProductScanner />
                </ProtectedRoute>
              }
            />

            {/* Scan Results: Admin and Enforcement Officer */}
            <Route
              path="scan-result"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER']}>
                  <ScanResult />
                </ProtectedRoute>
              }
            />

            {/* Inspection History: All roles */}
            <Route
              path="history"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER']}>
                  <InspectionHistory />
                </ProtectedRoute>
              }
            />

            {/* Product Repository: All roles */}
            <Route
              path="products"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER']}>
                  <ProductRepository />
                </ProtectedRoute>
              }
            />

            {/* Violations: Admin and Enforcement Officer */}
            <Route
              path="violations"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER']}>
                  <Violations />
                </ProtectedRoute>
              }
            />

            {/* Reports: All roles */}
            <Route
              path="reports"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'ENFORCEMENT_OFFICER', 'VIEWER']}>
                  <Reports />
                </ProtectedRoute>
              }
            />

            {/* Rule Management: Admin only */}
            <Route
              path="rules"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <RuleManagement />
                </ProtectedRoute>
              }
            />

            {/* User Management: Admin only */}
            <Route
              path="users"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <UserManagement />
                </ProtectedRoute>
              }
            />

            {/* Settings: Admin only */}
            <Route
              path="settings"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <Settings />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
