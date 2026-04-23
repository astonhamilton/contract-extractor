PRAGMA foreign_keys = ON;

CREATE VIEW IF NOT EXISTS v_ci_document_pages_best AS
WITH ranked_variants AS (
    SELECT
        variant.*,
        ROW_NUMBER() OVER (
            PARTITION BY variant.doc_id, variant.page_number
            ORDER BY variant.priority ASC, variant.representation ASC
        ) AS row_rank
    FROM ci_document_page_variants AS variant
)
SELECT
    doc_id,
    page_number,
    content,
    representation,
    source_path,
    extraction_method,
    char_count,
    ocr_char_count,
    ocr_confidence,
    warnings_json,
    quality_flags_json,
    estimated_tokens
FROM ranked_variants
WHERE row_rank = 1;

CREATE VIEW IF NOT EXISTS ci_v_document_stage_readiness AS
SELECT
    d.doc_id,
    d.source_filename,
    d.source_pdf_path,
    d.page_count,
    d.processing_status,
    d.normalized_document_path,
    d.procurement_context_path,
    d.procurement_context_status,
    d.classification_path,
    d.classification_status,
    d.governing_domain_notes_path,
    d.governing_domain_notes_status,
    d.change_extraction_path,
    d.change_extraction_status,
    d.page_notes_path,
    d.page_notes_status,
    c.procurement_stage,
    c.primary_document_role,
    c.change_kind,
    CASE
        WHEN d.normalized_document_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_normalized_document,
    CASE
        WHEN d.procurement_context_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_procurement_context,
    CASE
        WHEN d.classification_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_classification,
    CASE
        WHEN c.procurement_stage = 'contracting'
         AND c.primary_document_role = 'operative' THEN 1
        ELSE 0
    END AS expects_governing_notes,
    CASE
        WHEN c.procurement_stage = 'active_change'
         AND c.primary_document_role = 'delta' THEN 1
        ELSE 0
    END AS expects_change_notes,
    CASE
        WHEN d.governing_domain_notes_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_governing_notes,
    CASE
        WHEN d.change_extraction_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_change_notes,
    CASE
        WHEN d.page_notes_path IS NOT NULL THEN 1
        ELSE 0
    END AS has_page_notes
FROM ci_documents AS d
LEFT JOIN ci_classification AS c
    ON c.doc_id = d.doc_id;

CREATE VIEW IF NOT EXISTS ci_v_loader_ready_documents AS
SELECT
    *
FROM ci_v_document_stage_readiness
WHERE has_normalized_document = 1
  AND has_procurement_context = 1
  AND has_classification = 1
  AND (expects_governing_notes = 0 OR has_governing_notes = 1)
  AND (expects_change_notes = 0 OR has_change_notes = 1);

CREATE VIEW IF NOT EXISTS ci_v_missing_expected_stage_outputs AS
SELECT
    doc_id,
    source_filename,
    procurement_stage,
    primary_document_role,
    expects_governing_notes,
    expects_change_notes,
    has_governing_notes,
    has_change_notes,
    CASE
        WHEN expects_governing_notes = 1 AND has_governing_notes = 0
            THEN 'governing_domain_notes'
        WHEN expects_change_notes = 1 AND has_change_notes = 0
            THEN 'change_extraction'
        WHEN has_procurement_context = 0
            THEN 'procurement_context'
        WHEN has_classification = 0
            THEN 'classification'
        WHEN has_normalized_document = 0
            THEN 'normalized_document'
        ELSE NULL
    END AS missing_stage
FROM ci_v_document_stage_readiness
WHERE has_normalized_document = 0
   OR has_procurement_context = 0
   OR has_classification = 0
   OR (expects_governing_notes = 1 AND has_governing_notes = 0)
   OR (expects_change_notes = 1 AND has_change_notes = 0);
