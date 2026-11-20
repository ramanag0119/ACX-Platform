import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/core/components/DataState";
import { ApiError } from "@/lib/api/client";

/**
 * The shared <ErrorState> plus a Retry control for failures that a retry can
 * fix (network, 5xx). 401 already signs the user out through the API client,
 * and 403 / 422 are answers, not outages, so they get no retry button.
 */
export const QueryErrorState = ({ error, onRetry }: { error: unknown; onRetry?: () => void }) => {
  const retryable = !(error instanceof ApiError) || error.isNetworkError || error.isServerError;
  return (
    <div>
      <ErrorState error={error} />
      {retryable && onRetry ? (
        <div className="-mt-6 flex justify-center pb-6">
          <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
            <RotateCw className="h-3.5 w-3.5" aria-hidden /> Retry
          </Button>
        </div>
      ) : null}
    </div>
  );
};
