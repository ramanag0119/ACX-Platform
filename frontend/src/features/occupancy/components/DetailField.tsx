/**
 * The label/value pair the Room Details dialog is built from, and the grid it
 * sits on.
 *
 * Shared rather than per-file, because the dialog's tabs are supposed to look
 * like one dialog. Room Details, Occupants Details and Power & Energy all render
 * the same shape -- a muted micro-caps label over a value -- and each used to
 * declare its own class strings. They had already drifted: the two Details
 * grids were 14px foreground values while Power & Energy was still 11px
 * uppercase in the SAME muted slate as its own labels, so the same kind of data
 * read two different ways depending on the tab.
 *
 * Power & Energy's values also carried `py-2.5 px-3`, lifted from TableHead.
 * That is table-cell padding and it does not belong in a grid: the horizontal
 * half indented every value 12px past its own label, so no column lined up, and
 * without `block` the span stayed inline, where vertical margin does not apply
 * and the label/value gap was silently dropped. Both are fixed here once.
 *
 * `dark:` companions rather than a hard-coded `text-white`: this dialog also
 * renders on the light theme, where white values would vanish. `text-foreground`
 * and `text-muted-foreground` already resolve per theme, and the explicit slate
 * pair pins the intended dark-theme greys.
 */

import type { ReactNode } from "react";

/**
 * The dash shown wherever a value is absent.
 *
 * Shared for the reason it was named in the first place: so the dialog cannot
 * drift into two spellings of "no value". It lived in RoomDetailsModal while
 * RoomPowerEnergy went on hardcoding "-" in three places, which is the drift it
 * was meant to prevent. One definition, one place to change should it ever
 * become an em dash or wording like "Not recorded".
 */
export const EMPTY_VALUE = "-";

export const FIELD_LABEL =
    "text-muted-foreground dark:text-slate-400 block text-xs font-medium uppercase tracking-wider";

export const FIELD_VALUE = "text-foreground dark:text-slate-100 block text-sm font-medium";

/**
 * The grid every detail section shares.
 *
 * Pixel alignment between the sections is the whole point of naming this: they
 * are separate <div>s, so their columns line up only while the column count and
 * gaps are identical AND their containers are the same width -- which is why no
 * section may wrap itself in a card or extra padding.
 *
 * Four columns at every width. `grid-cols-4` is exactly
 * `repeat(4, minmax(0, 1fr))`; the `minmax(0, ...)` is what stops a long value
 * from widening its own column and breaking the alignment.
 */
export const DETAIL_GRID = "grid grid-cols-4 gap-x-8 gap-y-6";

interface FieldProps {
    label: string;
    /** Rendered as-is. Callers pass their own "-" for an absent value. */
    value: ReactNode;
    /** Tooltip for a value that needs explaining, such as a structural dash. */
    title?: string;
}

/** One label/value pair in any detail grid. */
export const Field = ({ label, value, title }: FieldProps) => (
    <div className="space-y-1.5">
        <span className={FIELD_LABEL}>{label} :</span>
        <span className={FIELD_VALUE} title={title}>
            {value}
        </span>
    </div>
);
