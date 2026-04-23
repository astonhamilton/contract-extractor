PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ci_documents (
    doc_id TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    source_pdf_path TEXT NOT NULL,
    source_pdf_size_bytes INTEGER,
    sha256 TEXT,
    page_count INTEGER NOT NULL DEFAULT 0,
    has_text_layer INTEGER,
    quality_flags_json TEXT NOT NULL DEFAULT '[]',
    processing_status TEXT,
    processing_updated_at TEXT,
    processing_version TEXT,
    processing_error TEXT,
    processing_warnings_json TEXT NOT NULL DEFAULT '[]',
    normalized_document_path TEXT,
    procurement_context_path TEXT,
    procurement_context_status TEXT,
    procurement_context_updated_at TEXT,
    classification_path TEXT,
    classification_status TEXT,
    classification_updated_at TEXT,
    governing_domain_notes_path TEXT,
    governing_domain_notes_status TEXT,
    governing_domain_notes_updated_at TEXT,
    change_extraction_path TEXT,
    change_extraction_status TEXT,
    change_extraction_updated_at TEXT,
    page_notes_path TEXT,
    page_notes_status TEXT,
    page_notes_updated_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ci_document_artifacts (
    artifact_id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    path TEXT NOT NULL,
    description TEXT,
    UNIQUE(doc_id, path),
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_document_page_variants (
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    representation TEXT NOT NULL,
    priority INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    content TEXT NOT NULL,
    extraction_method TEXT,
    char_count INTEGER NOT NULL DEFAULT 0,
    ocr_char_count INTEGER NOT NULL DEFAULT 0,
    ocr_confidence REAL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    quality_flags_json TEXT NOT NULL DEFAULT '[]',
    estimated_tokens INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_id, page_number, representation),
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_procurement_context (
    doc_id TEXT PRIMARY KEY,
    is_procurement_related INTEGER,
    buyer TEXT,
    seller TEXT,
    what_is_being_bought TEXT,
    procurement_category TEXT,
    context_summary TEXT,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_classification (
    doc_id TEXT PRIMARY KEY,
    procurement_stage TEXT NOT NULL,
    primary_document_role TEXT NOT NULL,
    change_kind TEXT,
    confidence REAL NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    evidence_pages_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    raw_json TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_governing_notes (
    doc_id TEXT PRIMARY KEY,
    identity_answer TEXT,
    parties_answer TEXT,
    subject_answer TEXT,
    term_answer TEXT,
    economics_answer TEXT,
    controls_answer TEXT,
    quality_warnings_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_change_notes (
    doc_id TEXT PRIMARY KEY,
    target_artifact_answer TEXT,
    change_answer TEXT,
    resulting_state_answer TEXT,
    dimensions_json TEXT NOT NULL DEFAULT '[]',
    quality_warnings_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_change_key_clauses (
    key_clause_id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL,
    label TEXT NOT NULL,
    summary TEXT NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_citations (
    citation_id INTEGER PRIMARY KEY,
    doc_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    domain TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    snippet TEXT NOT NULL,
    clause_label TEXT,
    ordinal INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ci_page_notes (
    doc_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    page_role TEXT,
    summary TEXT NOT NULL,
    key_terms_json TEXT NOT NULL DEFAULT '[]',
    relevance_tags_json TEXT NOT NULL DEFAULT '[]',
    warnings_json TEXT NOT NULL DEFAULT '[]',
    raw_json TEXT NOT NULL,
    PRIMARY KEY (doc_id, page_number),
    FOREIGN KEY (doc_id) REFERENCES ci_documents(doc_id) ON DELETE CASCADE
);
