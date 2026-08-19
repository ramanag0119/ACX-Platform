import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Calendar,
  Settings,
  Tag,
  PartyPopper,
  CalendarDays,
  Cpu,
  FileText,
  Ticket,
  Zap,
  Gauge,
  Home,
  Key,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Menu,
  Headphones,
  MapPin,
  ClipboardList,
  Wrench,
  UserCog,
  LayoutGrid,
  User,
  Target,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  collapsed: boolean;
  subItems?: { to: string; label: string; icon?: React.ElementType }[];
}

const NavItem = ({ to, icon: Icon, label, collapsed, subItems }: NavItemProps) => {
  const location = useLocation();
  const isActive = location.pathname === to || location.pathname.startsWith(to + "/");
  const hasSubItems = subItems && subItems.length > 0;
  const [isOpen, setIsOpen] = useState(isActive);

  if (hasSubItems) {
    return (
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            "sidebar-nav-item w-full",
            isActive && "sidebar-nav-item-active"
          )}
        >
          <Icon className="sidebar-nav-item-icon" />
          {!collapsed && (
            <>
              <span className="sidebar-nav-item-text flex-1 text-left">{label}</span>
              <ChevronDown
                className={cn(
                  "sidebar-nav-chevron",
                  isOpen && "sidebar-nav-chevron-open"
                )}
              />
            </>
          )}
          {collapsed && <span className="sidebar-tooltip">{label}</span>}
        </button>

        {!collapsed && isOpen && (
          <div className="sidebar-nav-submenu">
            {subItems.map((item) => {
              const SubIcon = item.icon;
              const isSubActive = location.pathname === item.to;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "sidebar-nav-subitem",
                    isSubActive && "sidebar-nav-subitem-active"
                  )}
                >
                  {SubIcon && <SubIcon className="w-4 h-4" />}
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "sidebar-nav-item",
          isActive && "sidebar-nav-item-active"
        )
      }
    >
      <Icon className="sidebar-nav-item-icon" />
      {!collapsed && <span className="sidebar-nav-item-text">{label}</span>}
      {collapsed && <span className="sidebar-tooltip">{label}</span>}
    </NavLink>
  );
};

interface AppSidebarProps {
  collapsed: boolean;
}

export const AppSidebar = ({ collapsed }: AppSidebarProps) => {
  const navItems = [
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/occupancy", icon: Users, label: "Occupancy" },
    { to: "/bookings", icon: Calendar, label: "Bookings" },
    {
      to: "/services",
      icon: Headphones,
      label: "Services",
      subItems: [
        { to: "/services/tracking", label: "Services Tracking", icon: MapPin },
        { to: "/services/planning", label: "Services Planning", icon: ClipboardList },
      ],
    },
    {
      to: "/config",
      icon: Settings,
      label: "Config and Setup",
      subItems: [
        { to: "/config/facility", label: "Facility Management", icon: Wrench },
        { to: "/config/user-roles", label: "User Roles", icon: UserCog },
        { to: "/config/services-setup", label: "Services Setup", icon: LayoutGrid },
        { to: "/config/employees", label: "Employees", icon: User },
        { to: "/config/job-order", label: "Job Order", icon: Target },
        { to: "/config/limit-alert", label: "Limit Config Alert", icon: ShieldAlert },
      ],
    },
    { to: "/offers", icon: Tag, label: "Offers" },
    { to: "/holidays", icon: PartyPopper, label: "Holidays" },
    { to: "/events", icon: CalendarDays, label: "Events" },
    {
      to: "/devices",
      icon: Cpu,
      label: "Device Management",
      subItems: [
        { to: "/devices/caleido-network", label: "Caleido Network", icon: Cpu },
        { to: "/devices/firmware-management", label: "Firmware Management", icon: Wrench },
      ],
    },
    { to: "/reports/occupancy", icon: FileText, label: "Reports" },
    { to: "/tickets", icon: Ticket, label: "Tickets" },
    { to: "/power-view", icon: Zap, label: "Power View" },
    { to: "/energy-view", icon: Gauge, label: "Energy View" },
    { to: "/room-view", icon: Home, label: "Room View" },
    { to: "/key-settings", icon: Key, label: "Default Key Settings" },
  ];

  return (
    <aside
      className={cn(
        "sidebar-futuristic fixed left-0 top-[48px] bottom-[28px] z-40 flex flex-col",
        "transition-all duration-300 ease-out",
        collapsed ? "w-[64px] sidebar-collapsed" : "w-[240px]"
      )}
      style={{ height: "calc(100vh - 48px - 28px)" }}
    >
      {/* Navigation */}
      <nav className="sidebar-nav flex-1 overflow-y-auto scrollbar-thin py-2 pb-6 space-y-0.5">
        {navItems.map((item) => (
          <NavItem
            key={item.to}
            to={item.to}
            icon={item.icon}
            label={item.label}
            collapsed={collapsed}
            subItems={item.subItems}
          />
        ))}
      </nav>
    </aside>
  );
};