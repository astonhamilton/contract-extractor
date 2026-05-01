import type {
  CorpusDocument,
  CorpusStatus,
} from "@/screens/CorpusScreen/CorpusScreen.types";
import { CorpusDocumentTile } from "@/screens/CorpusScreen/blocks/CorpusDocumentTile";
import { ChevronDown, ChevronUp } from "lucide-react";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./CorpusLibrarySection.module.css";

type CorpusLibraryMode = "grid" | "active-shelf";

type CorpusLibrarySectionProps = {
  collapsed: boolean;
  documents: CorpusDocument[];
  error: string | null;
  mode: CorpusLibraryMode;
  onClearSelection: () => void;
  onSelectDocument: (documentId: string) => void;
  onToggleCollapsed: () => void;
  selectedDocumentId: string | null;
  status: CorpusStatus;
};

export function CorpusLibrarySection({
  collapsed,
  documents,
  error,
  mode,
  onClearSelection,
  onSelectDocument,
  onToggleCollapsed,
  selectedDocumentId,
  status,
}: CorpusLibrarySectionProps) {
  const activeShelf = mode === "active-shelf";
  const shelfCollapsed = activeShelf && collapsed;

  if (status === "loading") {
    return (
      <section className={styles.message} aria-label="Documents loading">
        Loading documents.
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className={styles.message} aria-label="Document data error">
        Document data could not be loaded. {error}
      </section>
    );
  }

  if (documents.length === 0) {
    return (
      <section className={styles.message} aria-label="Documents empty state">
        No documents match this search.
      </section>
    );
  }

  return (
    <section
      className={styles.root}
      data-collapsed={shelfCollapsed ? "true" : undefined}
      data-mode={mode}
      aria-label="Document grid"
    >
      {activeShelf ? (
        <div className={styles.shelfHeader}>
          <div>
            <p>Available documents</p>
            {shelfCollapsed ? (
              <span>{documents.length} documents available.</span>
            ) : null}
          </div>
          <IconButton
            aria-expanded={!shelfCollapsed}
            aria-label={
              shelfCollapsed
                ? "Expand available documents"
                : "Collapse available documents"
            }
            onClick={onToggleCollapsed}
            tooltip={
              shelfCollapsed
                ? "Expand available documents"
                : "Collapse available documents"
            }
          >
            {shelfCollapsed ? (
              <ChevronDown size={16} aria-hidden="true" />
            ) : (
              <ChevronUp size={16} aria-hidden="true" />
            )}
          </IconButton>
        </div>
      ) : null}
      <div className={styles.grid} aria-hidden={shelfCollapsed ? "true" : undefined}>
        {documents.map((document) => (
          <CorpusDocumentTile
            compact={activeShelf}
            document={document}
            key={document.id}
            onClearSelection={onClearSelection}
            onSelectDocument={onSelectDocument}
            selected={document.id === selectedDocumentId}
          />
        ))}
      </div>
    </section>
  );
}
