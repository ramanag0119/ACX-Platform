import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Tickets from "@/pages/Tickets";
import RoomView from "@/pages/RoomView";
import DeviceManagement from "@/pages/DeviceManagement";
import Reports from "@/pages/Reports";
import EnergyView from "@/pages/EnergyView";
import KeySettings from "@/pages/KeySettings";
import Occupancy from "@/pages/Occupancy";
import Bookings from "@/pages/Bookings";
import ServiceTracking from "@/pages/ServiceTracking";
import ServicePlanning from "@/pages/ServicePlanning";
import FacilityManagement from "@/pages/FacilityManagement";
import ServicesSetup from "@/pages/ServicesSetup";
import Placeholder from "@/pages/Placeholder";
import NotFound from "@/pages/NotFound";
import UserRoles from "@/pages/UserRoles";
import Employees from "@/pages/Employees";
import JobOrder from "@/pages/JobOrder";
import LimitConfigAlert from "@/pages/LimitConfigAlert";
import Offers from "@/pages/Offers";
import Holidays from "@/pages/Holidays";
import FirmwareManagement from "@/pages/FirmwareManagement";
import Events from "@/pages/Events";
import PowerView from "@/pages/PowerView";

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
