"""Purpose-built read queries for the contract-intelligence SQLite DB."""

from packages.data_store.contract_intelligence.queries.change import get_change_notes, find_change_documents
from packages.data_store.contract_intelligence.queries.documents import (
    get_document,
    get_document_aggregate,
    get_document_page_variants,
    get_document_pages,
    get_page_notes,
)
from packages.data_store.contract_intelligence.queries.governing import get_governing_notes, find_governing_documents
from packages.data_store.contract_intelligence.queries.search import find_documents, list_document_index
from packages.data_store.contract_intelligence.queries.summary import (
    get_document_count,
    get_raw_corpus_size_bytes,
)

__all__ = [
    "find_change_documents",
    "find_documents",
    "find_governing_documents",
    "get_change_notes",
    "get_document",
    "get_document_aggregate",
    "get_document_page_variants",
    "get_document_pages",
    "get_governing_notes",
    "get_document_count",
    "get_raw_corpus_size_bytes",
    "get_page_notes",
    "list_document_index",
]
