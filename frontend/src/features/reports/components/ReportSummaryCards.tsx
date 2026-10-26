import { Card, CardContent } from "@/components/ui/card";
import { Database, Eye, Filter, FileSpreadsheet, Zap, BedDouble, Calendar } from "lucide-react";
import type { ReportRow } from "@/lib/api/reports";

interface ReportSummaryCardsProps {
  reportKey: string;
  total: number;
  rows: ReportRow[];
  filtersApplied: Record<string, string>;
  page: number;
  totalPages: number;
}

export const ReportSummaryCards = ({
  reportKey,
  total,
  rows,
  filtersApplied,
  page,
  totalPages,
}: ReportSummaryCardsProps) => {
  const appliedCount = Object.keys(filtersApplied).length;

  // Real contextual metric based on report type and rows on this page
  let contextualMetric = {
    title: "Report Status",
    value: total > 0 ? "Data Loaded" : "No Data",
    label: total > 0 ? "Ready to export" : "Adjust filters",
    icon: FileSpreadsheet,
    colorClass: "text-blue-500 bg-blue-500/10",
  };

  if (reportKey === "energy") {
    const pageTotalEnergy = rows.reduce((sum, r) => {
      const val = typeof r.energy_consumed === "number" ? r.energy_consumed : parseFloat(String(r.energy_consumed ?? 0));
      return sum + (Number.isNaN(val) ? 0 : val);
    }, 0);
    contextualMetric = {
      title: "Page Energy Usage",
      value: `${pageTotalEnergy.toLocaleString(undefined, { maximumFractionDigits: 1 })} kWh`,
      label: `Sum of ${rows.length} rows on page`,
      icon: Zap,
      colorClass: "text-amber-500 bg-amber-500/10",
    };
    const occupiedCount = rows.filter((r) => {
      const status = String(r.status_name ?? r.occupancy_status ?? "").toLowerCase();
      return status === "occupied" || status === "1";
    }).length;
    contextualMetric = {
      title: "Occupied in Page",
      value: `${occupiedCount} / ${rows.length}`,
      label: "Rooms occupied in view",
      icon: BedDouble,
      colorClass: "text-emerald-500 bg-emerald-500/10",
    };
  } else if (reportKey === "employee") {
    const activeStaff = rows.filter((r) => String(r.employment_status ?? "").toLowerCase() === "active").length;
    contextualMetric = {
      title: "Active on Page",
      value: `${activeStaff} / ${rows.length}`,
      label: "Active staff members",
      icon: Users,
      colorClass: "text-emerald-500 bg-emerald-500/10",
    };
  } else if (reportKey === "booking") {
    const totalGuestsOnPage = rows.reduce((sum, r) => {
      const guests = typeof r.no_of_guests === "number" ? r.no_of_guests : parseInt(String(r.no_of_guests ?? 0), 10);
      return sum + (Number.isNaN(guests) ? 0 : guests);
    }, 0);
    contextualMetric = {
      title: "Guests in View",
      value: totalGuestsOnPage.toLocaleString(),
      label: `Across ${rows.length} bookings on page`,
      icon: Calendar,
      colorClass: "text-purple-500 bg-purple-500/10",
    };
  }

  const cards = [
    {
      title: "Total Records",
      value: total.toLocaleString(),
      label: appliedCount > 0 ? "Matching criteria" : "Total available records",
      icon: Database,
      colorClass: "text-primary bg-primary/10",
    },
    {
      title: "Current View",
      value: `${rows.length} rows`,
      label: `Page ${page} of ${Math.max(1, totalPages)}`,
      icon: Eye,
      colorClass: "text-indigo-500 bg-indigo-500/10",
    },
    {
      title: "Active Filters",
      value: appliedCount === 0 ? "None" : `${appliedCount} applied`,
      label: appliedCount === 0 ? "Full dataset scope" : "Narrowed query",
      icon: Filter,
      colorClass: "text-teal-500 bg-teal-500/10",
    },
    contextualMetric,
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <Card
            key={index}
            className="border border-border/70 dark:border-slate-800 bg-card hover:bg-card/90 transition-shadow shadow-sm rounded-xl overflow-hidden"
          >
            <CardContent className="p-4 flex items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground tracking-tight">
                  {card.title}
                </p>
                <p className="text-xl font-bold tracking-tight text-foreground truncate">
                  {card.value}
                </p>
                <p className="text-[11px] text-muted-foreground/80 truncate">
                  {card.label}
                </p>
              </div>
              <div className={`p-2.5 rounded-xl ${card.colorClass} shrink-0`}>
                <Icon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};
