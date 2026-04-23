export type CorpusSummaryApiResponse = {
  document_count: number;
  db_size_mb: number;
  raw_corpus_size_mb: number;
};

export type CorpusDocumentsApiItem = {
  doc_id: string;
  source_filename: string;
  title: string;
  overview: string;
  page_count: number;
  buyer: string | null;
  seller: string | null;
  lifecycle?: string | null;
  order?: string | number | null;
  procurement_stage: string | null;
  primary_document_role: string | null;
  document_map_type: string | null;
};

export type CorpusDocumentsApiResponse = {
  items: CorpusDocumentsApiItem[];
  total: number;
  page: number;
  page_size: number;
};

export type CorpusDocumentDetailApiResponse = {
  document: {
    doc_id: string;
    title: string;
    source_filename: string;
    page_count: number;
  };
  overview: {
    summary: string;
    document_map_type: string | null;
    supports_page_notes: boolean;
  };
  procurement_context: {
    buyer: string | null;
    seller: string | null;
    what_is_being_bought: string | null;
    procurement_category: string | null;
  };
  classification: {
    procurement_stage: string | null;
    primary_document_role: string | null;
    change_kind: string | null;
  };
};

export type CorpusCitationApiResponse = {
  page_number: number;
  snippet: string;
  clause_label: string | null;
};

export type CorpusAnswerNoteApiResponse = {
  answer: string | null;
  citations: CorpusCitationApiResponse[];
};

export type CorpusGoverningNotesApiResponse = {
  identity: CorpusAnswerNoteApiResponse;
  parties: CorpusAnswerNoteApiResponse;
  subject: CorpusAnswerNoteApiResponse;
  term: CorpusAnswerNoteApiResponse;
  economics: CorpusAnswerNoteApiResponse;
  controls: CorpusAnswerNoteApiResponse;
  quality: CorpusAnswerNoteApiResponse;
};

export type CorpusChangeSectionApiResponse = {
  answer: string | null;
  dimensions: string[];
  citations: CorpusCitationApiResponse[];
};

export type CorpusQualitySectionApiResponse = {
  warnings: string[];
  citations: CorpusCitationApiResponse[];
};

export type CorpusChangeKeyClauseApiResponse = {
  label: string;
  summary: string;
};

export type CorpusChangeNotesApiResponse = {
  target_artifact: CorpusAnswerNoteApiResponse;
  change: CorpusChangeSectionApiResponse;
  resulting_state: CorpusAnswerNoteApiResponse;
  quality: CorpusQualitySectionApiResponse;
  key_clauses: CorpusChangeKeyClauseApiResponse[];
};

export type CorpusDocumentNotesApiResponse = {
  document_map_type: string | null;
  governing_notes: CorpusGoverningNotesApiResponse | null;
  change_notes: CorpusChangeNotesApiResponse | null;
};

export type CorpusDocumentPageNoteApiResponse = {
  page_number: number;
  page_role: string | null;
  summary: string;
  key_terms: string[];
  relevance_tags: string[];
  warnings: string[];
};

export type CorpusDocumentPageNotesApiResponse = {
  items: CorpusDocumentPageNoteApiResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type CorpusDocumentPageApiResponse = {
  page_number: number;
  best_representation: string | null;
  available_representations: string[];
  estimated_tokens: number;
  preview: string;
  page_note_available: boolean;
};

export type CorpusDocumentPagesApiResponse = {
  items: CorpusDocumentPageApiResponse[];
  total: number;
  page: number;
  page_size: number;
};

export type CorpusDocumentPageDetailContentApiResponse = {
  representation: string | null;
  source_path: string | null;
  content: string;
  extraction_method: string | null;
  char_count: number;
  ocr_confidence: number | null;
  warnings: string[];
  quality_flags: string[];
  estimated_tokens: number;
  priority: number | null;
  page_role: string | null;
  key_terms: string[];
  relevance_tags: string[];
};

export type CorpusDocumentPageDetailApiResponse = {
  page: CorpusDocumentPageApiResponse;
  best_content: CorpusDocumentPageDetailContentApiResponse;
  variants: CorpusDocumentPageDetailContentApiResponse[];
};

type CorpusDocumentsQuery = {
  q?: string;
  sort?: string;
  page?: number;
  pageSize?: number;
  signal?: AbortSignal;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { signal });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getCorpusSummary(
  signal?: AbortSignal,
): Promise<CorpusSummaryApiResponse> {
  return fetchJson<CorpusSummaryApiResponse>("/corpus/summary", signal);
}

export async function getCorpusDocuments(
  query: CorpusDocumentsQuery = {},
): Promise<CorpusDocumentsApiResponse> {
  const params = new URLSearchParams();
  if (query.q) {
    params.set("q", query.q);
  }
  if (query.sort) {
    params.set("sort", query.sort);
  }
  if (query.page) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }

  const search = params.toString();
  return fetchJson<CorpusDocumentsApiResponse>(
    `/corpus/documents${search ? `?${search}` : ""}`,
    query.signal,
  );
}

export async function getCorpusDocumentDetail(
  docId: string,
  signal?: AbortSignal,
): Promise<CorpusDocumentDetailApiResponse> {
  return fetchJson<CorpusDocumentDetailApiResponse>(
    `/corpus/documents/${encodeURIComponent(docId)}`,
    signal,
  );
}

export async function getCorpusDocumentNotes(
  docId: string,
  signal?: AbortSignal,
): Promise<CorpusDocumentNotesApiResponse> {
  return fetchJson<CorpusDocumentNotesApiResponse>(
    `/corpus/documents/${encodeURIComponent(docId)}/notes`,
    signal,
  );
}

export async function getCorpusDocumentPageNotes(
  docId: string,
  query: { page?: number; pageSize?: number; signal?: AbortSignal } = {},
): Promise<CorpusDocumentPageNotesApiResponse> {
  const params = new URLSearchParams();
  if (query.page) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }
  const search = params.toString();
  return fetchJson<CorpusDocumentPageNotesApiResponse>(
    `/corpus/documents/${encodeURIComponent(docId)}/page-notes${
      search ? `?${search}` : ""
    }`,
    query.signal,
  );
}

export async function getCorpusDocumentPages(
  docId: string,
  query: { page?: number; pageSize?: number; signal?: AbortSignal } = {},
): Promise<CorpusDocumentPagesApiResponse> {
  const params = new URLSearchParams();
  if (query.page) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }
  const search = params.toString();
  return fetchJson<CorpusDocumentPagesApiResponse>(
    `/corpus/documents/${encodeURIComponent(docId)}/pages${
      search ? `?${search}` : ""
    }`,
    query.signal,
  );
}

export async function getCorpusDocumentPageDetail(
  docId: string,
  pageNumber: number,
  query: { includeVariants?: boolean; signal?: AbortSignal } = {},
): Promise<CorpusDocumentPageDetailApiResponse> {
  const params = new URLSearchParams();
  if (query.includeVariants) {
    params.set("include_variants", "true");
  }
  const search = params.toString();
  return fetchJson<CorpusDocumentPageDetailApiResponse>(
    `/corpus/documents/${encodeURIComponent(docId)}/pages/${pageNumber}${
      search ? `?${search}` : ""
    }`,
    query.signal,
  );
}
