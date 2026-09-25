import { BatteryLow, CheckCircle2, Clock, Minus, ShieldCheck, Star, UserCheck, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * The housekeeping-condition pill: the Occupancy table's Status column and the
 * Room Details header both draw it, so it lives here once. Two copies would
 * drift, and the whole point of the header pill is that it looks exactly like
 * the one the operator just clicked from.
 *
 * Each rule only chooses a COLOUR for a name the API returned -- the condition
 * list itself is `amenity_condition` data, never a literal here. Rules are
 * checked in order and matched as substrings of the lower-cased name.
 */
const PILL_CLASS =
  "inline-flex h-7 items-center justify-center gap-1.5 px-2.5 py-1 text-[10.5px] font-semibold leading-none rounded-full border whitespace-nowrap";

interface ConditionStyle {
  match: string;
  pill: string;
  icon: string;
  Icon: LucideIcon;
}

const CONDITION_STYLES: ConditionStyle[] = [
  // `amenity_condition` 5, "Ready for occupant". Positive colouring so the rooms
  // that can actually be handed over stand out.
  {
    match: "ready",
    pill: "border-green-200 bg-green-50 text-green-700 dark:border-green-500/40 dark:bg-green-950/60 dark:text-green-400",
    icon: "text-green-600 dark:text-green-400",
    Icon: CheckCircle2,
  },
  {
    match: "maintenance",
    pill: "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/40 dark:bg-orange-950/60 dark:text-orange-400",
    icon: "text-orange-600 dark:text-orange-400",
    Icon: Wrench,
  },
  {
    match: "sanitation",
    pill: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400",
    icon: "text-emerald-600 dark:text-emerald-400",
    Icon: ShieldCheck,
  },
  {
    match: "low battery",
    pill: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-950/60 dark:text-rose-400",
    icon: "text-rose-600 dark:text-rose-400",
    Icon: BatteryLow,
  },
  {
    match: "vip",
    pill: "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-500/40 dark:bg-purple-950/60 dark:text-purple-300",
    icon: "text-purple-600 dark:text-purple-300",
    Icon: Star,
  },
  {
    match: "occupied",
    pill: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-300",
    icon: "text-amber-600 dark:text-amber-300",
    Icon: UserCheck,
  },
  {
    match: "late checkout",
    pill: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-400",
    icon: "text-amber-600 dark:text-amber-400",
    Icon: Clock,
  },
];

const FALLBACK_PILL =
  "border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-400";

/** One condition, as a coloured pill with its icon. */
export const ConditionBadge = ({ condition }: { condition: string }) => {
  const lower = condition.toLowerCase();
  const style = CONDITION_STYLES.find((rule) => lower.includes(rule.match));
  if (!style) {
    return (
      <span className={`${PILL_CLASS} ${FALLBACK_PILL}`}>
        <Minus className="h-3 w-3" />
        {condition}
      </span>
    );
  }
  const { Icon } = style;
  return (
    <span className={`${PILL_CLASS} ${style.pill}`}>
      <Icon className={`h-3 w-3 ${style.icon}`} />
      {condition}
    </span>
  );
};
