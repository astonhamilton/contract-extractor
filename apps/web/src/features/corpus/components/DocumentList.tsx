import { Fragment } from "react";
import type { CorpusDocumentListItem } from "../types";

export type DocumentSortKey = "name" | "page_count" | "seller" | "buyer";

type DocumentListProps = {
  documents: CorpusDocumentListItem[];
  selectedDocumentId: string;
  onSelectDocument: (documentId: string) => void;
  sortKey: DocumentSortKey;
  loading?: boolean;
  emptyState?: {
    kicker: string;
    title: string;
    copy: string;
  };
};

function formatMetaValue(value: string): string {
  return value.replace(/_/g, " ");
}

function caption(document: CorpusDocumentListItem): string {
  return `${document.pageCount} pages · ${document.seller} · ${document.buyer}`;
}

function lifecycleMeta(document: CorpusDocumentListItem): string | null {
  if (!document.lifecycle && !document.order) {
    return null;
  }

  if (document.lifecycle && document.order) {
    return `${formatMetaValue(document.lifecycle)} · ${formatMetaValue(document.order)}`;
  }

  return formatMetaValue(document.lifecycle ?? document.order ?? "");
}

function groupLabel(
  document: CorpusDocumentListItem,
  sortKey: DocumentSortKey,
): string | null {
  if (sortKey === "seller") {
    return document.seller;
  }

  if (sortKey === "buyer") {
    return document.buyer;
  }

  return null;
}

export default function DocumentList({
  documents,
  selectedDocumentId,
  onSelectDocument,
  sortKey,
  loading = false,
  emptyState = {
    kicker: "No matches",
    title: "Nothing is in view",
    copy: "Try a broader search.",
  },
}: DocumentListProps) {
  if (loading && documents.length === 0) {
    return (
      <div className="document-list">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="document-row document-row-skeleton">
            <div className="skeleton-line skeleton-line-title" />
            <div className="skeleton-line skeleton-line-body" />
            <div className="skeleton-line skeleton-line-body skeleton-line-body-short" />
            <div className="skeleton-line skeleton-line-caption" />
          </div>
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="document-list document-list-empty">
        <div className="empty-state">
          <p className="section-kicker">{emptyState.kicker}</p>
          <h4>{emptyState.title}</h4>
          <p>{emptyState.copy}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-list">
      {documents.map((document, index) => {
        const selected = document.id === selectedDocumentId;
        const header = groupLabel(document, sortKey);
        const previousHeader =
          index === 0 ? null : groupLabel(documents[index - 1], sortKey);
        const showHeader = header !== null && header !== previousHeader;

        return (
          <Fragment key={document.id}>
            {showHeader ? (
              <div className="document-group-header">
                <span>{header}</span>
              </div>
            ) : null}
            <button
              type="button"
              className={selected ? "document-row document-row-active" : "document-row"}
              onClick={() => onSelectDocument(document.id)}
            >
              {lifecycleMeta(document) ? (
                <dl className="document-row-metadata">
                  <dt className="document-row-meta-line">{lifecycleMeta(document)}</dt>
                </dl>
              ) : null}
              <h4>{document.title}</h4>
              <p className="document-row-summary">{document.overview}</p>
              <dl className="document-row-metadata">
                <dt className="document-row-caption" title={caption(document)}>
                  {caption(document)}
                </dt>
              </dl>
            </button>
          </Fragment>
        );
      })}
    </div>
  );
}
