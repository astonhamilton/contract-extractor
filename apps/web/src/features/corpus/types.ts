export type CitationView = {
  pageNumber: number;
  snippet: string;
};

export type DomainAnswer = {
  label: string;
  answer: string;
  citations: CitationView[];
};

export type GoverningNotesView = {
  identity: DomainAnswer[];
  parties: DomainAnswer[];
  subject: DomainAnswer[];
  term: DomainAnswer[];
  economics: DomainAnswer[];
  controls: DomainAnswer[];
  quality: DomainAnswer[];
};

export type ChangeKeyClauseView = {
  label: string;
  summary: string;
  citations: CitationView[];
};

export type ChangeNotesView = {
  targetArtifact: DomainAnswer;
  change: DomainAnswer & { dimensions: string[] };
  resultingState: DomainAnswer;
  keyClauses: ChangeKeyClauseView[];
};

export type PageNoteView = {
  pageNumber: number;
  pageRole: string;
  summary: string;
  keyTerms: string[];
  relevanceTags: string[];
};

export type DocumentPageView = {
  pageNumber: number;
  representation: string;
  sourcePath: string;
  qualityFlags: string[];
  excerpt: string;
};

export type CorpusDocument = {
  id: string;
  title: string;
  sourceFilename: string;
  overview: string;
  procurement: {
    buyer: string;
    seller: string;
    subject: string;
    category: string;
    summary: string;
  };
  classification: {
    procurementStage: string;
    primaryDocumentRole: string;
    changeKind?: string;
    confidence: number;
  };
  documentMapType: "governing" | "change" | "context";
  governingNotes?: GoverningNotesView;
  changeNotes?: ChangeNotesView;
  pageNotes: PageNoteView[];
  pages: DocumentPageView[];
};

export type CorpusDocumentListItem = {
  id: string;
  title: string;
  overview: string;
  pageCount: number;
  buyer: string;
  seller: string;
  lifecycle?: string;
  order?: string;
};
