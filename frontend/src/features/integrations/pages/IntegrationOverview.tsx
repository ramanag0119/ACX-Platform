import { RotateCw } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { DataState, InlineLoading, TableLoading } from "@/core/components/DataState";
import { useIntegrationDeadLetters, useIntegrationMessages, useIntegrationOverview } from "@/lib/api/hooks";
import { FailureActivityList, MessageActivityList } from "../components/MessageTables";
import { QueryErrorState } from "../components/QueryErrorState";
import { useFacilityScope } from "../lib/hooks";
import { OverviewView } from "../views/OverviewView";

const ACTIVITY_ROWS = 5;

/**
 * Integration Overview -- GET /integrations/observability/overview, plus two
 * small server-side pages (5 newest messages, 5 newest dead letters) for the
 * recent-activity panels. Read-only; route-guarded on `facility_management`
 * (core/rbac/modules.ts).
 */
const IntegrationOverview = () => {
  const query = useIntegrationOverview();
  const recent = useIntegrationMessages({ page: 1, page_size: ACTIVITY_ROWS });
  const failed = useIntegrationDeadLetters({ page: 1, page_size: ACTIVITY_ROWS });
  const { names } = useFacilityScope();

  const refresh = () => {
    query.refetch();
    recent.refetch();
    failed.refetch();
  };

  return (
    <div className="space-y-4 animate-fade-in text-foreground">
      <PageHeader
        title="Integration Overview"
        description="HTNG and FIAS · vendor validation pending"
        actions={
          <Button variant="outline" size="sm" onClick={refresh} disabled={query.isFetching} className="gap-1.5">
            <RotateCw className={`h-3.5 w-3.5 ${query.isFetching ? "animate-spin" : ""}`} aria-hidden />
            Refresh
          </Button>
        }
      />
      {query.isLoading ? (
        <InlineLoading label="Loading integration status..." />
      ) : query.error ? (
        <QueryErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.data ? (
        <OverviewView
          data={query.data}
          recentMessages={
            recent.error ? (
              <QueryErrorState error={recent.error} onRetry={() => recent.refetch()} />
            ) : (
              <DataState
                isLoading={recent.isLoading}
                error={null}
                isEmpty={(recent.data?.items.length ?? 0) === 0}
                emptyTitle="No messages in the last 7 days"
                loader={<TableLoading columns={3} rows={3} />}
              >
                <MessageActivityList rows={recent.data?.items ?? []} facilityNames={names} label="Recent messages" />
              </DataState>
            )
          }
          latestFailures={
            failed.error ? (
              <QueryErrorState error={failed.error} onRetry={() => failed.refetch()} />
            ) : (
              <DataState
                isLoading={failed.isLoading}
                error={null}
                isEmpty={(failed.data?.items.length ?? 0) === 0}
                emptyTitle="No failed messages"
                loader={<TableLoading columns={3} rows={3} />}
              >
                <FailureActivityList rows={failed.data?.items ?? []} facilityNames={names} label="Latest failures" />
              </DataState>
            )
          }
        />
      ) : null}
    </div>
  );
};

export default IntegrationOverview;
