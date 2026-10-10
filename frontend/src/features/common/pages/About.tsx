import { Card, CardContent } from "@/components/ui/card";
import {
  API_VERSION,
  PLATFORM_LICENSE,
  PLATFORM_RELEASE_DATE,
  PLATFORM_VENDOR,
  PLATFORM_VERSION,
} from "@/core/config/platform";

/** Release identity -- version, release date, vendor and license. */
const LEFT_COLUMN = [
  { label: "Platform Version", value: PLATFORM_VERSION },
  { label: "Platform Release Date", value: PLATFORM_RELEASE_DATE },
  { label: "API Version", value: API_VERSION },
];

const RIGHT_COLUMN = [
  { label: "Platform Vendor", value: PLATFORM_VENDOR },
  { label: "License", value: PLATFORM_LICENSE },
];

const InfoColumn = ({ rows }: { rows: { label: string; value: string }[] }) => (
  <dl className="divide-y divide-slate-200 dark:divide-slate-800">
    {rows.map(({ label, value }) => (
      <div key={label} className="flex items-center justify-between gap-4 py-2.5">
        <dt className="text-[13px] text-slate-700 dark:text-slate-300">{label}</dt>
        <dd className="text-[13px] font-semibold text-cyan-600 dark:text-cyan-400 text-right">
          {value}
        </dd>
      </div>
    ))}
  </dl>
);

const About = () => (
  <div className="animate-fade-in pt-5">
    <Card className="rounded-xl">
      <CardContent className="p-7">
        <h1 className="mb-4 text-[22px] font-semibold text-[#2563eb] dark:text-blue-400">
          About
        </h1>
        <div className="grid grid-cols-1 gap-x-6 md:grid-cols-2">
          <InfoColumn rows={LEFT_COLUMN} />
          <InfoColumn rows={RIGHT_COLUMN} />
        </div>
      </CardContent>
    </Card>
  </div>
);

export default About;
