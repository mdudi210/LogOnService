import { Navigate, createBrowserRouter } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { GuardedRoute } from '@/components/GuardedRoute';
import { LoginPage } from '@/features/auth/LoginPage';
import { AdminConfigPage } from '@/features/admin/AdminConfigPage';
import { AdminEventsPage } from '@/features/admin/AdminEventsPage';
import { OverviewPage } from '@/features/user/OverviewPage';
import { SecurityPage } from '@/features/user/SecurityPage';
import { SessionsPage } from '@/features/user/SessionsPage';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />
  },
  {
    element: <GuardedRoute />,
    children: [
      {
        path: '/',
        element: <AppShell />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: 'sessions', element: <SessionsPage /> },
          { path: 'security', element: <SecurityPage /> }
        ]
      }
    ]
  },
  {
    element: <GuardedRoute adminOnly />,
    children: [
      {
        path: '/admin',
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/admin/events" replace /> },
          { path: 'events', element: <AdminEventsPage /> },
          { path: 'config', element: <AdminConfigPage /> }
        ]
      }
    ]
  },
  {
    path: '*',
    element: <Navigate to="/" replace />
  }
]);
