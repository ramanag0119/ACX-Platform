import type { ReactNode } from "react";
import { AlertTriangle, Ban, DatabaseZap, Inbox, Loader2, ShieldOff } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, describeApiError } from "@/lib/api/client";

/**
 * The one place loading / empty / error states are rendered.
 *
 * Every API-driven screen wraps its content in <DataState>, so 401, 403, 404,
 * 422, 500 and 503 look the same everywhere and no page grows its own copy.
 */

export const TableLoading = ({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) => (
  <div className="space-y-2 py-2" role="status" aria-label="Loading">
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="flex gap-3">
        {Array.from({ length: columns }).map((__, columnIndex) => (
          <Skeleton key={columnIndex} className="h-8 flex-1" />
        ))}
      </div>
    ))}
  </div>
);

export const InlineLoading = ({ label = "Loading..." }: { label?: string }) => (
  <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
    <Loader2 className="h-4 w-4 animate-spin" />
    <span>{label}</span>
  </div>
);

interface StateShellProps {
  icon: ReactNode;
  title: string;
  description?: string;
  children?: ReactNode;
}

const StateShell = ({ icon, title, description, children }: StateShellProps) => (
  <div className="flex flex-col items-center justify-center py-12 text-center">
    <div className="mb-3 rounded-full bg-muted p-3 text-muted-foreground">{icon}</div>
    <p className="font-medium text-foreground">{title}</p>
    {description && (
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
    )}
    {children}
  </div>
);

export const EmptyState = ({
  title = "No records found",
  description,
}: {
  title?: string;
  description?: string;
}) => <StateShell icon={<Inbox className="h-6 w-6" />} title={title} description={description} />;

/** Picks the right icon and wording for whichever status the backend returned. */
export const ErrorState = ({ error }: { error: unknown }) => {
  const message = describeApiError(error);

  if (error instanceof ApiError && error.isForbidden) {
    return (
      <StateShell
        icon={<ShieldOff className="h-6 w-6" />}
        title="Access denied"
        description={message}
      />
    );
  }
  if (error instanceof ApiError && error.isUnauthorized) {
    return (
      <StateShell icon={<Ban className="h-6 w-6" />} title="Session expired" description={message} />
    );
  }
  if (error instanceof ApiError && (error.status === 503 || error.isNetworkError)) {
    return (
      <StateShell
        icon={<DatabaseZap className="h-6 w-6" />}
        title="Service unavailable"
        description={message}
      />
    );
  }
  return (
    <StateShell
      icon={<AlertTriangle className="h-6 w-6" />}
      title="Could not load this data"
      description={message}
    />
  );
};

interface DataStateProps {
  isLoading: boolean;
  error: unknown;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  loader?: ReactNode;
  children: ReactNode;
}

export const DataState = ({
  isLoading,
  error,
  isEmpty,
  emptyTitle,
  emptyDescription,
  loader,
  children,
}: DataStateProps) => {
  if (isLoading) return <>{loader ?? <InlineLoading />}</>;
  if (error) return <ErrorState error={error} />;
  if (isEmpty) return <EmptyState title={emptyTitle} description={emptyDescription} />;
  return <>{children}</>;
};

/** Card-wrapped variant for widgets that stand alone on a page. */
export const DataStateCard = (props: DataStateProps) => (
  <Card>
    <CardContent className="p-4">
      <DataState {...props} />
    </CardContent>
  </Card>
);
