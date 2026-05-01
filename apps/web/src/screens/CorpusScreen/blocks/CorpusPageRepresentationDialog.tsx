import { useEffect, useMemo, useState } from "react";
import type {
  CorpusAsyncStatus,
  CorpusPageDetailView,
} from "@/domain/corpus/corpusTypes";
import { Badge } from "@/ui/primitives/Badge/Badge";
import { Button } from "@/ui/primitives/Button/Button";
import { Dialog } from "@/ui/primitives/Dialog/Dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/ui/primitives/Tabs/Tabs";
import { AsyncContentFrame } from "@/ui/patterns/AsyncContentFrame/AsyncContentFrame";
import { DialogFrame } from "@/ui/patterns/DialogFrame/DialogFrame";
import { EmptyState } from "@/ui/patterns/EmptyState/EmptyState";
import { PaginationStatusControls } from "@/ui/patterns/PaginationStatusControls/PaginationStatusControls";
import { SkeletonStack } from "@/ui/patterns/SkeletonStack/SkeletonStack";
import { StatusBanner } from "@/ui/patterns/StatusBanner/StatusBanner";
import styles from "./CorpusPageRepresentationDialog.module.css";

type CorpusPageRepresentationDialogProps = {
  canNextPage: boolean;
  canPreviousPage: boolean;
  data: CorpusPageDetailView | null;
  onClose: () => void;
  onNextPage: () => void;
  onPreviousPage: () => void;
  pageCount: number;
  pageNumber: number | null;
  status: CorpusAsyncStatus;
};

export function CorpusPageRepresentationDialog({
  canNextPage,
  canPreviousPage,
  data,
  onClose,
  onNextPage,
  onPreviousPage,
  pageCount,
  pageNumber,
  status,
}: CorpusPageRepresentationDialogProps) {
  const [selectedViewKey, setSelectedViewKey] = useState("best");
  const [flagsExpanded, setFlagsExpanded] = useState(false);
  const open = pageNumber !== null;
  const summaryViewKey = data?.summaryNote?.key ?? null;
  const firstViewKey = summaryViewKey ?? data?.views[0]?.key ?? "best";

  useEffect(() => {
    setSelectedViewKey(firstViewKey);
    setFlagsExpanded(false);
  }, [firstViewKey, pageNumber]);

  useEffect(() => {
    setFlagsExpanded(false);
  }, [selectedViewKey]);

  const selectedView = useMemo(
    () =>
      (data?.summaryNote?.key === selectedViewKey ? data.summaryNote : null) ??
      data?.views.find((view) => view.key === selectedViewKey) ??
      data?.summaryNote ??
      data?.views[0] ??
      null,
    [data?.summaryNote, data?.views, selectedViewKey],
  );

  const selectedViewFlags = useMemo(() => {
    if (!selectedView) {
      return [];
    }

    return [
      ...(selectedView.pageRole ? [selectedView.pageRole] : []),
      ...selectedView.relevanceTags,
      ...selectedView.qualityFlags,
    ];
  }, [selectedView]);

  const visibleFlags = flagsExpanded
    ? selectedViewFlags
    : selectedViewFlags.slice(0, 3);
  const hiddenFlagCount = Math.max(0, selectedViewFlags.length - visibleFlags.length);
  const tabViews = useMemo(
    () => (data?.summaryNote ? [data.summaryNote, ...data.views] : data?.views ?? []),
    [data?.summaryNote, data?.views],
  );

  function flagTone(flag: string): "neutral" | "warning" {
    return selectedView?.qualityFlags.includes(flag) ? "warning" : "neutral";
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogFrame
        actions={
          <>
            <PaginationStatusControls
              canGoNext={canNextPage}
              canGoPrevious={canPreviousPage}
              label={`${pageNumber ?? "-"} of ${pageCount || "-"}`}
              nextAriaLabel="Next page representation"
              onNext={onNextPage}
              onPrevious={onPreviousPage}
              previousAriaLabel="Previous page representation"
            />
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </>
        }
        ariaLabel={`Page ${pageNumber ?? ""} representation`}
        className={styles.content}
        eyebrow="Extracted representation"
        title={`Page ${pageNumber ?? ""}`}
      >
        <AsyncContentFrame measuring={status === "ready"} reset={!open}>
          {status === "loading" ? <SkeletonStack rows={5} /> : null}

          {status === "error" ? (
            <StatusBanner tone="danger">
              This page representation could not be loaded.
            </StatusBanner>
          ) : null}

          {status === "ready" && data && selectedView ? (
            <Tabs
              className={styles.stack}
              onValueChange={setSelectedViewKey}
              value={selectedViewKey}
            >
              <div className={styles.meta}>
                <span>~{data.estimatedTokens} tokens</span>
                {data.summaryNote ? <span>Summary note available</span> : null}
              </div>

              {tabViews.length > 1 ? (
                <TabsList
                  className={styles.switcher}
                  aria-label="Page views"
                >
                  {tabViews.map((view) => (
                    <TabsTrigger
                      className={styles.tab}
                      key={view.key}
                      value={view.key}
                    >
                      {view.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              ) : null}

              {selectedViewFlags.length > 0 ? (
                <div className={styles.flags} data-expanded={flagsExpanded}>
                  <div className={styles.flagList}>
                    {visibleFlags.map((flag, index) => (
                      <Badge key={`${flag}-${index}`} tone={flagTone(flag)}>
                        {flag}
                      </Badge>
                    ))}
                  </div>
                  {hiddenFlagCount > 0 || flagsExpanded ? (
                    <Button
                      className={styles.flagToggle}
                      onClick={() => setFlagsExpanded((expanded) => !expanded)}
                      variant="secondary"
                    >
                      {flagsExpanded
                        ? "Show fewer"
                        : `View ${hiddenFlagCount} more`}
                    </Button>
                  ) : null}
                </div>
              ) : null}

              {tabViews.map((view) => (
                <TabsContent
                  className={styles.bodyPanel}
                  forceMount
                  hidden={view.key !== selectedViewKey}
                  key={view.key}
                  value={view.key}
                >
                  <pre className={styles.body}>{view.content}</pre>
                </TabsContent>
              ))}
            </Tabs>
          ) : null}

          {status === "empty" ? (
            <EmptyState eyebrow="Page" title="No representation">
              <p>No extracted representation was returned for this page.</p>
            </EmptyState>
          ) : null}
        </AsyncContentFrame>
      </DialogFrame>
    </Dialog>
  );
}
