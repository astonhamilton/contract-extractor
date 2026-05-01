import { useEffect, useRef, useState } from "react";
import { CorpusLibrarySection } from "@/screens/CorpusScreen/sections/CorpusLibrarySection";
import { CorpusPageRepresentationDialog } from "@/screens/CorpusScreen/blocks/CorpusPageRepresentationDialog";
import { CorpusStageSection } from "@/screens/CorpusScreen/sections/CorpusStageSection";
import { CorpusToolbarSection } from "@/screens/CorpusScreen/sections/CorpusToolbarSection";
import { useCorpusScreenViewModel } from "@/screens/CorpusScreen/CorpusScreen.viewmodel";
import type {
  CorpusRouteActions,
  CorpusRouteState,
} from "@/app/routes/CorpusRoute";
import { ScreenLayout } from "@/ui/layouts/ScreenLayout/ScreenLayout";
import styles from "./CorpusScreen.module.css";

type CorpusScreenProps = {
  routeActions: CorpusRouteActions;
  routeState: CorpusRouteState;
};

export function CorpusScreen({
  routeActions,
  routeState,
}: CorpusScreenProps) {
  const corpus = useCorpusScreenViewModel({ routeActions, routeState });
  const [stageDocumentId, setStageDocumentId] = useState<string | null>(
    routeState.documentId,
  );
  const [stageExiting, setStageExiting] = useState(false);
  const [shelfCollapsed, setShelfCollapsed] = useState(
    () => routeState.documentId !== null,
  );
  const exitTimerRef = useRef<number | null>(null);
  const previousRouteDocumentIdRef = useRef<string | null>(routeState.documentId);
  const selectedDocumentId = corpus.selectedDocument?.id ?? null;
  const routeDocumentId = routeState.documentId ?? null;

  useEffect(() => {
    if (routeDocumentId && routeDocumentId !== previousRouteDocumentIdRef.current) {
      setShelfCollapsed(true);
    }

    if (!routeDocumentId) {
      setShelfCollapsed(false);
    }

    previousRouteDocumentIdRef.current = routeDocumentId;
  }, [routeDocumentId]);

  useEffect(() => {
    if (exitTimerRef.current !== null) {
      window.clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }

    if (selectedDocumentId) {
      setStageDocumentId(selectedDocumentId);
      setStageExiting(false);
      window.requestAnimationFrame(() => {
        document
          .querySelector("[data-corpus-workspace]")
          ?.scrollIntoView({ block: "start" });
      });
      return;
    }

    if (stageDocumentId !== null) {
      setStageExiting(true);
      exitTimerRef.current = window.setTimeout(() => {
        setStageDocumentId(null);
        setStageExiting(false);
        exitTimerRef.current = null;
      }, 230);
    }

    return () => {
      if (exitTimerRef.current !== null) {
        window.clearTimeout(exitTimerRef.current);
        exitTimerRef.current = null;
      }
    };
  }, [selectedDocumentId, stageDocumentId]);

  const stageDocument =
    corpus.selectedDocument ??
    corpus.documents.find((document) => document.id === stageDocumentId) ??
    null;
  const shelfMode = stageDocument ? "active-shelf" : "grid";

  return (
    <ScreenLayout
      contentInset="none"
      header={
        <CorpusToolbarSection
          canNextResultsPage={corpus.resultsPage < corpus.resultsPageCount}
          canPreviousResultsPage={corpus.resultsPage > 1}
          onNextResultsPage={corpus.actions.nextResultsPage}
          onPreviousResultsPage={corpus.actions.previousResultsPage}
          onQueryChange={corpus.actions.setQuery}
          query={corpus.query}
          resultRangeLabel={corpus.resultRangeLabel}
          resultsFetching={corpus.resultsFetching}
          resultsPage={corpus.resultsPage}
          resultsPageCount={corpus.resultsPageCount}
        />
      }
    >
      <div
        className={styles.root}
        data-corpus-workspace
        data-mode={shelfMode}
      >
        <CorpusLibrarySection
          collapsed={shelfCollapsed}
          documents={corpus.filteredDocuments}
          error={corpus.error}
          mode={shelfMode}
          onClearSelection={corpus.actions.clearSelection}
          onSelectDocument={corpus.actions.selectDocument}
          onToggleCollapsed={() => setShelfCollapsed((collapsed) => !collapsed)}
          selectedDocumentId={corpus.selectedDocument?.id ?? stageDocumentId}
          status={corpus.status}
        />
        {stageDocument ? (
          <CorpusStageSection
            activePage={corpus.activePage ?? stageDocument.pages[0] ?? null}
            activePageIndex={corpus.activePageIndex}
            activePagePreviewPending={corpus.activePagePreviewPending}
            document={stageDocument}
            exiting={stageExiting}
            onClearSelection={corpus.actions.clearSelection}
            onOpenPageRepresentation={corpus.actions.openPageRepresentation}
            onPageIndexChange={corpus.actions.setActivePageIndex}
            pagesFetching={corpus.pagesFetching}
          />
        ) : null}
      </div>
      <CorpusPageRepresentationDialog
        canNextPage={corpus.pageRepresentation.canNextPage}
        canPreviousPage={corpus.pageRepresentation.canPreviousPage}
        data={corpus.pageRepresentation.data}
        onClose={corpus.actions.closePageRepresentation}
        onNextPage={corpus.actions.nextPageRepresentation}
        onPreviousPage={corpus.actions.previousPageRepresentation}
        pageCount={corpus.pageRepresentation.pageCount}
        pageNumber={corpus.pageRepresentation.pageNumber}
        status={corpus.pageRepresentation.status}
      />
    </ScreenLayout>
  );
}
