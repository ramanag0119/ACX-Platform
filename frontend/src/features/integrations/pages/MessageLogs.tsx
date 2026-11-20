import { PageHeader } from "@/components/layout/PageHeader";
import { DataState, TableLoading } from "@/core/components/DataState";
import { TablePagination } from "@/core/components/TablePagination";
import { useIntegrationMessages } from "@/lib/api/hooks";
import { useScrollToTop } from "@/hooks/use-scroll-to-top";
import { MessageFilterBar } from "../components/MessageFilterBar";
import { MessageTable } from "../components/MessageTables";
import { Panel } from "../components/Panel";
import { QueryErrorState } from "../components/QueryErrorState";
import { useFacilityScope, useUrlFilters } from "../lib/hooks";
import { formatShortTimestamp, restrictToScope, toQueryParams, validateDateRange } from "../lib/presentation";

/**
 * Message Logs -- GET /integrations/observability/messages.
 *
 * Filtering and pagination are server-side: the filters ARE the request, and
 * only one page is ever in the browser. Order is the backend's (newest
 * received first, then message id), which is stable across pages.
 * The API has no message-id search, so none is offered.
 */
const MessageLogs = () => {
  const [urlFilters, setFilters] = useUrlFilters(20);
  const { names, options, scopeIds } = useFacilityScope();
  const filters = restrictToScope(urlFilters, scopeIds);
  const dateError = validateDateRange(filters.from, filters.to);
  const query = useIntegrationMessages(toQueryParams(filters), { enabled: !dateError });
  useScrollToTop(filters.page);

  const page = query.data;
  const results = page
    ? `${page.total.toLocaleString()} ${page.total === 1 ? "message" : "messages"} · received ${formatShortTimestamp(page.window.received_from)} – ${formatShortTimestamp(page.window.received_to)}${filters.from || filters.to ? "" : " (last 7 days)"} · newest first`
    : "Newest first";

  return (
    <div className="space-y-4 animate-fade-in text-foreground">
      <PageHeader title="Message Logs" description="Inbound HTNG and FIAS messages for your facilities" />
      <Panel id="message-filters-heading" title="Filters">
        <MessageFilterBar
          filters={filters}
          onChange={setFilters}
          facilities={options}
          dateError={dateError}
          idPrefix="messages"
        />
      </Panel>
      <Panel id="message-results-heading" title="Messages" description={<span aria-live="polite">{results}</span>}>
        {query.error ? (
          <QueryErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : (
          <DataState
            isLoading={query.isLoading && !dateError}
            error={null}
            isEmpty={!dateError && (page?.items.length ?? 0) === 0}
            emptyTitle="No messages match these filters"
            emptyDescription="Widen the date range or clear a filter."
            loader={<TableLoading columns={8} />}
          >
            {page ? (
              <>
                <MessageTable rows={page.items} facilityNames={names} caption="Integration messages" />
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
      </Panel>
    </div>
  );
};

export default MessageLogs;
