import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  calculatePageWindowForPage,
  CORPUS_PAGES_WINDOW_SIZE,
} from "@/domain/corpus/corpusPaging";
import { mapCorpusDocumentPageDetail } from "@/domain/corpus/corpusMappers";
import {
  mapCorpusListDocument,
  mapCorpusSelectedDocument,
} from "@/screens/CorpusScreen/CorpusScreen.adapters";
import type {
  CorpusDocument,
  CorpusStatus,
  CorpusViewModel,
} from "@/screens/CorpusScreen/CorpusScreen.types";
import type { CorpusAsyncStatus } from "@/domain/corpus/corpusTypes";
import type {
  CorpusRouteActions,
  CorpusRouteState,
} from "@/app/routes/CorpusRoute";
import { corpusQueries } from "@/services/corpus/corpusQueries";

type UseCorpusScreenViewModelProps = {
  routeActions: CorpusRouteActions;
  routeState: CorpusRouteState;
};

const CORPUS_LIST_PAGE_SIZE = 25;
const LEGACY_FIXTURE_HASH_SUFFIX = /_([0-9a-f]{8})$/i;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function pageIndexFromRoute(document: CorpusDocument | null, pageNumber: number | null): number {
  if (!document || !pageNumber) {
    return 0;
  }

  const index = document.pages.findIndex((page) => page.pageNumber === pageNumber);
  return index >= 0 ? index : 0;
}

function apiDocumentIdFromRoute(documentId: string): string {
  if (documentId.includes("__")) {
    return documentId;
  }

  return documentId.replace(LEGACY_FIXTURE_HASH_SUFFIX, "__$1");
}

function resultRangeLabel(total: number, page: number, pageSize: number): string {
  if (total === 0) {
    return "0 documents";
  }

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);
  return `${start}-${end} of ${total} documents`;
}

export function useCorpusScreenViewModel({
  routeActions,
  routeState,
}: UseCorpusScreenViewModelProps): CorpusViewModel {
  const [query, setQuery] = useState("");
  const [resultsPage, setResultsPage] = useState(1);
  const [representationPageNumber, setRepresentationPageNumber] = useState<
    number | null
  >(null);

  const documentsQuery = useQuery(
    {
      ...corpusQueries.documents({
        q: query.trim(),
        sort: "seller",
        page: resultsPage,
        pageSize: CORPUS_LIST_PAGE_SIZE,
      }),
      placeholderData: keepPreviousData,
    },
  );
  const selectedDocumentId = routeState.documentId ?? "";
  const apiSelectedDocumentId = selectedDocumentId
    ? apiDocumentIdFromRoute(selectedDocumentId)
    : "";
  const selectedRoutePage = routeState.pageNumber ?? 1;
  const selectedPagesPage = calculatePageWindowForPage(
    selectedRoutePage,
    CORPUS_PAGES_WINDOW_SIZE,
  );
  const documentDetailQuery = useQuery({
    ...corpusQueries.documentDetail(apiSelectedDocumentId),
    enabled: apiSelectedDocumentId.length > 0,
  });
  const documentPagesQuery = useQuery({
    ...corpusQueries.documentPages(apiSelectedDocumentId, {
      page: selectedPagesPage,
      pageSize: CORPUS_PAGES_WINDOW_SIZE,
    }),
    placeholderData: keepPreviousData,
    enabled: apiSelectedDocumentId.length > 0,
  });
  const pageRepresentationQuery = useQuery({
    ...corpusQueries.documentPageDetail(
      apiSelectedDocumentId,
      representationPageNumber ?? 0,
      {
        includeVariants: true,
      },
    ),
    enabled: apiSelectedDocumentId.length > 0 && representationPageNumber !== null,
  });

  const documents = useMemo(
    () => documentsQuery.data?.items.map(mapCorpusListDocument) ?? [],
    [documentsQuery.data?.items],
  );
  const totalDocumentCount = documentsQuery.data?.total ?? documents.length;
  const responsePage = documentsQuery.data?.page ?? resultsPage;
  const responsePageSize =
    documentsQuery.data?.page_size ?? CORPUS_LIST_PAGE_SIZE;
  const resultsPageCount = Math.max(
    1,
    Math.ceil(totalDocumentCount / responsePageSize || 1),
  );
  const error =
    documentsQuery.error instanceof Error
      ? documentsQuery.error.message
      : documentsQuery.isError
        ? "Document data could not be loaded."
        : null;
  const status: CorpusStatus = documentsQuery.isPending
    ? "loading"
    : documentsQuery.isError
      ? "error"
      : documents.length === 0
        ? "empty"
        : "ready";

  const fallbackSelectedDocument = useMemo(
    () =>
      selectedDocumentId
        ? documents.find(
            (document) =>
              document.id === selectedDocumentId ||
              document.id === apiSelectedDocumentId,
          ) ?? null
        : null,
    [apiSelectedDocumentId, documents, selectedDocumentId],
  );
  const selectedDocument = useMemo(() => {
    if (!documentDetailQuery.data) {
      return fallbackSelectedDocument;
    }

    return mapCorpusSelectedDocument({
      detail: documentDetailQuery.data,
      fallback: fallbackSelectedDocument,
      pages: documentPagesQuery.data,
    });
  }, [
    documentDetailQuery.data,
    documentPagesQuery.data,
    fallbackSelectedDocument,
  ]);

  const activePageIndex = pageIndexFromRoute(
    selectedDocument,
    routeState.pageNumber,
  );
  const activePage = selectedDocument?.pages[activePageIndex] ?? null;
  const activePagePreviewPending =
    activePage !== null &&
    !activePage.loaded &&
    !documentPagesQuery.isError;
  const selectedPageCount =
    selectedDocument?.pageCount ?? selectedDocument?.pages.length ?? 0;
  const pageRepresentationData = pageRepresentationQuery.data
    ? mapCorpusDocumentPageDetail(pageRepresentationQuery.data)
    : null;
  const pageRepresentationStatus: CorpusAsyncStatus =
    representationPageNumber === null
      ? "idle"
      : pageRepresentationQuery.isPending
        ? "loading"
        : pageRepresentationQuery.isError
          ? "error"
          : pageRepresentationData?.views.length === 0
            ? "empty"
            : "ready";
  const canPreviousPageRepresentation =
    representationPageNumber !== null && representationPageNumber > 1;
  const canNextPageRepresentation =
    representationPageNumber !== null &&
    selectedPageCount > 0 &&
    representationPageNumber < selectedPageCount;

  function selectDocument(documentId: string): void {
    const document = documents.find((candidate) => candidate.id === documentId);
    routeActions.patchRouteState({
      documentId,
      pageNumber: document?.pages[0]?.pageNumber ?? 1,
    });
  }

  function setActivePageIndex(index: number): void {
    if (!selectedDocument) {
      return;
    }

    const boundedIndex = clamp(index, 0, selectedDocument.pages.length - 1);
    routeActions.patchRouteState({
      documentId: selectedDocument.id,
      pageNumber: selectedDocument.pages[boundedIndex]?.pageNumber ?? null,
    });
  }

  function movePageRepresentation(delta: number): void {
    if (representationPageNumber === null || selectedPageCount === 0) {
      return;
    }

    setRepresentationPageNumber((pageNumber) =>
      pageNumber === null
        ? pageNumber
        : clamp(pageNumber + delta, 1, selectedPageCount),
    );
  }

  return {
    activePage,
    activePageIndex,
    activePagePreviewPending,
    documents,
    error,
    filteredDocuments: documents,
    pagesFetching: documentPagesQuery.isFetching,
    query,
    resultRangeLabel: resultRangeLabel(
      totalDocumentCount,
      responsePage,
      responsePageSize,
    ),
    resultsFetching: documentsQuery.isFetching && !documentsQuery.isPending,
    resultsPage: responsePage,
    resultsPageCount,
    selectedDocument,
    status,
    totalDocumentCount,
    pageRepresentation: {
      canNextPage: canNextPageRepresentation,
      canPreviousPage: canPreviousPageRepresentation,
      data: pageRepresentationData,
      pageCount: selectedPageCount,
      pageNumber: representationPageNumber,
      status: pageRepresentationStatus,
    },
    actions: {
      clearSelection: () =>
        routeActions.patchRouteState({ documentId: null, pageNumber: null }),
      closePageRepresentation: () => setRepresentationPageNumber(null),
      nextResultsPage: () =>
        setResultsPage((page) => Math.min(page + 1, resultsPageCount)),
      nextPageRepresentation: () => movePageRepresentation(1),
      openPageRepresentation: setRepresentationPageNumber,
      previousPageRepresentation: () => movePageRepresentation(-1),
      previousResultsPage: () => setResultsPage((page) => Math.max(page - 1, 1)),
      selectDocument,
      setActivePageIndex,
      setQuery: (value) => {
        setQuery(value);
        setResultsPage(1);
      },
    },
  };
}
