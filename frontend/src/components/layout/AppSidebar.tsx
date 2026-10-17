import { useState, useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Calendar,
  Settings,
  Tag,
  PartyPopper,
  CalendarDays,
  FileText,
  Ticket,
  Key,
  ChevronDown,
  Headphones,
  MapPin,
  ClipboardList,
  Wrench,
  UserCog,
  LayoutGrid,
  User,
  Target,
  ShieldAlert,
  BedDouble,
  CalendarRange,
  Info,
  UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/core/contexts/AuthContext";
import { moduleForPath } from "@/core/rbac/modules";

interface NavItemProps {
  to: string;
  icon: React.ElementType;
  label: string;
  collapsed: boolean;
  subItems?: { to: string; label: string; icon?: React.ElementType }[];
}

const NavItem = ({ to, icon: Icon, label, collapsed, subItems }: NavItemProps) => {
  const location = useLocation();
  const matches = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");
  // A group is active when its own prefix matches OR any child's does.
  const isActive =
    matches(to) || (subItems ?? []).some((item) => matches(item.to));
  const hasSubItems = subItems && subItems.length > 0;
  const [isOpen, setIsOpen] = useState(isActive);

  useEffect(() => {
    if (isActive) {
      setIsOpen(true);
    }
  }, [isActive]);

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

interface HmsNavGroupProps {
  collapsed: boolean;
  canReadModule: (moduleName: string) => boolean;
}

/**
 * HMS Navigation Group:
 * Represents the top-level HMS menu which directly links to the existing
 * HMS Dashboard (/HMS) while acting as the expandable parent of Occupancy
 * and Services (which contains Services Tracking and Services Planning).
 */
const HmsNavGroup = ({ collapsed, canReadModule }: HmsNavGroupProps) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Child permission checks
  const hasHms = canReadModule("dashboard");
  const hasOccupancy = canReadModule("occupancy");
  const hasServiceTracking = canReadModule("service_tracking");
  const hasServicePlanning = canReadModule("service_planning");
  const hasServices = hasServiceTracking || hasServicePlanning;

  // Active route detection
  const isHmsActive =
    location.pathname === "/HMS" ||
    location.pathname === "/hms" ||
    location.pathname === "/";
  const isOccupancyActive =
    location.pathname === "/occupancy" ||
    location.pathname.startsWith("/occupancy/");
  const isServiceTrackingActive =
    location.pathname === "/services/tracking" ||
    location.pathname.startsWith("/services/tracking/");
  const isServicePlanningActive =
    location.pathname === "/services/planning" ||
    location.pathname.startsWith("/services/planning/");
  const isServicesActive =
    isServiceTrackingActive ||
    isServicePlanningActive ||
    location.pathname === "/services";

  const isChildActive = isOccupancyActive || isServicesActive;

  // HMS parent open state (expanded by default if on HMS or on child route)
  const [isOpen, setIsOpen] = useState(isHmsActive || isChildActive);
  // Services submenu open state
  const [servicesOpen, setServicesOpen] = useState(isServicesActive);

  // Auto-expand parent when a child route is navigated to
  useEffect(() => {
    if (isChildActive || isHmsActive) {
      setIsOpen(true);
    }
  }, [location.pathname, isChildActive, isHmsActive]);

  useEffect(() => {
    if (isServicesActive) {
      setServicesOpen(true);
    }
  }, [location.pathname, isServicesActive]);

  // If user has no read access to any part of HMS, hide the group
  if (!hasHms && !hasOccupancy && !hasServices) {
    return null;
  }

  const handleHmsClick = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate("/HMS");
    setIsOpen(true);
  };

  return (
    <div className="relative">
      <div
        className={cn(
          "sidebar-nav-item w-full flex items-center justify-between group cursor-pointer",
          isHmsActive && "sidebar-nav-item-active"
        )}
        onClick={handleHmsClick}
      >
        <div
          className={cn(
            "flex items-center text-inherit no-underline min-w-0",
            collapsed ? "justify-center w-full" : "gap-3 flex-1"
          )}
        >
          <LayoutDashboard className="sidebar-nav-item-icon" />
          {!collapsed && (
            <span className="sidebar-nav-item-text truncate">HMS</span>
          )}
        </div>

        {!collapsed && (
          <button
            type="button"
            aria-label={isOpen ? "Collapse HMS submenu" : "Expand HMS submenu"}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setIsOpen((prev) => !prev);
            }}
            className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 text-current transition-colors ml-1 focus:outline-none"
          >
            <ChevronDown
              className={cn(
                "sidebar-nav-chevron",
                isOpen && "sidebar-nav-chevron-open"
              )}
            />
          </button>
        )}
        {collapsed && <span className="sidebar-tooltip">HMS</span>}
      </div>

      {/* Submenu under HMS */}
      {!collapsed && isOpen && (
        <div className="sidebar-nav-submenu">
          {/* 1. Occupancy */}
          {hasOccupancy && (
            <NavLink
              to="/occupancy"
              className={cn(
                "sidebar-nav-subitem",
                isOccupancyActive && "sidebar-nav-subitem-active"
              )}
            >
              <Users className="w-4 h-4 flex-shrink-0" />
              <span>Occupancy</span>
            </NavLink>
          )}

          {/* 2. Services */}
          {hasServices && (
            <div className="relative">
              <button
                type="button"
                aria-label={
                  servicesOpen
                    ? "Collapse Services submenu"
                    : "Expand Services submenu"
                }
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setServicesOpen((prev) => !prev);
                }}
                className="sidebar-nav-subitem w-full flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-2.5">
                  <Headphones className="w-4 h-4 flex-shrink-0" />
                  <span>Services</span>
                </div>
                <ChevronDown
                  className={cn(
                    "sidebar-nav-chevron w-3.5 h-3.5 opacity-60",
                    servicesOpen && "sidebar-nav-chevron-open"
                  )}
                />
              </button>

              {/* Submenu under Services */}
              {servicesOpen && (
                <div className="sidebar-nav-nested-submenu">
                  {hasServiceTracking && (
                    <NavLink
                      to="/services/tracking"
                      className={cn(
                        "sidebar-nav-subitem",
                        isServiceTrackingActive && "sidebar-nav-subitem-active"
                      )}
                    >
                      <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>Services Tracking</span>
                    </NavLink>
                  )}

                  {hasServicePlanning && (
                    <NavLink
                      to="/services/planning"
                      className={cn(
                        "sidebar-nav-subitem",
                        isServicePlanningActive && "sidebar-nav-subitem-active"
                      )}
                    >
                      <ClipboardList className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>Services Planning</span>
                    </NavLink>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface AppSidebarProps {
  collapsed: boolean;
}

export const AppSidebar = ({ collapsed }: AppSidebarProps) => {
  const { canRead } = useAuth();

  // Remaining standard sidebar items:
  // Occupancy and Services have moved under HMS.
  // Stay, Config and Setup, Manage, Reports, Tickets, Default Key Settings,
  // and About remain in their exact positions and functions.
  const remainingNavItems = [
    // Stay groups the two screens a stay is made of. `/stay` is a nav-only
    // prefix with no route of its own -- the parent is a disclosure button,
    // never a link -- so Offers and Booking keep their existing routes,
    // components and module grants untouched.
    {
      to: "/stay",
      icon: BedDouble,
      label: "Stay",
      subItems: [
        { to: "/offers", label: "Offers", icon: Tag },
        { to: "/reservations", label: "Reservation", icon: Calendar },
        { to: "/check-in", label: "Check-in", icon: UserCheck },
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
    // Manage groups the management screens: Holidays, Events, and Tickets.
    // Like Stay, `/manage` is a nav-only prefix with no route of its own,
    // so child screens keep their existing routes, components and module grants untouched.
    {
      to: "/manage",
      icon: CalendarRange,
      label: "Manage",
      subItems: [
        { to: "/holidays", label: "Holidays", icon: PartyPopper },
        { to: "/events", label: "Events", icon: CalendarDays },
        { to: "/tickets", label: "Tickets", icon: Ticket },
      ],
    },
    { to: "/reports/occupancy", icon: FileText, label: "Reports" },
    // Power View / Energy View / Room View are gone: their room-level figures
    // now live inside the Occupancy Dashboard's Room Details dialog.
    { to: "/key-settings", icon: Key, label: "Default Key Settings" },
    // About has no module grant, so every signed-in user sees it.
    { to: "/about", icon: Info, label: "About" },
  ];

  // Hide what the signed-in user has no read grant for.
  const isPermitted = (to: string) => {
    const moduleName = moduleForPath(to);
    return moduleName ? canRead(moduleName) : true;
  };

  const navItems = remainingNavItems
    .map((item) => {
      if (!item.subItems) return isPermitted(item.to) ? item : null;
      const subItems = item.subItems.filter((sub) => isPermitted(sub.to));
      return subItems.length ? { ...item, subItems } : null;
    })
    .filter(Boolean) as typeof remainingNavItems;

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
        {/* HMS Navigation Group (Parent of Occupancy and Services) */}
        <HmsNavGroup collapsed={collapsed} canReadModule={canRead} />

        {/* Remaining Sidebar Navigation Items */}
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