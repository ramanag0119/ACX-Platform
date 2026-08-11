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
import RoomView from "@/features/occupancy/pages/RoomView";
import DeviceManagement from "@/features/devices/pages/DeviceManagement";
import Reports from "@/features/reports/pages/Reports";
import EnergyView from "@/features/devices/pages/EnergyView";
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
import FirmwareManagement from "@/features/devices/pages/FirmwareManagement";
import Events from "@/features/marketing/pages/Events";
import PowerView from "@/features/devices/pages/PowerView";

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
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
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
              <Route path="/devices" element={<Navigate to="/devices/caleido-network" replace />} />
              <Route path="/devices/caleido-network" element={<DeviceManagement />} />
              <Route path="/devices/firmware-management" element={<FirmwareManagement />} />
              <Route path="/reports/*" element={<Reports />} />
              <Route path="/tickets" element={<Tickets />} />
              <Route path="/power-view" element={<PowerView />} />
              <Route path="/energy-view" element={<EnergyView />} />
              <Route path="/room-view" element={<RoomView />} />
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
