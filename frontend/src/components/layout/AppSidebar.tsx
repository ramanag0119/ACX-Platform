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
  FileText,
  Ticket,
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
  BedDouble,
  CalendarRange,
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
  // A group is active when its own prefix matches OR any child's does. For
  // Services and Config and Setup the children already sit under the parent
  // prefix, so this changes nothing for them; it is what lets
  // a group whose children keep their own top-level routes -- Stay -> Offers,
  // Booking -- still highlight and open on the page it is showing.
  const isActive =
    matches(to) || (subItems ?? []).some((item) => matches(item.to));
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
  const { canRead } = useAuth();

  const allNavItems = [
    { to: "/dashboard", icon: LayoutDashboard, label: "HMS" },
    { to: "/occupancy", icon: Users, label: "Occupancy" },
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
        { to: "/bookings", label: "Booking", icon: Calendar },
      ],
    },
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
    // Manage groups the calendar-driven screens. Like Stay, `/manage` is a
    // nav-only prefix with no route of its own, so Holidays and Events keep
    // their existing routes, components and module grants untouched.
    {
      to: "/manage",
      icon: CalendarRange,
      label: "Manage",
      subItems: [
        { to: "/holidays", label: "Holidays", icon: PartyPopper },
        { to: "/events", label: "Events", icon: CalendarDays },
      ],
    },
    { to: "/reports/occupancy", icon: FileText, label: "Reports" },
    { to: "/tickets", icon: Ticket, label: "Tickets" },
    // Power View / Energy View / Room View are gone: their room-level figures
    // now live inside the Occupancy Dashboard's Room Details dialog.
    { to: "/key-settings", icon: Key, label: "Default Key Settings" },
  ];

  // Hide what the signed-in user has no read grant for. A parent with
  // sub-items survives as long as at least one child is permitted, and its
  // sub-items are filtered to match. Purely cosmetic -- the API is the
  // authority, and it will still answer 403 on anything not granted.
  const isPermitted = (to: string) => {
    const moduleName = moduleForPath(to);
    return moduleName ? canRead(moduleName) : true;
  };

  const navItems = allNavItems
    .map((item) => {
      if (!item.subItems) return isPermitted(item.to) ? item : null;
      const subItems = item.subItems.filter((sub) => isPermitted(sub.to));
      return subItems.length ? { ...item, subItems } : null;
    })
    .filter(Boolean) as typeof allNavItems;

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