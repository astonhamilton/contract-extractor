import { Layers3, Search } from "lucide-react";
import { PaginationStatusControls } from "@/ui/patterns/PaginationStatusControls/PaginationStatusControls";
import { TextField } from "@/ui/primitives/TextField/TextField";
import styles from "./CorpusToolbarSection.module.css";

type CorpusToolbarSectionProps = {
  canNextResultsPage: boolean;
  canPreviousResultsPage: boolean;
  onNextResultsPage: () => void;
  onPreviousResultsPage: () => void;
  onQueryChange: (query: string) => void;
  query: string;
  resultRangeLabel: string;
  resultsFetching: boolean;
  resultsPage: number;
  resultsPageCount: number;
};

export function CorpusToolbarSection({
  canNextResultsPage,
  canPreviousResultsPage,
  onNextResultsPage,
  onPreviousResultsPage,
  onQueryChange,
  query,
  resultRangeLabel,
  resultsFetching,
  resultsPage,
  resultsPageCount,
}: CorpusToolbarSectionProps) {
  return (
    <header className={styles.root}>
      <div className={styles.titleGroup}>
        <div className={styles.mark}>
          <Layers3 size={18} aria-hidden="true" />
        </div>
        <div>
          <p className={styles.eyebrow}>Document Repository</p>
          <h1 className={styles.title}>Browse Documents</h1>
        </div>
      </div>

      <label className={styles.search}>
        <Search size={16} aria-hidden="true" />
        <TextField
          aria-label="Search documents"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search documents"
          value={query}
        />
      </label>

      <div className={styles.resultsBar} aria-label="Document result paging">
        <span className={styles.resultRange}>{resultRangeLabel}</span>
        <PaginationStatusControls
          canGoNext={canNextResultsPage}
          canGoPrevious={canPreviousResultsPage}
          label={`Page ${resultsPage} of ${resultsPageCount}`}
          loading={resultsFetching}
          loadingLabel="Loading document results"
          onNext={onNextResultsPage}
          onPrevious={onPreviousResultsPage}
          variant="ghost"
        />
      </div>
    </header>
  );
}
