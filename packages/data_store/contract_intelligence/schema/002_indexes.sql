PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_documents_source_filename
    ON ci_documents(source_filename);

CREATE INDEX IF NOT EXISTS idx_documents_procurement_context_status
    ON ci_documents(procurement_context_status);

CREATE INDEX IF NOT EXISTS idx_documents_classification_status
    ON ci_documents(classification_status);

CREATE INDEX IF NOT EXISTS idx_documents_governing_status
    ON ci_documents(governing_domain_notes_status);

CREATE INDEX IF NOT EXISTS idx_documents_change_status
    ON ci_documents(change_extraction_status);

CREATE INDEX IF NOT EXISTS idx_document_artifacts_doc_id
    ON ci_document_artifacts(doc_id);

CREATE INDEX IF NOT EXISTS idx_document_page_variants_doc_page_priority
    ON ci_document_page_variants(doc_id, page_number, priority);

CREATE INDEX IF NOT EXISTS idx_document_page_variants_representation
    ON ci_document_page_variants(representation);

CREATE INDEX IF NOT EXISTS idx_procurement_context_buyer
    ON ci_procurement_context(buyer);

CREATE INDEX IF NOT EXISTS idx_procurement_context_seller
    ON ci_procurement_context(seller);

CREATE INDEX IF NOT EXISTS idx_procurement_context_category
    ON ci_procurement_context(procurement_category);

CREATE INDEX IF NOT EXISTS idx_classification_stage_role
    ON ci_classification(procurement_stage, primary_document_role);

CREATE INDEX IF NOT EXISTS idx_classification_change_kind
    ON ci_classification(change_kind);

CREATE INDEX IF NOT EXISTS idx_change_key_clauses_doc_id_ordinal
    ON ci_change_key_clauses(doc_id, ordinal);

CREATE INDEX IF NOT EXISTS idx_citations_doc_stage_domain_page
    ON ci_citations(doc_id, stage, domain, page_number);

CREATE INDEX IF NOT EXISTS idx_citations_stage_domain
    ON ci_citations(stage, domain);

CREATE INDEX IF NOT EXISTS idx_page_notes_role
    ON ci_page_notes(page_role);
