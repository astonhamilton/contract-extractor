import { useDeferredValue, useEffect, useMemo, useState } from "react";
import DocumentDetail, {
  type DetailTab,
} from "../components/DocumentDetail";
import DocumentList, {
  type DocumentSortKey,
} from "../components/DocumentList";
import type { CorpusDocument, CorpusDocumentListItem } from "../types";
import useStoredState from "../../../lib/useStoredState";
import {
  getCorpusDocumentDetail,
  getCorpusDocuments,
  getCorpusSummary,
  type CorpusDocumentDetailApiResponse,
  type CorpusDocumentsApiItem,
  type CorpusSummaryApiResponse,
} from "../../../lib/api/corpus";

type CorpusPageProps = {
  documents: CorpusDocument[];
};

const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;

type CorpusUrlState = {
  docId: string;
  tab: DetailTab | null;
  pageNumber: number | null;
};

function normalizeTab(
  rawTab: string | null,
  pageNumber: number | null,
): DetailTab | null {
  if (rawTab === "summary" || rawTab === "pages" || rawTab === "notes") {
    return rawTab;
  }
  if (pageNumber !== null) {
    return "pages";
  }
  return null;
}

function parsePositiveInteger(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) || parsed < 1 ? null : parsed;
}

function readCorpusUrlState(): CorpusUrlState {
  const params = new URLSearchParams(window.location.search);
  const pageNumber = parsePositiveInteger(params.get("page"));
  return {
    docId: params.get("doc")?.trim() ?? "",
    tab: normalizeTab(params.get("tab"), pageNumber),
    pageNumber,
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function mapListItem(item: CorpusDocumentsApiItem): CorpusDocumentListItem {
  return {
    id: item.doc_id,
    title: item.title,
    overview: item.overview,
    pageCount: item.page_count,
    buyer: item.buyer ?? "Unknown buyer",
    seller: item.seller ?? "Unknown seller",
    lifecycle: item.lifecycle ?? item.procurement_stage ?? undefined,
    order:
      (item.order != null ? String(item.order) : null) ??
      item.primary_document_role ??
      undefined,
  };
}

function buildFallbackDocument(
  detail: CorpusDocumentDetailApiResponse,
): CorpusDocument {
  return {
    id: detail.document.doc_id,
    title: detail.document.title,
    sourceFilename: detail.document.source_filename,
    overview: detail.overview.summary,
    procurement: {
      buyer: detail.procurement_context.buyer ?? "—",
      seller: detail.procurement_context.seller ?? "—",
      subject: detail.procurement_context.what_is_being_bought ?? "—",
      category: detail.procurement_context.procurement_category ?? "—",
      summary: "",
    },
    classification: {
      procurementStage: detail.classification.procurement_stage ?? "context",
      primaryDocumentRole: detail.classification.primary_document_role ?? "supporting",
      changeKind: detail.classification.change_kind ?? undefined,
      confidence: 0,
    },
    documentMapType:
      detail.overview.document_map_type === "governing" ||
      detail.overview.document_map_type === "change"
        ? detail.overview.document_map_type
        : "context",
    pageNotes: [],
    pages: [],
  };
}

export default function CorpusPage({ documents }: CorpusPageProps) {
  const [urlState, setUrlState] = useState<CorpusUrlState>(() =>
    typeof window === "undefined" ? { docId: "", tab: null, pageNumber: null } : readCorpusUrlState(),
  );
  const [search, setSearch] = useStoredState("ci.corpus.search", "", {
    storage: "session",
  });
  const [selectedDocumentId, setSelectedDocumentId] = useStoredState(
    "ci.corpus.selectedDocumentId",
    "",
    { storage: "session" },
  );
  const [sortKey, setSortKey] = useStoredState<DocumentSortKey>(
    "ci.corpus.sortKey",
    "seller",
    { storage: "session" },
  );
  const [pageSize, setPageSize] = useStoredState<number>(
    "ci.corpus.pageSize",
    25,
    { storage: "session" },
  );
  const [pageIndex, setPageIndex] = useStoredState<number>(
    "ci.corpus.pageIndex",
    0,
    { storage: "session" },
  );
  const [controlsOpen, setControlsOpen] = useState(false);
  const [summary, setSummary] = useState<CorpusSummaryApiResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);
  const [documentsResponse, setDocumentsResponse] = useState<{
    items: CorpusDocumentListItem[];
    total: number;
    page: number;
    pageSize: number;
  }>({
    items: [],
    total: 0,
    page: 1,
    pageSize,
  });
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState(false);
  const [detail, setDetail] = useState<CorpusDocumentDetailApiResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const deferredSearch = useDeferredValue(search);

  function syncCorpusUrl(nextState: CorpusUrlState): void {
    const params = new URLSearchParams();
    if (nextState.docId) {
      params.set("doc", nextState.docId);
    }
    if (nextState.tab) {
      params.set("tab", nextState.tab);
    }
    if (nextState.tab === "pages" && nextState.pageNumber !== null) {
      params.set("page", String(nextState.pageNumber));
    }
    const nextUrl = `/corpus${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState(null, "", nextUrl);
    setUrlState(nextState);
  }

  function handleSelectDocument(documentId: string): void {
    setSelectedDocumentId(documentId);
    syncCorpusUrl({
      docId: documentId,
      tab: "summary",
      pageNumber: null,
    });
  }

  function handleDeepLinkTabChange(tab: DetailTab): void {
    if (!selectedDocumentId) {
      return;
    }
    syncCorpusUrl({
      docId: selectedDocumentId,
      tab,
      pageNumber: tab === "pages" ? urlState.pageNumber : null,
    });
  }

  function handleDeepLinkPageChange(pageNumber: number | null): void {
    if (!selectedDocumentId) {
      return;
    }
    syncCorpusUrl({
      docId: selectedDocumentId,
      tab: pageNumber !== null ? "pages" : urlState.tab,
      pageNumber,
    });
  }

  useEffect(() => {
    function syncFromUrl(): void {
      setUrlState(readCorpusUrlState());
    }

    window.addEventListener("popstate", syncFromUrl);
    return () => {
      window.removeEventListener("popstate", syncFromUrl);
    };
  }, []);

  useEffect(() => {
    if (urlState.docId && urlState.docId !== selectedDocumentId) {
      setSelectedDocumentId(urlState.docId);
    }
  }, [selectedDocumentId, setSelectedDocumentId, urlState.docId]);

  useEffect(() => {
    const controller = new AbortController();
    setSummaryLoading(true);
    setSummaryError(false);
    getCorpusSummary(controller.signal)
      .then((response) => {
        setSummary(response);
        setSummaryError(false);
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setSummary(null);
        setSummaryError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setSummaryLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setDocumentsLoading(true);
    setDocumentsError(false);
    getCorpusDocuments({
      q: deferredSearch.trim(),
      sort: sortKey,
      page: pageIndex + 1,
      pageSize,
      signal: controller.signal,
    })
      .then((response) =>
        setDocumentsResponse({
          items: response.items.map(mapListItem),
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
        }),
      )
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setDocumentsError(true);
        setDocumentsResponse({
          items: [],
          total: 0,
          page: 1,
          pageSize,
        });
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDocumentsLoading(false);
        }
      });
    return () => controller.abort();
  }, [deferredSearch, pageIndex, pageSize, sortKey]);

  const pageCount = Math.max(
    1,
    Math.ceil(documentsResponse.total / documentsResponse.pageSize || 1),
  );

  useEffect(() => {
    if (pageIndex > pageCount - 1) {
      setPageIndex(Math.max(0, pageCount - 1));
    }
  }, [pageCount, pageIndex, setPageIndex]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setDetail(null);
      setDetailLoading(false);
      return;
    }

    const controller = new AbortController();
    setDetail((current) =>
      current?.document.doc_id === selectedDocumentId ? current : null,
    );
    setDetailLoading(true);
    getCorpusDocumentDetail(selectedDocumentId, controller.signal)
      .then((response) => setDetail(response))
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setDetail(null);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDetailLoading(false);
        }
      });
    return () => controller.abort();
  }, [selectedDocumentId]);

  const selectedMockDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId),
    [documents, selectedDocumentId],
  );

  const isDetailCurrent =
    !!selectedDocumentId && detail?.document.doc_id === selectedDocumentId;
  const isSelectionLoading = !!selectedDocumentId && detailLoading && !isDetailCurrent;

  const selectedDocument = isSelectionLoading
    ? undefined
    : selectedMockDocument ??
      (detail && selectedDocumentId ? buildFallbackDocument(detail) : undefined);

  return (
    <section className="workspace-shell">
      <header className="workspace-header workspace-header-compact">
        {summaryLoading ? (
          <div className="skeleton-line skeleton-line-meta" />
        ) : summaryError ? (
          <p className="section-kicker corpus-meta-line">Corpus · unavailable</p>
        ) : (
          <p className="section-kicker corpus-meta-line">
            Corpus · {summary?.document_count ?? 0} total documents ·{" "}
            {summary ? summary.raw_corpus_size_mb.toFixed(1) : "0.0"} MB
          </p>
        )}
      </header>

      <div className="corpus-layout">
        <section className="panel corpus-finder-panel">
          <div className="finder-toolbar">
            <span className="field-label finder-toolbar-label">
              Search title, buyer, seller, or subject
            </span>
            <div className="finder-search-row">
              <label className="search-field finder-search-field">
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Tyler, road salt, behavioral health..."
                />
              </label>

              <div className="finder-menu-shell">
                <button
                  type="button"
                  className={
                    controlsOpen
                      ? "finder-menu-button finder-menu-button-active"
                      : "finder-menu-button"
                  }
                  onClick={() => setControlsOpen((current) => !current)}
                >
                  Filter / sort
                </button>

                {controlsOpen ? (
                  <div className="finder-menu-popover">
                    <label className="select-field finder-select-field">
                      <span className="field-label">Show</span>
                      <select
                        value={pageSize}
                        onChange={(event) => {
                          setPageSize(Number(event.target.value));
                          setPageIndex(0);
                          setControlsOpen(false);
                        }}
                      >
                        {PAGE_SIZE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option} documents
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="select-field finder-select-field">
                      <span className="field-label">Sort</span>
                      <select
                        value={sortKey}
                        onChange={(event) => {
                          setSortKey(event.target.value as DocumentSortKey);
                          setPageIndex(0);
                          setControlsOpen(false);
                        }}
                      >
                        <option value="name">Name</option>
                        <option value="page_count">Page count</option>
                        <option value="seller">Seller</option>
                        <option value="buyer">Buyer</option>
                      </select>
                    </label>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="finder-controls">
              <div className="finder-pagination">
                <span className="muted-meta">
                  {documentsResponse.total === 0
                    ? "0 results"
                    : `${(documentsResponse.page - 1) * documentsResponse.pageSize + 1}-${Math.min(
                        documentsResponse.total,
                        documentsResponse.page * documentsResponse.pageSize,
                      )} of ${documentsResponse.total}`}
                </span>
                <div className="finder-pagination-actions">
                  {documentsLoading ? (
                    <div className="finder-live-indicator" aria-live="polite">
                      <span className="live-indicator-dot" />
                      <span>Updating</span>
                    </div>
                  ) : null}
                  <div className="page-pagination">
                    <button
                      type="button"
                      className="page-nav-button"
                      onClick={() => setPageIndex((current) => Math.max(0, current - 1))}
                      disabled={pageIndex === 0}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className="page-nav-button"
                      onClick={() =>
                        setPageIndex((current) => Math.min(pageCount - 1, current + 1))
                      }
                      disabled={pageIndex >= pageCount - 1}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <DocumentList
            documents={documentsResponse.items}
            selectedDocumentId={selectedDocument?.id ?? ""}
            onSelectDocument={handleSelectDocument}
            sortKey={sortKey}
            loading={documentsLoading}
            emptyState={
              documentsError
                ? {
                    kicker: "Unavailable",
                    title: "Corpus data could not be loaded",
                    copy: "Check that the API is running, then reload the page.",
                  }
                : {
                    kicker: "No matches",
                    title: "Nothing is in view",
                    copy: "Try a broader search.",
                  }
            }
          />
        </section>

        {selectedDocument ? (
          <DocumentDetail
            document={selectedDocument}
            detail={detail}
            loading={detailLoading && isDetailCurrent}
            deepLinkedTab={
              urlState.docId && urlState.docId === selectedDocument.id
                ? urlState.tab
                : null
            }
            deepLinkedPageNumber={
              urlState.docId && urlState.docId === selectedDocument.id
                ? urlState.pageNumber
                : null
            }
            onTabChange={handleDeepLinkTabChange}
            onPageDialogChange={handleDeepLinkPageChange}
          />
        ) : isSelectionLoading ? (
          <section className="panel document-detail-panel">
            <div className="detail-loading-state">
              <div className="skeleton-line skeleton-line-detail-kicker" />
              <div className="skeleton-line skeleton-line-detail-title" />
              <div className="skeleton-line skeleton-line-detail-body" />
              <div className="skeleton-line skeleton-line-detail-body skeleton-line-body-short" />
              <div className="detail-loading-grid">
                <div className="detail-section">
                  <div className="skeleton-line skeleton-line-detail-kicker" />
                  <div className="skeleton-line skeleton-line-detail-body" />
                  <div className="skeleton-line skeleton-line-detail-body skeleton-line-body-short" />
                </div>
                <div className="detail-section">
                  <div className="skeleton-line skeleton-line-detail-kicker" />
                  <div className="skeleton-line skeleton-line-detail-body" />
                  <div className="skeleton-line skeleton-line-detail-body skeleton-line-body-short" />
                </div>
              </div>
            </div>
          </section>
        ) : (
          <section className="panel document-detail-panel detail-empty-panel">
            <div className="detail-empty-state">
              <div className="detail-empty-etch" aria-hidden="true">
                <span className="detail-empty-glyph">◫</span>
              </div>
              <div className="detail-empty-copy">
                <p className="section-kicker">Selected document</p>
                <h3>
                  {documentsError
                    ? "Corpus data is unavailable"
                    : documentsResponse.total === 0
                    ? "No documents match the current search"
                    : "Select a document from the left to view it"}
                </h3>
                <p className="detail-lede">
                  {documentsError
                    ? "Start the API and reload the page to inspect live corpus records."
                    : documentsResponse.total === 0
                    ? "Clear or broaden the search to inspect a document."
                    : "Search, sort, and browse the corpus, then open a document to inspect its notes, cliff notes, and pages."}
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
    </section>
  );
}
