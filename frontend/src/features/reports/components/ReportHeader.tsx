import { Badge } from "@/components/ui/badge";

interface ReportHeaderProps {
  title: string;
  category?: string;
  description: string;
  isGenerated?: boolean;
  totalRecords?: number;
}

export const ReportHeader = ({
  title,
  category,
  description,
  isGenerated,
  totalRecords,
}: ReportHeaderProps) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div className="space-y-1">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h2 className="text-lg font-semibold tracking-tight text-foreground">{title}</h2>
          {category && (
            <Badge
              variant="secondary"
              className="text-[10px] font-medium tracking-wide uppercase px-2 py-0.5 bg-muted/60 text-muted-foreground border-border/50"
            >
              {category}
            </Badge>
          )}
          {isGenerated && totalRecords !== undefined && (
            <Badge
              variant="outline"
              className="text-[10px] font-medium px-2 py-0.5 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10"
            >
              Live Data
            </Badge>
          )}
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground max-w-3xl leading-relaxed">
          {description}
        </p>
      </div>
    </div>
  );
};
