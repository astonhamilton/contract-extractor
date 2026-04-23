import { useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import type { CorpusDocument } from "../types";
import useStoredState from "../../../lib/useStoredState";
import {
  getCorpusDocumentNotes,
  getCorpusDocumentPageDetail,
  getCorpusDocumentPageNotes,
  getCorpusDocumentPages,
  type CorpusAnswerNoteApiResponse,
  type CorpusChangeKeyClauseApiResponse,
  type CorpusChangeNotesApiResponse,
  type CorpusDocumentDetailApiResponse,
  type CorpusDocumentNotesApiResponse,
  type CorpusDocumentPageApiResponse,
  type CorpusDocumentPageDetailApiResponse,
  type CorpusDocumentPageDetailContentApiResponse,
  type CorpusDocumentPageNotesApiResponse,
  type CorpusDocumentPagesApiResponse,
  type CorpusGoverningNotesApiResponse,
  type CorpusQualitySectionApiResponse,
} from "../../../lib/api/corpus";

type DocumentDetailProps = {
  document: CorpusDocument;
  detail?: CorpusDocumentDetailApiResponse | null;
  loading?: boolean;
  deepLinkedTab?: DetailTab | null;
  deepLinkedPageNumber?: number | null;
  onTabChange?: (tab: DetailTab) => void;
  onPageDialogChange?: (pageNumber: number | null) => void;
};

export type DetailTab = "summary" | "notes" | "cliff_notes" | "pages";

type PersistedDetailState = {
  pageWindowIndex: number;
  cliffNoteWindowIndex: number;
};

type ActiveNoteDialog = {
  title: string;
  body: string;
} | null;

type ActivePageDialog = {
  pageNumber: number;
  selectedRepresentation: string;
} | null;

type CliffNotesCacheEntry = {
  page: number;
  pageSize: number;
  total: number;
  items: Array<{
    pageNumber: number;
    pageRole: string;
    summary: string;
    relevanceTags: string[];
    warnings: string[];
  }>;
};

type PagesCacheEntry = {
  page: number;
  pageSize: number;
  total: number;
  items: CorpusDocumentPageApiResponse[];
};

const PAGE_WINDOW_SIZE = 10;
const SHOW_CLIFF_NOTES_TAB = false;

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ");
}

function stageTone(document: CorpusDocument): string {
  if (document.classification.procurementStage === "contracting") {
    return "tone-governing";
  }
  if (document.classification.procurementStage === "active_change") {
    return "tone-change";
  }
  return "tone-context";
}

function stageLabel(document: CorpusDocument): string {
  if (document.classification.procurementStage === "contracting") {
    return "Governing";
  }
  if (document.classification.procurementStage === "active_change") {
    return "Change";
  }
  return "Context";
}

function formatSectionTitle(value: string): string {
  return value.replace(/_/g, " ");
}

function noteQuestionForSection(title: string): string {
  switch (title) {
    case "Identity":
      return "What kind of document is this, and what is it doing?";
    case "Parties":
      return "Who are the main parties involved?";
    case "Subject":
      return "What is being bought, governed, or described here?";
    case "Term":
      return "What does this document say about timing, duration, or renewal?";
    case "Economics":
      return "What does this document say about money, pricing, or payment terms?";
    case "Controls":
      return "What controls, obligations, or protections matter here?";
    case "Quality":
      return "What caveats or cautions should you keep in mind?";
    case "Target artifact":
      return "Which agreement or arrangement is this document changing?";
    case "Change":
      return "What changed in the arrangement?";
    case "Resulting state":
      return "What does the arrangement look like after this change?";
    case "Warnings":
      return "What should you be careful about when using these notes?";
    default:
      return title;
  }
}

function noteDialogTitle(title: string): string {
  return `${title} - ${noteQuestionForSection(title)}`;
}

function defaultDetailState(): PersistedDetailState {
  return {
    pageWindowIndex: 0,
    cliffNoteWindowIndex: 0,
  };
}

function AnswerNoteBlock({
  note,
  title,
  onOpenNote,
}: {
  note: CorpusAnswerNoteApiResponse;
  title: string;
  onOpenNote: (title: string, body: string) => void;
}) {
  return (
    <section className="detail-section">
      <div className="detail-section-heading">
        <p className="section-kicker">
          {title} - {noteQuestionForSection(title)}
        </p>
      </div>
      <article className="note-block">
        <button
          type="button"
          className="note-answer-button"
          onClick={() => onOpenNote(noteDialogTitle(title), note.answer ?? "—")}
        >
          <p className="note-answer">{note.answer ?? "—"}</p>
        </button>
        <div className="citation-stack">
          {note.citations.map((citation) => (
            <div
              key={`${title}-${citation.page_number}-${citation.snippet}`}
              className="citation-chip"
            >
              <p className="citation-heading">
                Extract from document supporting notes: Page {citation.page_number}
              </p>
              <blockquote className="citation-quote">
                {citation.snippet}
              </blockquote>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function GoverningNotesPanel({
  notes,
  onOpenNote,
}: {
  notes: CorpusGoverningNotesApiResponse;
  onOpenNote: (title: string, body: string) => void;
}) {
  const orderedSections: Array<[string, CorpusAnswerNoteApiResponse]> = [
    ["Identity", notes.identity],
    ["Parties", notes.parties],
    ["Subject", notes.subject],
    ["Term", notes.term],
    ["Economics", notes.economics],
    ["Controls", notes.controls],
    ["Quality", notes.quality],
  ];

  return (
    <div className="detail-section-stack">
      {orderedSections.map(([title, note]) => (
        <AnswerNoteBlock
          key={title}
          title={title}
          note={note}
          onOpenNote={onOpenNote}
        />
      ))}
    </div>
  );
}

function ChangeClauseList({
  clauses,
  onOpenNote,
}: {
  clauses: CorpusChangeKeyClauseApiResponse[];
  onOpenNote: (title: string, body: string) => void;
}) {
  return clauses.map((clause) => (
    <article key={clause.label} className="note-block">
      <p className="note-label">{clause.label}</p>
      <button
        type="button"
        className="note-answer-button"
        onClick={() => onOpenNote(clause.label, clause.summary)}
      >
        <p className="note-answer">{clause.summary}</p>
      </button>
    </article>
  ));
}

function QualityWarningsBlock({
  quality,
  onOpenNote,
}: {
  quality: CorpusQualitySectionApiResponse;
  onOpenNote: (title: string, body: string) => void;
}) {
  if (quality.warnings.length === 0 && quality.citations.length === 0) {
    return null;
  }

  return (
    <section className="detail-section">
      <div className="detail-section-heading">
        <p className="section-kicker">
          Warnings - {noteQuestionForSection("Warnings")}
        </p>
      </div>
      <article className="note-block">
        {quality.warnings.length ? (
          <ul className="warning-list">
            {quality.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : (
          <p className="note-answer">No warnings noted.</p>
        )}
        <div className="citation-stack">
          {quality.citations.map((citation) => (
            <div
              key={`quality-${citation.page_number}-${citation.snippet}`}
              className="citation-chip"
            >
              <p className="citation-heading">
                Extract from document supporting notes: Page {citation.page_number}
              </p>
              <blockquote className="citation-quote">
                {citation.snippet}
              </blockquote>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function ChangeNotesPanel({
  notes,
  onOpenNote,
}: {
  notes: CorpusChangeNotesApiResponse;
  onOpenNote: (title: string, body: string) => void;
}) {
  return (
    <div className="detail-section-stack">
      <AnswerNoteBlock
        title="Target artifact"
        note={notes.target_artifact}
        onOpenNote={onOpenNote}
      />

      <section className="detail-section">
        <div className="detail-section-heading">
          <p className="section-kicker">
            Change - {noteQuestionForSection("Change")}
          </p>
          <div className="inline-tag-row">
            {notes.change.dimensions.map((dimension) => (
              <span key={dimension} className="tag tone-change">
                {dimension}
              </span>
            ))}
          </div>
        </div>
        <article className="note-block">
          <button
            type="button"
            className="note-answer-button"
            onClick={() =>
              onOpenNote(noteDialogTitle("Change"), notes.change.answer ?? "—")
            }
          >
            <p className="note-answer">{notes.change.answer ?? "—"}</p>
          </button>
          <div className="citation-stack">
            {notes.change.citations.map((citation) => (
              <div
                key={`change-${citation.page_number}-${citation.snippet}`}
                className="citation-chip"
              >
                <p className="citation-heading">
                  Extract from document supporting notes: Page {citation.page_number}
                </p>
                <blockquote className="citation-quote">
                  {citation.snippet}
                </blockquote>
              </div>
            ))}
          </div>
        </article>
      </section>

      <AnswerNoteBlock
        title="Resulting state"
        note={notes.resulting_state}
        onOpenNote={onOpenNote}
      />

      <QualityWarningsBlock quality={notes.quality} onOpenNote={onOpenNote} />

      <section className="detail-section">
        <div className="detail-section-heading">
          <p className="section-kicker">Key clauses</p>
        </div>
        <div className="key-clause-stack">
          <ChangeClauseList clauses={notes.key_clauses} onOpenNote={onOpenNote} />
        </div>
      </section>
    </div>
  );
}

function fallbackLabel(value: string | null | undefined): string {
  return value ? formatLabel(value) : "—";
}

function hasText(value: string | null | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isMeaningfulExtractedValue(value: string | null | undefined): value is string {
  if (!hasText(value)) {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized !== "unknown seller" && normalized !== "unknown buyer";
}

export default function DocumentDetail({
  document,
  detail,
  loading = false,
  deepLinkedTab = null,
  deepLinkedPageNumber = null,
  onTabChange,
  onPageDialogChange,
}: DocumentDetailProps) {
  const [detailStateByDocument, setDetailStateByDocument] =
    useStoredState<Record<string, PersistedDetailState>>(
      "ci.corpus.documentDetailState",
      {},
      { storage: "session" },
    );
  const [jumpValue, setJumpValue] = useState("");
  const [cliffJumpValue, setCliffJumpValue] = useState("");
  const [notesByDocument, setNotesByDocument] = useState<
    Record<string, CorpusDocumentNotesApiResponse>
  >({});
  const [notesLoadingDocumentId, setNotesLoadingDocumentId] = useState<
    string | null
  >(null);
  const [notesErrorByDocument, setNotesErrorByDocument] = useState<
    Record<string, boolean>
  >({});
  const [pagesByDocument, setPagesByDocument] = useState<
    Record<string, PagesCacheEntry>
  >({});
  const [pagesLoadingDocumentId, setPagesLoadingDocumentId] = useState<
    string | null
  >(null);
  const [pagesErrorByDocument, setPagesErrorByDocument] = useState<
    Record<string, boolean>
  >({});
  const [pageDetailByKey, setPageDetailByKey] = useState<
    Record<string, CorpusDocumentPageDetailApiResponse>
  >({});
  const [pageDetailLoadingKey, setPageDetailLoadingKey] = useState<string | null>(
    null,
  );
  const [pageDetailErrorByKey, setPageDetailErrorByKey] = useState<
    Record<string, boolean>
  >({});
  const [cliffNotesByDocument, setCliffNotesByDocument] = useState<
    Record<string, CliffNotesCacheEntry>
  >({});
  const [cliffNotesLoadingDocumentId, setCliffNotesLoadingDocumentId] =
    useState<string | null>(null);
  const [cliffNotesErrorByDocument, setCliffNotesErrorByDocument] = useState<
    Record<string, boolean>
  >({});
  const [activeNoteDialog, setActiveNoteDialog] = useState<ActiveNoteDialog>(null);
  const [activePageDialog, setActivePageDialog] = useState<ActivePageDialog>(null);

  const persistedState =
    detailStateByDocument[document.id] ?? defaultDetailState();

  const pageWindowCount = Math.max(
    1,
    Math.ceil(
      (pagesByDocument[document.id]?.total ??
        detail?.document.page_count ??
        document.pages.length) / PAGE_WINDOW_SIZE,
    ),
  );
  const cliffNoteWindowCount = Math.max(
    1,
    Math.ceil(
      (cliffNotesByDocument[document.id]?.total ?? document.pageNotes.length) /
        PAGE_WINDOW_SIZE,
    ),
  );

  const tab = deepLinkedTab ?? "summary";
  const pageWindowIndex = Math.min(
    persistedState.pageWindowIndex,
    pageWindowCount - 1,
  );
  const cliffNoteWindowIndex = Math.min(
    persistedState.cliffNoteWindowIndex,
    cliffNoteWindowCount - 1,
  );

  function updateDetailState(patch: Partial<PersistedDetailState>): void {
    setDetailStateByDocument((current) => ({
      ...current,
      [document.id]: {
        ...defaultDetailState(),
        ...current[document.id],
        ...patch,
      },
    }));
  }

  useEffect(() => {
    setJumpValue("");
    setCliffJumpValue("");
    setActiveNoteDialog(null);
    setActivePageDialog(null);
  }, [document.id]);

  useEffect(() => {
    if (tab !== "pages" || deepLinkedPageNumber === null) {
      return;
    }
    const targetWindowIndex = Math.floor((deepLinkedPageNumber - 1) / PAGE_WINDOW_SIZE);
    if (targetWindowIndex !== pageWindowIndex) {
      updateDetailState({ pageWindowIndex: targetWindowIndex });
    }
  }, [deepLinkedPageNumber, pageWindowIndex, tab]);

  useEffect(() => {
    if (tab !== "notes" || notesByDocument[document.id]) {
      return;
    }

    const controller = new AbortController();
    setNotesLoadingDocumentId(document.id);
    setNotesErrorByDocument((current) => ({ ...current, [document.id]: false }));
    getCorpusDocumentNotes(document.id, controller.signal)
      .then((response) => {
        setNotesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setNotesByDocument((current) => ({ ...current, [document.id]: response }));
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setNotesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setNotesErrorByDocument((current) => ({ ...current, [document.id]: true }));
      });

    return () => controller.abort();
  }, [document.id, notesByDocument, tab]);

  useEffect(() => {
    if (tab !== "pages") {
      return;
    }

    const existing = pagesByDocument[document.id];
    if (
      existing &&
      existing.page === pageWindowIndex + 1 &&
      existing.pageSize === PAGE_WINDOW_SIZE
    ) {
      return;
    }

    const controller = new AbortController();
    setPagesLoadingDocumentId(document.id);
    setPagesErrorByDocument((current) => ({ ...current, [document.id]: false }));
    getCorpusDocumentPages(document.id, {
      page: pageWindowIndex + 1,
      pageSize: PAGE_WINDOW_SIZE,
      signal: controller.signal,
    })
      .then((response) => {
        setPagesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setPagesByDocument((current) => ({
          ...current,
          [document.id]: {
            page: response.page,
            pageSize: response.page_size,
            total: response.total,
            items: response.items,
          },
        }));
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setPagesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setPagesErrorByDocument((current) => ({ ...current, [document.id]: true }));
      });

    return () => {
      controller.abort();
      setPagesLoadingDocumentId((current) =>
        current === document.id ? null : current,
      );
    };
  }, [document.id, pageWindowIndex, tab]);

  useEffect(() => {
    if (tab !== "cliff_notes") {
      return;
    }

    const controller = new AbortController();
    setCliffNotesLoadingDocumentId(document.id);
    setCliffNotesErrorByDocument((current) => ({
      ...current,
      [document.id]: false,
    }));
    getCorpusDocumentPageNotes(document.id, {
      page: cliffNoteWindowIndex + 1,
      pageSize: PAGE_WINDOW_SIZE,
      signal: controller.signal,
    })
      .then((response) => {
        setCliffNotesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setCliffNotesByDocument((current) => ({
          ...current,
          [document.id]: {
            page: response.page,
            pageSize: response.page_size,
            total: response.total,
            items: response.items.map((item) => ({
              pageNumber: item.page_number,
              pageRole: item.page_role ?? "page_note",
              summary: item.summary,
              relevanceTags: item.relevance_tags,
              warnings: item.warnings,
            })),
          },
        }));
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setCliffNotesLoadingDocumentId((current) =>
          current === document.id ? null : current,
        );
        setCliffNotesErrorByDocument((current) => ({
          ...current,
          [document.id]: true,
        }));
      });

    return () => controller.abort();
  }, [cliffNoteWindowIndex, document.id, tab]);

  useEffect(() => {
    if (pageWindowIndex !== persistedState.pageWindowIndex) {
      updateDetailState({ pageWindowIndex });
    }
  }, [pageWindowIndex, persistedState.pageWindowIndex]);

  useEffect(() => {
    if (cliffNoteWindowIndex !== persistedState.cliffNoteWindowIndex) {
      updateDetailState({ cliffNoteWindowIndex });
    }
  }, [cliffNoteWindowIndex, persistedState.cliffNoteWindowIndex]);

  const pagedPages = useMemo(
    () => pagesByDocument[document.id]?.items ?? [],
    [document.id, pagesByDocument],
  );
  const pagedCliffNotes = useMemo(() => {
    const liveItems = cliffNotesByDocument[document.id]?.items;
    if (liveItems) {
      return liveItems;
    }
    return document.pageNotes.slice(
      cliffNoteWindowIndex * PAGE_WINDOW_SIZE,
      (cliffNoteWindowIndex + 1) * PAGE_WINDOW_SIZE,
    );
  }, [cliffNoteWindowIndex, cliffNotesByDocument, document.id, document.pageNotes]);
  const liveNotes = notesByDocument[document.id];
  const notesLoading = notesLoadingDocumentId === document.id;
  const notesError = notesErrorByDocument[document.id] ?? false;
  const livePages = pagesByDocument[document.id];
  const pagesLoading = pagesLoadingDocumentId === document.id;
  const pagesError = pagesErrorByDocument[document.id] ?? false;
  const hasNoPageContent =
    !pagesLoading &&
    !pagesError &&
    !!livePages &&
    livePages.total === 0;
  const liveCliffNotes = cliffNotesByDocument[document.id];
  const cliffNotesLoading = cliffNotesLoadingDocumentId === document.id;
  const cliffNotesError = cliffNotesErrorByDocument[document.id] ?? false;
  const hasNoCliffNotes =
    !cliffNotesLoading &&
    !cliffNotesError &&
    ((liveCliffNotes && liveCliffNotes.total === 0) ||
      (!liveCliffNotes && document.pageNotes.length === 0));

  function handleJumpSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetPage = Number.parseInt(jumpValue, 10);
    if (Number.isNaN(targetPage)) {
      return;
    }

    const totalPages = detail?.document.page_count ?? document.pages.length;
    if (targetPage < 1 || targetPage > totalPages) {
      return;
    }

    updateDetailState({
      pageWindowIndex: Math.floor((targetPage - 1) / PAGE_WINDOW_SIZE),
    });
  }

  function handleCliffJumpSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetPage = Number.parseInt(cliffJumpValue, 10);
    if (Number.isNaN(targetPage)) {
      return;
    }

    const targetIndex = document.pageNotes.findIndex(
      (note) => note.pageNumber === targetPage,
    );
    if (targetIndex === -1) {
      return;
    }

    updateDetailState({
      cliffNoteWindowIndex: Math.floor(targetIndex / PAGE_WINDOW_SIZE),
    });
  }

  function openNoteDialog(title: string, body: string): void {
    setActiveNoteDialog({ title, body });
  }

  function closePageDialog(): void {
    setActivePageDialog(null);
    onPageDialogChange?.(null);
  }

  function openPageDialog(pageNumber: number): void {
    const key = `${document.id}:${pageNumber}`;
    const controller = new AbortController();
    setActivePageDialog({
      pageNumber,
      selectedRepresentation: "best",
    });
    onPageDialogChange?.(pageNumber);
    if (pageDetailByKey[key]) {
      return;
    }
    setPageDetailLoadingKey(key);
    setPageDetailErrorByKey((current) => ({ ...current, [key]: false }));
    getCorpusDocumentPageDetail(document.id, pageNumber, {
      includeVariants: true,
      signal: controller.signal,
    })
      .then((response) => {
        setPageDetailByKey((current) => ({ ...current, [key]: response }));
      })
      .catch((error) => {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
        setPageDetailErrorByKey((current) => ({ ...current, [key]: true }));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setPageDetailLoadingKey((current) => (current === key ? null : current));
        }
      });
  }

  useEffect(() => {
    if (tab !== "pages") {
      if (activePageDialog) {
        setActivePageDialog(null);
      }
      return;
    }

    if (deepLinkedPageNumber === null) {
      if (activePageDialog) {
        setActivePageDialog(null);
      }
      return;
    }

    if (activePageDialog?.pageNumber === deepLinkedPageNumber) {
      return;
    }

    openPageDialog(deepLinkedPageNumber);
  }, [activePageDialog?.pageNumber, deepLinkedPageNumber, tab]);

  const activePageKey = activePageDialog
    ? `${document.id}:${activePageDialog.pageNumber}`
    : null;
  const activePageDetail = activePageKey ? pageDetailByKey[activePageKey] : null;
  const activePageLoading = activePageKey
    ? pageDetailLoadingKey === activePageKey
    : false;
  const activePageError = activePageKey
    ? pageDetailErrorByKey[activePageKey] ?? false
    : false;

  const availablePageViews = useMemo(() => {
    if (!activePageDetail) {
      return [];
    }
    const best = {
      key: "best",
      label: "Best view",
      content: activePageDetail.best_content,
    };
    const variants = activePageDetail.variants.map((variant) => ({
      key: variant.representation ?? "variant",
      label:
        variant.representation === "page_notes"
          ? "Cliff note"
          : formatLabel(variant.representation ?? "variant"),
      content: variant,
    }));
    return [best, ...variants];
  }, [activePageDetail]);

  const activePageView = useMemo(() => {
    if (!activePageDetail || !activePageDialog) {
      return null;
    }
    return (
      availablePageViews.find(
        (entry) => entry.key === activePageDialog.selectedRepresentation,
      ) ?? availablePageViews[0] ?? null
    );
  }, [activePageDetail, activePageDialog, availablePageViews]);

  return (
    <section className="panel document-detail-panel">
      <div className="detail-header">
        <div className="detail-header-copy">
          <p className="section-kicker">Selected document</p>
          <h3>{detail?.document.title ?? document.title}</h3>
          <p className="detail-meta-caption">
            Document ID · {detail?.document.doc_id ?? document.id}
          </p>
          <p className="detail-lede">
            {detail?.overview.summary || document.overview}
          </p>
          <p className="detail-meta-caption">
            {detail?.procurement_context.procurement_category ??
              document.procurement.category}{" "}
            · {document.sourceFilename}
          </p>
        </div>
        {loading ? (
          <div className="detail-live-indicator" aria-live="polite">
            <span className="live-indicator-dot" />
            <span>Loading</span>
          </div>
        ) : null}
      </div>

      <div className="tab-row">
        {(
          [
            "summary",
            "pages",
            "notes",
            ...(SHOW_CLIFF_NOTES_TAB ? (["cliff_notes"] as const) : []),
          ] as DetailTab[]
        ).map(
          (entry) => (
            <button
              key={entry}
              type="button"
              className={tab === entry ? "tab-pill tab-pill-active" : "tab-pill"}
              onClick={() => {
                onTabChange?.(entry);
              }}
            >
              {entry === "cliff_notes" ? "Cliff notes" : entry}
            </button>
          ),
        )}
      </div>

      {tab === "summary" ? (
        <div className="detail-content">
          <div className="detail-summary-grid">
            <section className="detail-section">
              <div className="detail-section-heading">
                <p className="section-kicker">
                  At a glance - Procurement context
                </p>
              </div>
              <dl className="definition-list">
                <div>
                  <dt>Buyer</dt>
                  <dd>
                    {isMeaningfulExtractedValue(
                      detail
                        ? detail.procurement_context.buyer
                        : document.procurement.buyer,
                    ) ? (
                      detail
                        ? detail.procurement_context.buyer
                        : document.procurement.buyer
                    ) : (
                      <em>Not found in initial extraction</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Seller</dt>
                  <dd>
                    {isMeaningfulExtractedValue(
                      detail
                        ? detail.procurement_context.seller
                        : document.procurement.seller,
                    ) ? (
                      detail
                        ? detail.procurement_context.seller
                        : document.procurement.seller
                    ) : (
                      <em>Not found in initial extraction</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>What is being bought</dt>
                  <dd>
                    {hasText(
                      detail?.procurement_context.what_is_being_bought ??
                        document.procurement.subject,
                    ) ? (
                      detail?.procurement_context.what_is_being_bought ??
                      document.procurement.subject
                    ) : (
                      <em>Nothing found in initial extraction</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Procurement summary</dt>
                  <dd>
                    {hasText(document.procurement.summary) ? (
                      document.procurement.summary
                    ) : (
                      <em>Nothing found in initial extraction</em>
                    )}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="detail-section">
              <div className="detail-section-heading">
                <p className="section-kicker">
                  Classification - How this file fits the lifecycle
                </p>
              </div>
              <dl className="definition-list">
                <div>
                  <dt>Stage</dt>
                  <dd>
                    {hasText(
                      detail?.classification.procurement_stage ??
                        document.classification.procurementStage,
                    ) ? (
                      fallbackLabel(
                        detail?.classification.procurement_stage ??
                          document.classification.procurementStage,
                      )
                    ) : (
                      <em>N/A</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Primary role</dt>
                  <dd>
                    {hasText(
                      detail?.classification.primary_document_role ??
                        document.classification.primaryDocumentRole,
                    ) ? (
                      fallbackLabel(
                        detail?.classification.primary_document_role ??
                          document.classification.primaryDocumentRole,
                      )
                    ) : (
                      <em>N/A</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Change kind</dt>
                  <dd>
                    {hasText(
                      detail?.classification.change_kind ??
                        document.classification.changeKind,
                    ) ? (
                      fallbackLabel(
                          detail?.classification.change_kind ??
                            document.classification.changeKind,
                        )
                    ) : (
                      <em>N/A</em>
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Document-map surface</dt>
                  <dd>{detail?.overview.document_map_type ?? document.documentMapType}</dd>
                </div>
                <div>
                  <dt>Loaded pages</dt>
                  <dd>
                    <button
                      type="button"
                      className="definition-link-button"
                      onClick={() => onTabChange?.("pages")}
                    >
                      {detail?.document.page_count ?? document.pages.length}
                    </button>
                  </dd>
                </div>
              </dl>
            </section>
          </div>
        </div>
      ) : null}

      {tab === "notes" ? (
        <div className="detail-content">
          {notesLoading && !liveNotes ? (
            <section className="detail-section">
              <div className="detail-section-heading">
                <p className="section-kicker">Notes</p>
              </div>
              <div className="notes-skeleton-stack">
                <div className="skeleton-line skeleton-line-kicker" />
                <div className="skeleton-line skeleton-line-paragraph" />
                <div className="skeleton-line skeleton-line-paragraph short" />
                <div className="skeleton-line skeleton-line-kicker" />
                <div className="skeleton-line skeleton-line-paragraph" />
              </div>
            </section>
          ) : null}

          {liveNotes?.governing_notes ? (
            <GoverningNotesPanel
              notes={liveNotes.governing_notes}
              onOpenNote={openNoteDialog}
            />
          ) : null}

          {liveNotes?.change_notes ? (
            <ChangeNotesPanel
              notes={liveNotes.change_notes}
              onOpenNote={openNoteDialog}
            />
          ) : null}

          {notesError && !liveNotes ? (
            <section className="detail-section">
              <div className="detail-section-heading">
                <p className="section-kicker">Notes unavailable</p>
              </div>
              <p className="prose-block">
                Live notes could not be loaded for this document right now. Retry
                after the API finishes responding.
              </p>
            </section>
          ) : null}

          {!notesLoading &&
          !notesError &&
          liveNotes &&
          liveNotes.document_map_type === null ? (
            <section className="detail-section">
              <div className="detail-section-heading">
                <p className="section-kicker">No specific notes captured</p>
              </div>
              <p className="prose-block">
                Sorry, no specific governing or change notes were captured for this
                document. Use the procurement context and cliff notes to decide
                which pages are worth reading, then open raw page text only for
                the exact fact you need.
              </p>
            </section>
          ) : null}
        </div>
      ) : null}

      {tab === "cliff_notes" ? (
        <div className="detail-content">
          <section className="detail-section">
            <div className="detail-section-heading">
              <p className="section-kicker">Cliff notes</p>
              <span className="muted-meta">
                {(liveCliffNotes?.total ?? document.pageNotes.length).toString()} notes
              </span>
            </div>
            {cliffNotesLoading && !liveCliffNotes ? (
              <div className="notes-skeleton-stack">
                <div className="skeleton-line skeleton-line-kicker" />
                <div className="skeleton-line skeleton-line-paragraph" />
                <div className="skeleton-line skeleton-line-paragraph short" />
              </div>
            ) : null}
            {cliffNotesError && !liveCliffNotes ? (
              <p className="prose-block">
                Cliff notes could not be loaded for this document right now. Try
                again after the API finishes responding.
              </p>
            ) : null}
            {hasNoCliffNotes ? (
              <div className="empty-state detail-empty-inline">
                <h4>No cliff notes available</h4>
                <p>
                  This document is {detail?.document.page_count ?? document.pages.length}{" "}
                  pages long, and no cliff notes were generated for it.
                </p>
                <button
                  type="button"
                  className="page-nav-button"
                  onClick={() => onTabChange?.("pages")}
                >
                  Go straight to pages
                </button>
              </div>
            ) : null}
            {!hasNoCliffNotes &&
            !cliffNotesLoading &&
            !cliffNotesError &&
            liveCliffNotes?.total ? (
              <>
            <div className="page-toolbar">
              <div className="page-pagination">
                <button
                  type="button"
                  className="page-nav-button"
                  onClick={() =>
                    updateDetailState({
                      cliffNoteWindowIndex: Math.max(0, cliffNoteWindowIndex - 1),
                    })
                  }
                  disabled={cliffNoteWindowIndex === 0}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="page-nav-button"
                  onClick={() =>
                    updateDetailState({
                      cliffNoteWindowIndex: Math.min(
                        cliffNoteWindowCount - 1,
                        cliffNoteWindowIndex + 1,
                      ),
                    })
                  }
                  disabled={cliffNoteWindowIndex >= cliffNoteWindowCount - 1}
                >
                  Next
                </button>
              </div>

              <form className="page-jump-form" onSubmit={handleCliffJumpSubmit}>
                <label className="page-jump-label" htmlFor="cliff-note-jump-input">
                  Jump to note page
                </label>
                <div className="page-jump-controls">
                  <input
                    id="cliff-note-jump-input"
                    type="number"
                    min={1}
                    step={1}
                    value={cliffJumpValue}
                    onChange={(event) => setCliffJumpValue(event.target.value)}
                    placeholder="18"
                  />
                  <button type="submit" className="page-nav-button">
                    Go
                  </button>
                </div>
              </form>
            </div>
            <div className="page-note-stack">
              {pagedCliffNotes.map((note) => (
                  <article key={note.pageNumber} className="page-note-card">
                    <div className="page-note-topline">
                      <strong>Page {note.pageNumber}</strong>
                      <span className="tag tone-context">{note.pageRole}</span>
                    </div>
                    <p>{note.summary}</p>
                    <div className="inline-tag-row">
                      {note.relevanceTags.map((tag) => (
                        <span key={tag} className="tag tone-neutral">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
            </div>
              </>
            ) : null}
          </section>
        </div>
      ) : null}

      {tab === "pages" ? (
        <div className="detail-content">
          <section className="detail-section">
            <div className="detail-section-heading">
              <p className="section-kicker">Pages</p>
              <span className="muted-meta">
                Window {pageWindowIndex + 1} of{" "}
                {Math.max(
                  1,
                  Math.ceil(
                    (livePages?.total ?? detail?.document.page_count ?? document.pages.length) /
                      PAGE_WINDOW_SIZE,
                  ),
                )}
              </span>
            </div>

            <div className="page-toolbar">
              <div className="page-pagination">
                <button
                  type="button"
                  className="page-nav-button"
                  onClick={() =>
                    updateDetailState({
                      pageWindowIndex: Math.max(0, pageWindowIndex - 1),
                    })
                  }
                  disabled={pageWindowIndex === 0}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="page-nav-button"
                  onClick={() =>
                    updateDetailState({
                      pageWindowIndex: Math.min(
                        pageWindowCount - 1,
                        pageWindowIndex + 1,
                      ),
                    })
                  }
                  disabled={pageWindowIndex >= pageWindowCount - 1}
                >
                  Next
                </button>
              </div>

              <form className="page-jump-form" onSubmit={handleJumpSubmit}>
                <label className="page-jump-label" htmlFor="page-jump-input">
                  Jump to loaded page
                </label>
                <div className="page-jump-controls">
                  <input
                    id="page-jump-input"
                    type="number"
                    min={1}
                    step={1}
                    value={jumpValue}
                    onChange={(event) => setJumpValue(event.target.value)}
                    placeholder="18"
                  />
                  <button type="submit" className="page-nav-button">
                    Go
                  </button>
                </div>
              </form>
            </div>
            {pagesLoading && !livePages ? (
              <div className="notes-skeleton-stack">
                <div className="skeleton-line skeleton-line-kicker" />
                <div className="skeleton-line skeleton-line-paragraph" />
                <div className="skeleton-line skeleton-line-paragraph short" />
              </div>
            ) : null}
            {pagesError && !livePages ? (
              <p className="prose-block">
                Page tiles could not be loaded for this document right now. Try
                again after the API finishes responding.
              </p>
            ) : null}
            {hasNoPageContent ? (
              <div className="empty-state detail-empty-inline">
                <h4>No page content available</h4>
                <p>
                  This document is {detail?.document.page_count ?? document.pages.length}{" "}
                  pages long, but no page text variants were loaded into the corpus
                  browser for it.
                </p>
              </div>
            ) : null}
            {!hasNoPageContent && !pagesError && livePages ? (
              <div className="page-tile-grid">
                {pagedPages.map((page) => (
                  <button
                    key={page.page_number}
                    type="button"
                    className="page-card page-card-button"
                    onClick={() => openPageDialog(page.page_number)}
                  >
                    <div className="page-card-topline">
                      <strong>Page {page.page_number}</strong>
                      <span className="tag tone-neutral">
                        Best view: {formatLabel(page.best_representation ?? "unknown")}
                      </span>
                    </div>
                    <p className="page-excerpt">{page.preview}</p>
                    <div className="page-card-meta">
                      <span>~{page.estimated_tokens} tokens</span>
                      {page.page_note_available ? <span>Cliff note available</span> : null}
                      {page.available_representations.length > 1 ? (
                        <span>
                          {page.available_representations.length - 1} other version
                          {page.available_representations.length - 1 === 1 ? "" : "s"}
                        </span>
                      ) : null}
                    </div>
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      {activeNoteDialog
        ? createPortal(
            <div
              className="dialog-backdrop"
              role="presentation"
              onClick={() => setActiveNoteDialog(null)}
            >
              <div
                className="dialog-shell"
                role="dialog"
                aria-modal="true"
                aria-label={activeNoteDialog.title}
                onClick={(event) => event.stopPropagation()}
              >
                <div className="dialog-header">
                  <div>
                    <p className="section-kicker">Note</p>
                    <h3>{activeNoteDialog.title}</h3>
                  </div>
                  <button
                    type="button"
                    className="dialog-close"
                    aria-label="Close note"
                    onClick={() => setActiveNoteDialog(null)}
                  >
                    ×
                  </button>
                </div>
                <pre className="dialog-body dialog-body-pre">
                  {activeNoteDialog.body}
                </pre>
              </div>
            </div>,
            window.document.body,
          )
        : null}

      {activePageDialog
        ? createPortal(
            <div
              className="dialog-backdrop"
              role="presentation"
              onClick={closePageDialog}
            >
              <div
                className="dialog-shell dialog-shell-wide"
                role="dialog"
                aria-modal="true"
                aria-label={`Page ${activePageDialog.pageNumber}`}
                onClick={(event) => event.stopPropagation()}
              >
                <div className="dialog-header">
                  <div>
                    <p className="section-kicker">Page inspector</p>
                    <h3>Page {activePageDialog.pageNumber}</h3>
                  </div>
                  <button
                    type="button"
                    className="dialog-close"
                    aria-label="Close page"
                    onClick={closePageDialog}
                  >
                    ×
                  </button>
                </div>

                {activePageLoading && !activePageDetail ? (
                  <div className="notes-skeleton-stack">
                    <div className="skeleton-line skeleton-line-kicker" />
                    <div className="skeleton-line skeleton-line-paragraph" />
                    <div className="skeleton-line skeleton-line-paragraph" />
                  </div>
                ) : null}

                {activePageError && !activePageDetail ? (
                  <p className="prose-block">
                    This page could not be loaded right now. Try again after the API
                    finishes responding.
                  </p>
                ) : null}

                {activePageDetail && activePageView ? (
                  <div className="page-inspector-stack">
                    <div className="page-inspector-meta">
                      <span className="tag tone-neutral">
                        Best view:{" "}
                        {formatLabel(
                          activePageDetail.page.best_representation ?? "unknown",
                        )}
                      </span>
                      <span className="muted-meta">
                        ~{activePageDetail.page.estimated_tokens} tokens
                      </span>
                    </div>

                    <div className="variant-switcher">
                      {availablePageViews.map((view) => (
                        <button
                          key={view.key}
                          type="button"
                          className={
                            activePageDialog.selectedRepresentation === view.key
                              ? "tab-pill tab-pill-active"
                              : "tab-pill"
                          }
                          onClick={() =>
                            setActivePageDialog((current) =>
                              current
                                ? {
                                    ...current,
                                    selectedRepresentation: view.key,
                                  }
                                : current,
                            )
                          }
                        >
                          {view.label}
                        </button>
                      ))}
                    </div>

                    <section className="detail-section">
                      <div className="detail-section-heading">
                        <p className="section-kicker">
                          {activePageView.content.representation === "page_notes"
                            ? "Cliff note"
                            : "Page content"}
                        </p>
                      </div>
                      <pre className="dialog-body dialog-body-pre page-content-block">
                        {activePageView.content.content}
                      </pre>
                    </section>
                  </div>
                ) : null}
              </div>
            </div>,
            window.document.body,
          )
        : null}
    </section>
  );
}
