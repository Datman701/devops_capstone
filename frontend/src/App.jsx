import { useState } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';

import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import AppointmentsPage from './pages/AppointmentsPage';
import DashboardPage from './pages/DashboardPage';
import DoctorsPage from './pages/DoctorsPage';
import PatientsPage from './pages/PatientsPage';
import { useReferenceData } from './hooks/useClinicData';

const TITLES = {
  '/': { title: 'Dashboard', subtitle: 'Clinic-wide appointment overview' },
  '/appointments': {
    title: 'Appointments',
    subtitle: 'Search, reschedule and cancel bookings',
  },
  '/doctors': { title: 'Doctors', subtitle: 'Manage the practitioner roster' },
  '/patients': { title: 'Patients', subtitle: 'Registered patient directory' },
};

export default function App() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Single source of truth for doctors/patients/stats, shared by every page.
  const reference = useReferenceData();

  const meta = TITLES[location.pathname] ?? TITLES['/'];

  return (
    <div className="layout">
      <Sidebar
        isOpen={sidebarOpen}
        onNavigate={() => setSidebarOpen(false)}
        backendUp={reference.backendUp}
      />
      {sidebarOpen ? (
        <div
          className="scrim"
          role="presentation"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}

      <div className="main">
        <Topbar
          title={meta.title}
          subtitle={meta.subtitle}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
        />

        <Routes>
          <Route
            path="/"
            element={<DashboardPage reference={reference} />}
          />
          <Route
            path="/appointments"
            element={<AppointmentsPage reference={reference} />}
          />
          <Route
            path="/doctors"
            element={<DoctorsPage reference={reference} />}
          />
          <Route
            path="/patients"
            element={<PatientsPage reference={reference} />}
          />
          <Route
            path="*"
            element={
              <div className="content">
                <div className="panel">
                  <div className="panel__body">
                    <strong>Page not found.</strong>{' '}
                    <span className="muted">Use the sidebar to navigate.</span>
                  </div>
                </div>
              </div>
            }
          />
        </Routes>
      </div>
    </div>
  );
}