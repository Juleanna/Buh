import React, { useEffect, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuthStore } from './store/authStore'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AssetsPage from './pages/AssetsPage'
import AssetDetailPage from './pages/AssetDetailPage'
import GroupsPage from './pages/GroupsPage'
import ReceiptsPage from './pages/ReceiptsPage'
import DisposalsPage from './pages/DisposalsPage'
import DepreciationPage from './pages/DepreciationPage'
import InventoriesPage from './pages/InventoriesPage'
import InventoryDetailPage from './pages/InventoryDetailPage'
import UsersPage from './pages/UsersPage'
import ProfilePage from './pages/ProfilePage'

const EntriesPage = lazy(() => import('./pages/EntriesPage'))
const RevaluationsPage = lazy(() => import('./pages/RevaluationsPage'))
const ImprovementsPage = lazy(() => import('./pages/ImprovementsPage'))
const AuditLogPage = lazy(() => import('./pages/AuditLogPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const OrganizationsPage = lazy(() => import('./pages/OrganizationsPage'))
const ResponsiblePersonsPage = lazy(() => import('./pages/ResponsiblePersonsPage'))
const LocationsPage = lazy(() => import('./pages/LocationsPage'))
const PositionsPage = lazy(() => import('./pages/PositionsPage'))
const TurnoverReportPage = lazy(() => import('./pages/TurnoverReportPage'))
const BackupPage = lazy(() => import('./pages/BackupPage'))

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

const App: React.FC = () => {
  const { isAuthenticated, isLoading, loadProfile } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      loadProfile()
    }
  }, [])

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '200px auto' }} />
  }

  return (
    <Routes>
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
      } />
      <Route path="/" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      }>
        <Route index element={<DashboardPage />} />
        <Route path="assets" element={<AssetsPage />} />
        <Route path="assets/:id" element={<AssetDetailPage />} />
        <Route path="groups" element={<GroupsPage />} />
        <Route path="receipts" element={<ReceiptsPage />} />
        <Route path="disposals" element={<DisposalsPage />} />
        <Route path="depreciation" element={<DepreciationPage />} />
        <Route path="inventories" element={<InventoriesPage />} />
        <Route path="inventories/:id" element={<InventoryDetailPage />} />
        <Route path="entries" element={<Suspense fallback={<Spin />}><EntriesPage /></Suspense>} />
        <Route path="revaluations" element={<Suspense fallback={<Spin />}><RevaluationsPage /></Suspense>} />
        <Route path="improvements" element={<Suspense fallback={<Spin />}><ImprovementsPage /></Suspense>} />
        <Route path="organizations" element={<Suspense fallback={<Spin />}><OrganizationsPage /></Suspense>} />
        <Route path="responsible-persons" element={<Suspense fallback={<Spin />}><ResponsiblePersonsPage /></Suspense>} />
        <Route path="locations" element={<Suspense fallback={<Spin />}><LocationsPage /></Suspense>} />
        <Route path="positions" element={<Suspense fallback={<Spin />}><PositionsPage /></Suspense>} />
        <Route path="turnover-report" element={<Suspense fallback={<Spin />}><TurnoverReportPage /></Suspense>} />
        <Route path="audit-log" element={<Suspense fallback={<Spin />}><AuditLogPage /></Suspense>} />
        <Route path="notifications" element={<Suspense fallback={<Spin />}><NotificationsPage /></Suspense>} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="backup" element={<Suspense fallback={<Spin />}><BackupPage /></Suspense>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
