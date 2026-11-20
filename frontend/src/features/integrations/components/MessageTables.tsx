import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSurfaceTokens } from "@/core/styles/surfaceTokens";
import type { DeadLetterEntry, IntegrationMessage } from "@/lib/api/integrations";
import {
  facilityLabel,
  failureCategoryLabel,
  failureLabel,
  formatShortTimestamp,
  formatTimestamp,
  messageTypeLabel,
} from "../lib/presentation";
import { StatusBadge } from "./StatusBadge";

/**
 * Metadata-only tables. The observability API carries no payload, guest data
 * or credential, and these tables add none: every cell is a field of the
 * documented response, shown in business wording (message type, failure
 * reason and category labels) rather than as backend identifiers.
 *
 * The message cell carries the type plus the short message ID and the
 * sender's reference ID, which keeps the tables within a desktop width.
 * `inProtocolContext` (the HTNG / FIAS screens) also drops the Protocol
 * column, since every row there has the same protocol.
 */

// Headers may wrap to two lines (the global table style uppercases them), so
// a table fits a 1366px laptop without scrolling.
const HEAD = "px-3 py-2 align-bottom text-xs font-semibold";
const CELL = "px-3 py-2.5 text-xs align-top";
const ROW = "border-b border-border/60 hover:bg-[var(--hms-table-row-hover-bg)]";

const When = ({ iso }: { iso: string | null }) => (
  <span className="whitespace-nowrap" title={iso ? formatTimestamp(iso) : undefined}>
    {formatShortTimestamp(iso)}
  </span>
);

/** Last attempt on top, the received time underneath. */
const AttemptTimes = ({ last, received }: { last: string | null; received: string | null }) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <span className="flex flex-col">
      <When iso={last} />
      <span className="whitespace-nowrap text-[11px] leading-4" style={{ color: textMuted }}>
        Received <When iso={received} />
      </span>
    </span>
  );
};

/** Type on top; message ID (short) and reference ID underneath, full values on hover. */
const MessageCell = ({
  type,
  id,
  reference,
  protocol,
}: {
  type: string;
  id: string;
  reference: string;
  /** When given, the protocol tag sits beside the type instead of in its own column. */
  protocol?: string;
}) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <span className="flex min-w-[9rem] flex-col">
      <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
        {protocol ? <Protocol value={protocol} /> : null}
        {messageTypeLabel(type)}
      </span>
      <span className="whitespace-nowrap text-[11px] leading-4" style={{ color: textMuted }}>
        <span title={`Message ID ${id}`}>#{id.slice(0, 8)}</span>
        {" · "}
        <span title={`Reference ID ${reference}`}>Ref {reference}</span>
      </span>
    </span>
  );
};

const Protocol = ({ value }: { value: string }) => (
  <span className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-semibold">{value.toUpperCase()}</span>
);

const FailureReason = ({ code, category }: { code: string | null; category: string | null }) => {
  const { textMuted } = useSurfaceTokens();
  if (!code) return <span style={{ color: textMuted }}>—</span>;
  return (
    <span className="flex min-w-[8rem] max-w-[14rem] flex-col" data-error-code={code}>
      <span className="text-foreground">{failureLabel(code)}</span>
      {category ? <span className="text-[11px]" style={{ color: textMuted }}>{failureCategoryLabel(category)}</span> : null}
    </span>
  );
};

export const MessageTable = ({
  rows,
  facilityNames,
  caption,
  inProtocolContext = false,
}: {
  rows: IntegrationMessage[];
  facilityNames: Map<string, string>;
  caption: string;
  inProtocolContext?: boolean;
}) => (
  <div className="overflow-x-auto">
    <Table aria-label={caption}>
      <TableHeader>
        <TableRow>
          <TableHead className={HEAD}>Message</TableHead>
          {inProtocolContext ? null : <TableHead className={HEAD}>Protocol</TableHead>}
          <TableHead className={HEAD}>Facility</TableHead>
          <TableHead className={HEAD}>Status</TableHead>
          <TableHead className={HEAD}>Received</TableHead>
          <TableHead className={HEAD}>Processed</TableHead>
          <TableHead className={`${HEAD} text-right`}>Retries</TableHead>
          <TableHead className={HEAD}>Failure reason</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((m) => (
          <TableRow key={m.message_id} className={ROW} data-message-id={m.message_id}>
            <TableCell className={CELL}><MessageCell type={m.message_type} id={m.message_id} reference={m.correlation_id} /></TableCell>
            {inProtocolContext ? null : <TableCell className={CELL}><Protocol value={m.protocol} /></TableCell>}
            <TableCell className={CELL}>{facilityLabel(m.facility_id, facilityNames)}</TableCell>
            <TableCell className={CELL}><StatusBadge status={m.status} /></TableCell>
            <TableCell className={CELL}><When iso={m.received_at} /></TableCell>
            <TableCell className={CELL}>
              {m.completed_at ? <When iso={m.completed_at} /> : <span className="text-muted-foreground">Not yet</span>}
            </TableCell>
            <TableCell className={`${CELL} text-right tabular-nums`}>{m.retry_count}</TableCell>
            <TableCell className={CELL}><FailureReason code={m.error?.code ?? null} category={m.error?.category ?? null} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
);

export const DeadLetterTable = ({
  rows,
  facilityNames,
  caption,
  inProtocolContext = false,
}: {
  rows: DeadLetterEntry[];
  facilityNames: Map<string, string>;
  caption: string;
  inProtocolContext?: boolean;
}) => (
  <div className="overflow-x-auto">
    <Table aria-label={caption}>
      <TableHeader>
        <TableRow>
          <TableHead className={HEAD}>Message</TableHead>
          <TableHead className={HEAD}>Facility</TableHead>
          <TableHead className={HEAD}>Failure category</TableHead>
          <TableHead className={HEAD}>Failure reason</TableHead>
          <TableHead className={`${HEAD} text-right`}>Retry attempts</TableHead>
          <TableHead className={HEAD}>Last attempt</TableHead>
          <TableHead className={HEAD}>Reprocessing</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((d) => (
          <TableRow key={d.message_id} className={ROW} data-message-id={d.message_id}>
            <TableCell className={CELL}>
              <MessageCell
                type={d.message_type}
                id={d.message_id}
                reference={d.correlation_id}
                protocol={inProtocolContext ? undefined : d.protocol}
              />
            </TableCell>
            <TableCell className={CELL}>{facilityLabel(d.facility_id, facilityNames)}</TableCell>
            <TableCell className={CELL}>{failureCategoryLabel(d.failure_category)}</TableCell>
            <TableCell className={CELL}><FailureReason code={d.failure_code} category={null} /></TableCell>
            <TableCell className={`${CELL} text-right tabular-nums`}>{d.attempt_count}</TableCell>
            <TableCell className={CELL}><AttemptTimes last={d.last_attempt_at} received={d.received_at} /></TableCell>
            <TableCell className={CELL}><RedriveEligibility redrive={d.redrive} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
);

/**
 * Read-only. Mirrors the two checks the existing audited reprocess (redrive)
 * endpoint makes -- the message is dead-lettered, and the caller may change
 * facility data. It does NOT predict that processing would succeed, and it
 * offers no action.
 */
export const RedriveEligibility = ({ redrive }: { redrive: DeadLetterEntry["redrive"] }) => {
  if (redrive.eligible) return <span className="whitespace-nowrap text-xs text-foreground">Eligible</span>;
  if (!redrive.state_eligible) return <span className="whitespace-nowrap text-xs text-muted-foreground">Not eligible</span>;
  return (
    <span className="block min-w-[5.5rem] text-xs text-muted-foreground" title="Reprocessing requires permission to change facility data.">
      Requires write access
    </span>
  );
};

// ------------------------------------------------- compact activity lists
/*
 * Overview "recent activity": the same fields as the tables, as a list that
 * fits a half-width panel without horizontal scrolling.
 */

export const MessageActivityList = ({
  rows,
  facilityNames,
  label,
}: {
  rows: IntegrationMessage[];
  facilityNames: Map<string, string>;
  label: string;
}) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <ul className="divide-y divide-border/60" aria-label={label}>
      {rows.map((m) => (
        <li key={m.message_id} className="flex items-start justify-between gap-3 py-2.5" data-message-id={m.message_id}>
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-sm text-foreground">
              <Protocol value={m.protocol} />
              <span className="font-medium">{messageTypeLabel(m.message_type)}</span>
            </p>
            <p className="mt-0.5 truncate text-xs" style={{ color: textMuted }}>
              {facilityLabel(m.facility_id, facilityNames)}
              {m.error ? ` · ${failureLabel(m.error.code)}` : ""}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <StatusBadge status={m.status} />
            <span className="text-[11px]" style={{ color: textMuted }}><When iso={m.received_at} /></span>
          </div>
        </li>
      ))}
    </ul>
  );
};

export const FailureActivityList = ({
  rows,
  facilityNames,
  label,
}: {
  rows: DeadLetterEntry[];
  facilityNames: Map<string, string>;
  label: string;
}) => {
  const { textMuted } = useSurfaceTokens();
  return (
    <ul className="divide-y divide-border/60" aria-label={label}>
      {rows.map((d) => (
        <li key={d.message_id} className="flex items-start justify-between gap-3 py-2.5" data-message-id={d.message_id}>
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-sm text-foreground">
              <Protocol value={d.protocol} />
              <span className="font-medium">{failureLabel(d.failure_code)}</span>
            </p>
            <p className="mt-0.5 truncate text-xs" style={{ color: textMuted }}>
              {messageTypeLabel(d.message_type)} · {facilityLabel(d.facility_id, facilityNames)} · {failureCategoryLabel(d.failure_category)}
            </p>
          </div>
          <span className="shrink-0 text-[11px]" style={{ color: textMuted }}><When iso={d.last_attempt_at ?? d.received_at} /></span>
        </li>
      ))}
    </ul>
  );
};
