import { Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";

interface RoomDetailsPanelProps {
  roomNumber: string;
  roomType: string;
}

export const RoomDetailsPanel = ({ roomNumber, roomType }: RoomDetailsPanelProps) => {
  const { isDark } = useTheme();

  // Theme tokens
  const cardBg = isDark ? "linear-gradient(180deg, #1e2233, #1a1e30)" : "linear-gradient(180deg, rgba(255,255,255,0.85), rgba(245,242,255,0.95))";
  const cardBorder = isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(124,92,255,0.12)";
  const devCardBg = isDark ? "#1e2233" : "#ffffff";
  const devCardBorder = isDark ? "rgba(255,255,255,0.07)" : "rgba(124,92,255,0.12)";
  const devHeaderBg = isDark ? "#252a3e" : "#EEF2FF";
  const devHeaderBorder = isDark ? "#2a2f42" : "#e5e7eb";
  const titleColor = isDark ? "#dde2ed" : "#1F1B3A";
  const subTitleColor = isDark ? "#8b95a9" : "#5E5A7A";
  const labelColor = isDark ? "#8b95a9" : "#8A86A8";
  const valueColor = isDark ? "#dde2ed" : "#1F1B3A";
  const rowBorder = isDark ? "rgba(255,255,255,0.06)" : "rgba(124,92,255,0.1)";

  // Device card wrapper
  const DevCard = ({ children }: { children: React.ReactNode }) => (
    <div
      className="flex flex-col h-full rounded-lg overflow-hidden shadow-[0_8px_24px_rgba(17,12,46,0.12)] transition-all duration-250 hover:-translate-y-0.5"
      style={{ background: devCardBg, border: `1px solid ${devCardBorder}` }}
    >
      {children}
    </div>
  );

  // Device card header
  const DevHeader = ({ title, showSettings = false }: { title: string; showSettings?: boolean }) => (
    <div
      className="p-3 flex items-center justify-between min-h-[48px]"
      style={{ backgroundColor: devHeaderBg, borderBottom: `1px solid ${devHeaderBorder}` }}
    >
      <span className="font-medium text-sm" style={{ color: titleColor }}>{title}</span>
      {showSettings && <Settings className="h-4 w-4" style={{ color: labelColor }} />}
    </div>
  );

  // A single data row
  const Row = ({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) => (
    <div className="flex justify-between items-center">
      <span style={{ color: labelColor }}>{label}</span>
      <span className={valueClass} style={valueClass ? undefined : { color: valueColor }}>{value}</span>
    </div>
  );

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Room Details Card */}
      <div
        className="rounded-lg p-6 transition-all duration-250 ease hover:-translate-y-0.5"
        style={{ background: cardBg, border: cardBorder, boxShadow: "0 8px 24px rgba(17,12,46,0.12)" }}
      >
        <h3 style={{ color: titleColor }} className="font-medium mb-6">Room Details</h3>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Occupancy Details */}
          <div>
            <h4 style={{ color: subTitleColor }} className="text-center mb-4 font-medium">Occupancy Details</h4>
            <div className="space-y-3">
              {[
                { label: "Occupancy No", value: roomNumber },
                { label: "Occupancy Type", value: "Golden Package" },
                { label: "Status", value: "Occupied" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="flex justify-between py-2"
                  style={{ borderBottom: `1px solid ${rowBorder}` }}
                >
                  <span style={{ color: labelColor }}>{label}</span>
                  <span style={{ color: valueColor }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Booking Details */}
          <div>
            <h4 style={{ color: subTitleColor }} className="text-center mb-4 font-medium">Booking Details</h4>
            <div className="space-y-3">
              {[
                { label: "Guest Name", value: "Siva Subramanian N" },
                { label: "Booking Date", value: "27-12-2025 16:10" },
                { label: "Additional Guest", value: "0" },
                { label: "Actual Check In", value: "27-12-2025 16:22" },
                { label: "Expected Check Out", value: "27-12-2026 13:00" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="flex justify-between py-2"
                  style={{ borderBottom: `1px solid ${rowBorder}` }}
                >
                  <span style={{ color: labelColor }}>{label}</span>
                  <span style={{ color: valueColor }}>{value}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-4">
              <Button className="bg-[hsl(0,70%,50%)] hover:bg-[hsl(0,70%,45%)] text-white">
                Re-Allocate
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Device Details */}
      <div>
        <h3 style={{ color: titleColor }} className="font-medium mb-4">Device Details</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">

          {/* IntelliHub */}
          <DevCard>
            <DevHeader title={`IntelliHub - ${roomNumber}HUB01`} />
            <div className="p-4 space-y-2 text-sm flex-1">
              {[
                ["Room Power", ": ON"],
                ["Temperature", ": 66.0 °C"],
                ["Voltage", ": 260.0 V"],
                ["Current", ": 0.35 A"],
                ["Frequency", ": 50.1 Hz"],
                ["Power Factor", ": 1.00"],
                ["Active Power (P)", ": 0.370 KW"],
                ["Active Energy", ": 37.140 kWh"],
                ["Relay Operations", ": 434"],
              ].map(([label, value]) => (
                <Row key={label} label={label} value={value} />
              ))}
            </div>
          </DevCard>

          {/* AirQ */}
          <DevCard>
            <DevHeader title={`AirQ - ${roomNumber}AIR01`} showSettings />
            <div className="p-4 space-y-2 text-sm flex-1">
              <Row label="Room Temperature" value=": 0.0 °C" />
              <Row label="Humidity" value=": 29.8 %RH" />
              <Row label="Pressure" value=": 999.6 hPa" />
              <Row label="Air Quality (IAQ)" value=": 104" valueClass="text-[hsl(38,92%,50%)]" />
              <Row label="Temperature" value=": 34.5 °C" />
              <div className="mt-4 grid grid-cols-4 gap-1 text-[10px] text-center pt-4">
                <div>
                  <div className="w-3 h-3 bg-[hsl(145,70%,45%)] mx-auto mb-1 rounded-full" />
                  <span style={{ color: labelColor }}>GOOD</span>
                </div>
                <div>
                  <div className="w-3 h-3 bg-[hsl(38,92%,50%)] mx-auto mb-1 rounded-full" />
                  <span style={{ color: labelColor }}>MODERATE</span>
                </div>
                <div>
                  <div className="w-3 h-3 bg-[hsl(280,60%,50%)] mx-auto mb-1 rounded-full" />
                  <span style={{ color: labelColor }}>VERY UNHEALTHY</span>
                </div>
                <div>
                  <div className="w-3 h-3 bg-[hsl(0,70%,40%)] mx-auto mb-1 rounded-full" />
                  <span style={{ color: labelColor }}>HAZARDOUS</span>
                </div>
              </div>
            </div>
          </DevCard>

          {/* Mikos */}
          <DevCard>
            <DevHeader title={`Mikos - ${roomNumber}MIK01`} showSettings />
            <div className="p-4 space-y-2 text-sm flex-1">
              {[
                ["Voltage", ": 258.0 V"],
                ["Current", ": 0.00 A"],
                ["Frequency", ": 47.2 Hz"],
                ["Power Factor", ": 1.00"],
                ["Active Power (P)", ": 0.070 KW"],
                ["Active Energy", ": 4.960 kWh"],
                ["Temperature", ": 59.5 °C"],
              ].map(([label, value]) => (
                <Row key={label} label={label} value={value} />
              ))}
            </div>
          </DevCard>

          {/* Kleio */}
          <DevCard>
            <DevHeader title={`Kleio - ${roomNumber}KLE01`} />
            <div className="p-4 space-y-2 text-sm flex-1">
              {[
                ["Battery", ": 100 %"],
                ["Temperature", ": 31.5 °C"],
                ["Lock Status", ": CLOSE"],
              ].map(([label, value]) => (
                <Row key={label} label={label} value={value} />
              ))}
            </div>
          </DevCard>

        </div>
      </div>
    </div>
  );
};
