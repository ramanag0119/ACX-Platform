import type { ComponentType } from "react";
import {
  BedDouble,
  Users,
  CheckCircle2,
  CalendarDays,
  Ticket,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Zap,
  FileText,
} from "lucide-react";

export interface ReportMeta {
  title: string;
  category: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
}

export const REPORT_META_MAP: Record<string, ReportMeta> = {
  occupancy: {
    title: "Occupancy Report",
    category: "Rooms & Spaces",
    description: "View real-time room occupancy, allotment status, and guest assignments across the property.",
    icon: BedDouble,
  },
  employee: {
    title: "Employee Report",
    category: "Staff & Organization",
    description: "Access staff directory records, department allocations, job functions, and employment histories.",
    icon: Users,
  },
  "room-status": {
    title: "Room Status Report",
    category: "Rooms & Spaces",
    description: "Monitor physical room condition, serviceability flags, privacy indicators, and maintenance states.",
    icon: CheckCircle2,
  },
  booking: {
    title: "Booking Report",
    category: "Stays & Guests",
    description: "Track reservation lifecycles, expected and actual arrival schedules, and stay durations.",
    icon: CalendarDays,
  },
  ticket: {
    title: "Ticket Report",
    category: "Service Operations",
    description: "Track guest and internal service requests from creation and assignment through completion.",
    icon: Ticket,
  },
  housekeeping: {
    title: "Housekeeping Report",
    category: "Service Operations",
    description: "Review scheduled and planned housekeeping work orders, room assignments, and completion states.",
    icon: Sparkles,
  },
  sanitization: {
    title: "Sanitization Report",
    category: "Service Operations",
    description: "Review disinfection schedules, sanitization compliance, and room hygiene readiness records.",
    icon: ShieldCheck,
  },
  alert: {
    title: "Alert Report",
    category: "Devices & Telemetry",
    description: "Track hardware alerts, warning severities, affected room locations, and incident telemetry.",
    icon: AlertTriangle,
  },
  energy: {
    title: "Energy Report",
    category: "Devices & Telemetry",
    description: "Analyze hourly electrical energy consumption by connected device, room, and floor.",
    icon: Zap,
  },
};

/**
 * Returns clean business metadata for a report key.
 * Never exposes database names, SQL references, or developer notes.
 */
export function getReportMeta(
  key: string,
  fallbackTitle?: string,
  fallbackDescription?: string
): ReportMeta {
  const meta = REPORT_META_MAP[key];
  if (meta) return meta;

  // For any unexpected or custom report, sanitize any technical jargon from description
  const cleanTitle = fallbackTitle || key.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  let cleanDesc = fallbackDescription || "Operational report for business monitoring and compliance.";

  // Strip technical details if present in fallback
  if (cleanDesc.includes("Source:") || cleanDesc.includes("`")) {
    cleanDesc = cleanDesc.replace(/Source:.*$/i, "").replace(/`[^`]+`/g, "").trim();
  }

  return {
    title: cleanTitle,
    category: "General",
    description: cleanDesc,
    icon: FileText,
  };
}
