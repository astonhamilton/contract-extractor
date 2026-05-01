import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { CorpusScreen } from "@/screens/CorpusScreen/CorpusScreen";

export type CorpusRouteState = {
  documentId: string | null;
  pageNumber: number | null;
};

export type CorpusRouteActions = {
  patchRouteState: (patch: Partial<CorpusRouteState>) => void;
};

function readRouteState(searchParams: URLSearchParams): CorpusRouteState {
  const page = Number(searchParams.get("page"));

  return {
    documentId: searchParams.get("doc"),
    pageNumber: Number.isFinite(page) && page > 0 ? page : null,
  };
}

function writeRouteState(
  current: URLSearchParams,
  patch: Partial<CorpusRouteState>,
): URLSearchParams {
  const next = new URLSearchParams(current);

  if ("documentId" in patch) {
    if (patch.documentId) {
      next.set("doc", patch.documentId);
    } else {
      next.delete("doc");
    }
  }

  if ("pageNumber" in patch) {
    if (patch.pageNumber) {
      next.set("page", String(patch.pageNumber));
    } else {
      next.delete("page");
    }
  }

  return next;
}

export function CorpusRoute() {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeState = useMemo(
    () => readRouteState(searchParams),
    [searchParams],
  );

  function patchRouteState(patch: Partial<CorpusRouteState>): void {
    setSearchParams((current) => writeRouteState(current, patch));
  }

  return (
    <CorpusScreen
      routeActions={{ patchRouteState }}
      routeState={routeState}
    />
  );
}
