import { useEffect, useState } from "react";
import { FileWarning, X } from "lucide-react";
import type { CorpusDocument } from "@/screens/CorpusScreen/CorpusScreen.types";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./CorpusSelectedDocumentAnchor.module.css";

type CorpusSelectedDocumentAnchorProps = {
  document: CorpusDocument;
  onClearSelection: () => void;
};

function formatFileSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  if (unitIndex === 0) {
    return `${Math.round(value)} ${units[unitIndex]}`;
  }

  const digits = value >= 10 ? 1 : 2;
  return `${value
    .toFixed(digits)
    .replace(/\.0+$/, "")
    .replace(/(\.\d*[1-9])0+$/, "$1")} ${units[unitIndex]}`;
}

function documentFileMeta(document: CorpusDocument): string {
  const details = ["PDF file"];

  if (document.sourceFileSizeBytes && document.sourceFileSizeBytes > 0) {
    details.push(formatFileSize(document.sourceFileSizeBytes));
  }

  details.push(`${document.pageCount} pages`);
  return details.join(" · ");
}

export function CorpusSelectedDocumentAnchor({
  document,
  onClearSelection,
}: CorpusSelectedDocumentAnchorProps) {
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
    <article className={styles.root}>
      <div className={styles.toolbar}>
        <span>Selected document</span>
        <IconButton aria-label="Close selected document" onClick={onClearSelection}>
          <X size={15} aria-hidden="true" />
        </IconButton>
      </div>
      <div className={styles.coverFrame}>
        <span className={styles.pageEdges} aria-hidden="true" />
        <span
          className={
            coverLoaded
              ? `${styles.coverPlaceholder} ${styles.coverPlaceholderHidden}`
              : coverFailed
                ? `${styles.coverPlaceholder} ${styles.coverPlaceholderFailed}`
                : styles.coverPlaceholder
          }
          aria-hidden="true"
        >
          {coverFailed ? (
            <>
              <FileWarning size={24} aria-hidden="true" />
              <span>Preview unavailable</span>
            </>
          ) : (
            <>
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
            className={`${styles.cover} ${coverLoaded ? styles.coverLoaded : ""}`}
            draggable={false}
            onError={() => setCoverStatus("failed")}
            onLoad={() => setCoverStatus("loaded")}
            src={document.coverUrl}
          />
        )}
      </div>
      <div className={styles.meta}>
        <h2>{document.title}</h2>
        <p>{documentFileMeta(document)}</p>
      </div>
    </article>
  );
}
