export type CorpusAsyncStatus = "idle" | "loading" | "error" | "empty" | "ready";

export type CorpusPageContentView = {
  key: string;
  label: string;
  representation: string | null;
  sourcePath: string | null;
  content: string;
  estimatedTokens: number;
  warnings: string[];
  qualityFlags: string[];
  pageRole: string | null;
  keyTerms: string[];
  relevanceTags: string[];
};

export type CorpusPageDetailView = {
  pageNumber: number;
  bestRepresentation: string;
  estimatedTokens: number;
  summaryNote: CorpusPageContentView | null;
  views: CorpusPageContentView[];
};
