import { AlertTriangle, ArrowUpFromLine, Inbox } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { DataState, TableLoading } from "@/core/components/DataState";
import { TablePagination } from "@/core/components/TablePagination";
import { useIntegrationDeadLetters, useIntegrationOverview } from "@/lib/api/hooks";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { ACCENT, KpiTile } from "../components/KpiTile";
import { MessageFilterBar } from "../components/MessageFilterBar";
import { DeadLetterTable } from "../components/MessageTables";
import { Muted, Panel, SectionHeading } from "../components/Panel";
import { QueryErrorState } from "../components/QueryErrorState";
import { useFacilityScope, useUrlFilters } from "../lib/hooks";
import { LOAD_FAILED, restrictToScope, sumMeasured, toQueryParams, validateDateRange } from "../lib/presentation";

/**
 * Failed Messages / DLQ -- GET /integrations/observability/dlq. READ-ONLY.
 *
 * Reprocessing eligibility is displayed exactly as the backend reports it.
 * The existing audited POST /integrations/messages/{id}/redrive is
 * deliberately NOT exposed here (not approved for this screen). Dead letters
 * have no default date window; the backend bounds the query by status and
 * page. The summary tiles reuse the cached overview query.
 */
const DeadLetters = () => {
  const [urlFilters, setFilters] = useUrlFilters(20);
  const { names, options, scopeIds } = useFacilityScope();
  const filters = restrictToScope(urlFilters, scopeIds);
  const dateError = validateDateRange(filters.from, filters.to, null);
  const query = useIntegrationDeadLetters(toQueryParams(filters, { withStatus: false }), { enabled: !dateError });
  const overview = useIntegrationOverview();
  useScrollToTop(filters.page);
  const page = query.data;

  const shared = overview.data?.overview.messages;
  const status = overview.data ? shared?.status : overview.error ? LOAD_FAILED : undefined;
  const htng = overview.data?.protocols.htng.messages;
  const fias = overview.data?.protocols.fias.messages;

  return (
    <div className="space-y-4 animate-fade-in text-foreground">
      <PageHeader
        title="Failed Messages / DLQ"
        description="Messages that could not be processed after their retry attempts · read-only"
      />

      <section aria-labelledby="dlq-summary-heading">
        <SectionHeading
          id="dlq-summary-heading"
          title="Failure summary"
          description="All your facilities · messages currently held in the dead-letter queue"
        />
        {overview.isLoading ? null : (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <KpiTile
              label="Total in DLQ"
              value={shared ? sumMeasured([shared.failed_dead_letter, shared.outbound_dead_letter]) : null}
              blockStatus={status}
              icon={Inbox}
              accent={ACCENT.red}
              detail="Inbound and outbound"
            />
            <KpiTile label="HTNG inbound" value={htng?.inbound?.failed_dead_letter ?? null} blockStatus={htng?.status ?? status} icon={AlertTriangle} accent={ACCENT.amber} detail="Failed HTNG messages" />
            <KpiTile label="FIAS inbound" value={fias?.inbound?.failed_dead_letter ?? null} blockStatus={fias?.status ?? status} icon={AlertTriangle} accent={ACCENT.amber} detail="Failed FIAS messages" />
            <KpiTile label="Outbound" value={shared?.outbound_dead_letter ?? null} blockStatus={status} icon={ArrowUpFromLine} accent={ACCENT.violet} detail="Could not be sent to vendors" />
          </div>
        )}
      </section>

      <Panel
        id="dlq-filters-heading"
        title="Filters"
        description="A message moves to the dead-letter queue when it fails permanently or runs out of retry attempts."
      >
        <MessageFilterBar
          filters={filters}
          onChange={setFilters}
          facilities={options}
          showStatus={false}
          dateError={dateError}
          idPrefix="dlq"
        />
      </Panel>

      <Panel
        id="dlq-results-heading"
        title="Failed messages"
        description={page ? `${page.total.toLocaleString()} ${page.total === 1 ? "message" : "messages"} · newest first` : "Newest first"}
      >
        {query.error ? (
          <QueryErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : (
          <DataState
            isLoading={query.isLoading && !dateError}
            error={null}
            isEmpty={!dateError && (page?.items.length ?? 0) === 0}
            emptyTitle="No failed messages"
            emptyDescription="Nothing matching these filters is in the dead-letter queue."
            loader={<TableLoading columns={9} />}
          >
            {page ? (
              <>
                <DeadLetterTable rows={page.items} facilityNames={names} caption="Failed messages" />
                <TablePagination
                  currentPage={filters.page}
                  onPageChange={(p) => setFilters({ ...filters, page: p })}
                  totalEntries={page.total}
                  pageSize={filters.pageSize}
                />
              </>
            ) : null}
          </DataState>
        )}
        <Muted className="mt-3">
          Reprocessing is not available from this screen. Eligibility reflects the message state and your
          access; it does not predict whether reprocessing would succeed.
        </Muted>
      </Panel>
    </div>
  );
};

export default DeadLetters;
