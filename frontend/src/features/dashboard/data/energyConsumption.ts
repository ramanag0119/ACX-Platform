/**
 * Selectors behind the dashboard's Average Energy Consumption card.
 *
 * The source is GET /energy-stats/summary, which performs SUM and COUNT only.
 * Every headline figure the card shows is derived from the same buckets it
 * plots, so the numbers cannot drift away from the bars.
 *
 * NO UNIT IS RECORDED: `energy_stat` has no unit column and the API returns
 * `energy_unit: null`. Nothing here may be labelled kWh, costed or
 * carbon-weighted, and there is no efficiency or baseline figure to report.
 */

import type { EnergySummaryBucket } from "@/lib/api/types";

export type EnergyGrouping = "hour" | "day";

export interface EnergyPoint {
  /** Axis label. */
  name: string;
  /** Spelled out bucket, used in the tooltip and the insight sentence. */
  fullName: string;
  /** The stored SUM for the bucket. */
  totalEnergy: number;
  /** That SUM divided by the stored COUNT - a presentation division. */
  avgPerReading: number;
  /** The stored COUNT, kept so tiles can report real reading volume. */
  readingCount: number;
}

const round = (value: number, decimals = 3) => {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
};

const mean = (values: number[]) =>
  values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

/**
 * Axis and tooltip wording for one bucket. `bucket_label` is used whenever the
 * backend supplies one; the fallbacks only cover the null case.
 */
const describeBucket = (
  bucket: EnergySummaryBucket,
  grouping: EnergyGrouping,
  bucketCount: number,
): { name: string; fullName: string } => {
  const at = new Date(bucket.bucket);
  const parsed = !Number.isNaN(at.getTime());

  if (!parsed) {
    const raw = bucket.bucket_label ?? bucket.bucket;
    return { name: raw, fullName: raw };
  }

  if (grouping === "hour") {
    return {
      name: bucket.bucket_label ?? at.toLocaleTimeString([], { hour: "2-digit", hour12: false }),
      fullName: at.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        hour12: false,
      }),
    };
  }

  // A week's worth of days reads best as weekdays; longer spans need the date.
  const shortDay =
    bucketCount <= 7
      ? at.toLocaleDateString([], { weekday: "short" })
      : at.toLocaleDateString([], { month: "short", day: "numeric" });

  return {
    name: bucket.bucket_label ?? shortDay,
    fullName: at.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" }),
  };
};

export const toEnergyPoints = (
  buckets: EnergySummaryBucket[],
  grouping: EnergyGrouping,
): EnergyPoint[] =>
  buckets.map((bucket) => ({
    ...describeBucket(bucket, grouping, buckets.length),
    totalEnergy: round(bucket.total_energy_consumed),
    avgPerReading:
      bucket.reading_count > 0 ? round(bucket.total_energy_consumed / bucket.reading_count) : 0,
    readingCount: bucket.reading_count,
  }));

export interface EnergyStats {
  peak: EnergyPoint;
  lowest: EnergyPoint;
  /** Mean average-per-reading across the window. */
  average: number;
  /** Sum of the stored bucket totals across the window. */
  totalEnergy: number;
  /** Sum of the stored reading counts across the window. */
  readingCount: number;
  /**
   * Signed change in `average` against the preceding window of equal length.
   * Null when the endpoint returned no earlier history to compare against.
   */
  trendPercent: number | null;
  /** Peak bucket measured against the next highest. */
  insight: { peak: EnergyPoint; runnerUp: EnergyPoint; percentHigher: number } | null;
}

export const summariseEnergy = (
  points: EnergyPoint[],
  previous: EnergyPoint[] = [],
): EnergyStats | null => {
  if (points.length === 0) return null;

  const byTotal = [...points].sort((a, b) => b.totalEnergy - a.totalEnergy);
  const [peak, runnerUp] = byTotal;
  const average = mean(points.map((point) => point.avgPerReading));
  const previousAverage = previous.length ? mean(previous.map((point) => point.avgPerReading)) : 0;

  return {
    peak,
    lowest: byTotal[byTotal.length - 1],
    average: round(average),
    totalEnergy: round(points.reduce((sum, point) => sum + point.totalEnergy, 0)),
    readingCount: points.reduce((sum, point) => sum + point.readingCount, 0),
    trendPercent: previousAverage
      ? round(((average - previousAverage) / previousAverage) * 100, 1)
      : null,
    insight:
      runnerUp && runnerUp.totalEnergy > 0
        ? {
            peak,
            runnerUp,
            percentHigher: round(
              ((peak.totalEnergy - runnerUp.totalEnergy) / runnerUp.totalEnergy) * 100,
              1,
            ),
          }
        : null,
  };
};
