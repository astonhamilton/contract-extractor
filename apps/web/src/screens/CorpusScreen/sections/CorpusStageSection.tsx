import type {
  CorpusDocument,
  CorpusPage,
} from "@/screens/CorpusScreen/CorpusScreen.types";
import { CorpusPageScrubber } from "@/screens/CorpusScreen/blocks/CorpusPageScrubber";
import { CorpusSelectedDocumentAnchor } from "@/screens/CorpusScreen/blocks/CorpusSelectedDocumentAnchor";
import { CorpusSummaryTable } from "@/screens/CorpusScreen/blocks/CorpusSummaryTable";
import { cn } from "@/lib/cn";
import styles from "./CorpusStageSection.module.css";

type CorpusStageSectionProps = {
  activePage: CorpusPage | null;
  activePageIndex: number;
  activePagePreviewPending: boolean;
  exiting?: boolean;
  document: CorpusDocument | null;
  onClearSelection: () => void;
  onOpenPageRepresentation: (pageNumber: number) => void;
  onPageIndexChange: (index: number) => void;
  pagesFetching: boolean;
};

export function CorpusStageSection({
  activePage,
  activePageIndex,
  activePagePreviewPending,
  document,
  exiting = false,
  onClearSelection,
  onOpenPageRepresentation,
  onPageIndexChange,
  pagesFetching,
}: CorpusStageSectionProps) {
  if (!document) {
    return null;
  }

  return (
    <section
      className={cn(styles.root, exiting && styles.exiting)}
      aria-label={`${document.title} stage`}
    >
      <div className={styles.detailBand}>
        <CorpusSelectedDocumentAnchor
          document={document}
          onClearSelection={onClearSelection}
        />
        <CorpusSummaryTable document={document} />
      </div>
      <CorpusPageScrubber
        activePage={activePage}
        activePageIndex={activePageIndex}
        activePagePreviewPending={activePagePreviewPending}
        document={document}
        onOpenRepresentation={onOpenPageRepresentation}
        onPageIndexChange={onPageIndexChange}
        pagesFetching={pagesFetching}
      />
    </section>
  );
}
