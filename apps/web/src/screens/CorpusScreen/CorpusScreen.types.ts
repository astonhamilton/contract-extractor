import type {
  CorpusAsyncStatus,
  CorpusPageDetailView,
} from "@/domain/corpus/corpusTypes";

export type CorpusSummary = {
  parties: string[];
  procurementCategory: string;
  subject: string;
};

export type CorpusPage = {
  pageNumber: number;
  loaded: boolean;
  thumbUrl: string;
  previewUrl: string;
  previewText?: string;
  fullUrl?: string;
  sourcePath: string;
  width?: number;
  height?: number;
};

export type CorpusDocument = {
  id: string;
  title: string;
  sourceFolder: string;
  sourceFileSizeBytes?: number;
  pageCount: number;
  availablePages: number;
  coverUrl: string;
  summary: CorpusSummary;
  pages: CorpusPage[];
};

export type CorpusManifest = {
  generatedBy: string;
  source: string;
  seed: number;
  documents: CorpusDocument[];
};

export type CorpusStatus = "loading" | "ready" | "empty" | "error";

export type CorpusViewModel = {
  activePage: CorpusPage | null;
  activePageIndex: number;
  activePagePreviewPending: boolean;
  documents: CorpusDocument[];
  error: string | null;
  filteredDocuments: CorpusDocument[];
  pagesFetching: boolean;
  query: string;
  resultRangeLabel: string;
  resultsFetching: boolean;
  resultsPage: number;
  resultsPageCount: number;
  selectedDocument: CorpusDocument | null;
  status: CorpusStatus;
  totalDocumentCount: number;
  pageRepresentation: {
    canNextPage: boolean;
    canPreviousPage: boolean;
    data: CorpusPageDetailView | null;
    pageCount: number;
    pageNumber: number | null;
    status: CorpusAsyncStatus;
  };
  actions: {
    clearSelection: () => void;
    closePageRepresentation: () => void;
    nextResultsPage: () => void;
    nextPageRepresentation: () => void;
    openPageRepresentation: (pageNumber: number) => void;
    previousPageRepresentation: () => void;
    previousResultsPage: () => void;
    selectDocument: (documentId: string) => void;
    setActivePageIndex: (index: number) => void;
    setQuery: (query: string) => void;
  };
};
