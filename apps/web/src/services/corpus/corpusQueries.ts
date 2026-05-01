import {
  getCorpusDocumentDetail,
  getCorpusDocumentNotes,
  getCorpusDocumentPageDetail,
  getCorpusDocumentPageNotes,
  getCorpusDocumentPages,
  getCorpusDocuments,
  getCorpusSummary,
  type CorpusDocumentsQuery,
  type CorpusPageDetailQuery,
  type CorpusPagedQuery,
} from "@/services/corpus/corpusApi";

export const corpusKeys = {
  all: ["corpus"] as const,
  summary: () => [...corpusKeys.all, "summary"] as const,
  documents: (query: Omit<CorpusDocumentsQuery, "signal">) =>
    [...corpusKeys.all, "documents", query] as const,
  documentDetail: (documentId: string) =>
    [...corpusKeys.all, "documents", documentId] as const,
  documentNotes: (documentId: string) =>
    [...corpusKeys.documentDetail(documentId), "notes"] as const,
  documentPages: (documentId: string, query: Omit<CorpusPagedQuery, "signal">) =>
    [...corpusKeys.documentDetail(documentId), "pages", query] as const,
  documentPageNotes: (
    documentId: string,
    query: Omit<CorpusPagedQuery, "signal">,
  ) => [...corpusKeys.documentDetail(documentId), "page-notes", query] as const,
  documentPageDetail: (
    documentId: string,
    pageNumber: number,
    query: Omit<CorpusPageDetailQuery, "signal">,
  ) =>
    [...corpusKeys.documentDetail(documentId), "pages", pageNumber, query] as const,
};

export const corpusQueries = {
  summary: () => ({
    queryKey: corpusKeys.summary(),
    queryFn: ({ signal }: { signal: AbortSignal }) => getCorpusSummary(signal),
  }),
  documents: (query: Omit<CorpusDocumentsQuery, "signal">) => ({
    queryKey: corpusKeys.documents(query),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocuments({ ...query, signal }),
  }),
  documentDetail: (documentId: string) => ({
    queryKey: corpusKeys.documentDetail(documentId),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocumentDetail(documentId, signal),
    enabled: documentId.length > 0,
  }),
  documentNotes: (documentId: string) => ({
    queryKey: corpusKeys.documentNotes(documentId),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocumentNotes(documentId, signal),
    enabled: documentId.length > 0,
  }),
  documentPages: (
    documentId: string,
    query: Omit<CorpusPagedQuery, "signal">,
  ) => ({
    queryKey: corpusKeys.documentPages(documentId, query),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocumentPages(documentId, { ...query, signal }),
    enabled: documentId.length > 0,
  }),
  documentPageNotes: (
    documentId: string,
    query: Omit<CorpusPagedQuery, "signal">,
  ) => ({
    queryKey: corpusKeys.documentPageNotes(documentId, query),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocumentPageNotes(documentId, { ...query, signal }),
    enabled: documentId.length > 0,
  }),
  documentPageDetail: (
    documentId: string,
    pageNumber: number,
    query: Omit<CorpusPageDetailQuery, "signal">,
  ) => ({
    queryKey: corpusKeys.documentPageDetail(documentId, pageNumber, query),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getCorpusDocumentPageDetail(documentId, pageNumber, { ...query, signal }),
    enabled: documentId.length > 0 && pageNumber > 0,
  }),
};
