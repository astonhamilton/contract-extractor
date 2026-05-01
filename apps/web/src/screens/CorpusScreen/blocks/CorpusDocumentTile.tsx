import { useEffect, useState } from "react";
import { BookOpen, CornerUpLeft, FileWarning } from "lucide-react";
import type { CorpusDocument } from "@/screens/CorpusScreen/CorpusScreen.types";
import { cn } from "@/lib/cn";
import styles from "./CorpusDocumentTile.module.css";

type CorpusDocumentTileProps = {
  compact?: boolean;
  document: CorpusDocument;
  onClearSelection: () => void;
  onSelectDocument: (documentId: string) => void;
  selected: boolean;
};

export function CorpusDocumentTile({
  compact = false,
  document,
  onClearSelection,
  onSelectDocument,
  selected,
}: CorpusDocumentTileProps) {
  const hasCoverUrl = document.coverUrl.trim().length > 0;
  const [coverStatus, setCoverStatus] = useState<"loading" | "loaded" | "failed">(
    hasCoverUrl ? "loading" : "failed",
  );

  useEffect(() => {
    if (!hasCoverUrl) {
      setCoverStatus("failed");
      return;
    }

    setCoverStatus("loading");

    const stallTimer = window.setTimeout(() => {
      setCoverStatus((status) => (status === "loading" ? "failed" : status));
    }, 5000);

    return () => {
      window.clearTimeout(stallTimer);
    };
  }, [document.coverUrl, hasCoverUrl]);

  const coverLoaded = coverStatus === "loaded";
  const coverFailed = !hasCoverUrl || coverStatus === "failed";

  return (
    <button
      aria-pressed={selected}
      className={cn(
        styles.root,
        compact && styles.compact,
        selected && styles.selected,
      )}
      onClick={() =>
        selected ? onClearSelection() : onSelectDocument(document.id)
      }
      type="button"
    >
      <span className={styles.coverWrap}>
        <span className={styles.pageEdges} aria-hidden="true" />
        <span
          className={cn(
            styles.coverPlaceholder,
            coverFailed && styles.coverPlaceholderFailed,
            coverLoaded && styles.coverPlaceholderHidden,
          )}
          aria-hidden="true"
        >
          {coverFailed ? (
            <>
              <FileWarning size={22} aria-hidden="true" />
              <span>Preview unavailable</span>
            </>
          ) : (
            <>
              <span />
              <span />
              <span />
              <span />
              <span />
            </>
          )}
        </span>
        {coverFailed || !hasCoverUrl ? null : (
          <img
            alt=""
            className={cn(styles.cover, coverLoaded && styles.coverLoaded)}
            draggable={false}
            onError={() => setCoverStatus("failed")}
            onLoad={() => setCoverStatus("loaded")}
            src={document.coverUrl}
          />
        )}
      </span>
      <span className={styles.meta}>
        <span className={styles.title}>{document.title}</span>
        <span className={styles.footer}>
          <span>
            <BookOpen size={13} aria-hidden="true" />
            {document.pageCount} pages
          </span>
          {selected ? (
            <span>
              <CornerUpLeft size={13} aria-hidden="true" />
              opened
            </span>
          ) : null}
        </span>
      </span>
    </button>
  );
}
