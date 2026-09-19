import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AuthProvider } from "@/core/contexts/AuthContext";
import { ProtectedRoute } from "@/core/components/ProtectedRoute";
import Login from "@/features/auth/pages/Login";
import Dashboard from "@/features/dashboard/pages/Dashboard";
import Tickets from "@/features/tickets/pages/Tickets";
import Reports from "@/features/reports/pages/Reports";
import KeySettings from "@/features/devices/pages/KeySettings";
import Occupancy from "@/features/occupancy/pages/Occupancy";
import Bookings from "@/features/bookings/pages/Bookings";
import ServiceTracking from "@/features/services/pages/ServiceTracking";
import ServicePlanning from "@/features/services/pages/ServicePlanning";
import FacilityManagement from "@/features/config/pages/FacilityManagement";
import ServicesSetup from "@/features/config/pages/ServicesSetup";
import Placeholder from "@/features/common/pages/Placeholder";
import NotFound from "@/features/common/pages/NotFound";
import UserRoles from "@/features/config/pages/UserRoles";
import Employees from "@/features/config/pages/Employees";
import JobOrder from "@/features/config/pages/JobOrder";
import LimitConfigAlert from "@/features/config/pages/LimitConfigAlert";
import Offers from "@/features/marketing/pages/Offers";
import Holidays from "@/features/marketing/pages/Holidays";
import Events from "@/features/marketing/pages/Events";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Navigate to="/HMS" replace />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              {/* The HMS dashboard. React Router matches case-SENSITIVELY, so
                  `/hms` is a separate path from `/HMS` and is redirected rather
                  than left to fall through to NotFound. `/dashboard` is kept as
                  a retired route for existing links, the same treatment
                  /power-view and friends get below. */}
              <Route path="/HMS" element={<Dashboard />} />
              <Route path="/hms" element={<Navigate to="/HMS" replace />} />
              <Route path="/dashboard" element={<Navigate to="/HMS" replace />} />
              <Route path="/occupancy" element={<Occupancy />} />
              <Route path="/bookings" element={<Bookings />} />
              <Route path="/services" element={<Navigate to="/services/tracking" replace />} />
              <Route path="/services/tracking" element={<ServiceTracking />} />
              <Route path="/services/planning" element={<ServicePlanning />} />
              <Route path="/config" element={<Navigate to="/config/facility" replace />} />
              <Route path="/config/facility" element={<FacilityManagement />} />
              <Route path="/config/user-roles" element={<UserRoles />} />
              <Route path="/config/services-setup" element={<ServicesSetup />} />
              <Route path="/config/employees" element={<Employees />} />
              <Route path="/config/job-order" element={<JobOrder />} />
              <Route path="/config/limit-alert" element={<LimitConfigAlert />} />
              <Route path="/offers" element={<Offers />} />
              <Route path="/holidays" element={<Holidays />} />
              <Route path="/events" element={<Events />} />
              <Route path="/reports/*" element={<Reports />} />
              <Route path="/tickets" element={<Tickets />} />
              {/* /power-view, /energy-view and /room-view are retired. Their
                  room-level figures are part of Room Details on /occupancy,
                  so old links land there rather than on a dead page. */}
              <Route path="/power-view" element={<Navigate to="/occupancy" replace />} />
              <Route path="/energy-view" element={<Navigate to="/occupancy" replace />} />
              <Route path="/room-view" element={<Navigate to="/occupancy" replace />} />
              <Route path="/key-settings" element={<KeySettings />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
