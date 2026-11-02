import { Button } from "@/components/ui/button";
import { FileText, Loader2, Play } from "lucide-react";

interface ReportEmptyStateProps {
  reportTitle: string;
  onGenerate: () => void;
  isLoading?: boolean;
}

export const ReportEmptyState = ({
  reportTitle,
  onGenerate,
  isLoading,
}: ReportEmptyStateProps) => {
  return (
    <div className="rounded-lg border border-dashed border-border/80 dark:border-slate-800 bg-muted/5 py-10 px-6 text-center space-y-3">
      <div className="mx-auto w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center">
        <FileText className="h-5 w-5" />
      </div>
      <div className="space-y-1 max-w-sm mx-auto">
        <h3 className="text-sm font-semibold text-foreground">
          Ready to Generate {reportTitle}
        </h3>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Configure filter parameters above and generate the report to retrieve live records.
        </p>
      </div>
      <div className="pt-1">
        <Button
          type="button"
          onClick={onGenerate}
          disabled={isLoading}
          className="h-9 px-4 rounded-md bg-brand hover:bg-brand-hover text-white text-xs font-medium shadow-xs hover:shadow-sm focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none transition-all inline-flex items-center justify-center gap-1.5"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Generating...</span>
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Generate Report</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
