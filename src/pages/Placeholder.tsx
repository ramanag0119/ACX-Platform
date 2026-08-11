import { Construction } from "lucide-react";
import { useLocation } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";

const Placeholder = () => {
  const location = useLocation();
  const pageName = location.pathname.split("/").pop() || "Page";
  const formattedName = pageName
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">{formattedName}</h1>
        <p className="page-description">This module is under construction</p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="p-4 rounded-full bg-muted mb-4">
            <Construction className="h-12 w-12 text-muted-foreground" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Coming Soon</h2>
          <p className="text-muted-foreground text-center max-w-md">
            The {formattedName} module is currently being developed. Check back
            soon for updates.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Placeholder;
