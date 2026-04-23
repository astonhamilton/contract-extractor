# Contract Intelligence Pipeline And App

Contract lifecycle intelligence pipeline and intelligence app.

License: see [LICENCE](LICENCE).

## Quick Start

If you want the fastest way to run what is already in the repo:

```bash
git clone <repo-url>
cd <repo-folder>
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
OPENAI_API_KEY=<openai-key> uvicorn apps.api.app:app --reload
```

For model-backed stages and the assistant, you will typically also need an OpenAI API key.

You can provide it either way:

```bash
echo 'OPENAI_API_KEY=your-key-here' >> .env
```

or:

```bash
OPENAI_API_KEY=your-key-here uvicorn apps.api.app:app --reload
```

Why this works:
- the backend is the primary app entrypoint
- the built frontend bundle is already checked in under `apps/api/static/web`
- the app initializes its SQLite state under `data/app/app.db`
- the FastAPI app serves both the API and the bundled frontend
- the embedded assistant worker starts with the API app lifecycle

If you want the frontend dev server instead of the bundled app shell, you can still run `apps/web` separately, but the simplest path is just `uvicorn`.

On first launch, the app starts against a blank DB unless you have already run the pipeline and loader.

So the fastest path is simply:
- clone
- set `OPENAI_API_KEY` if you want live model-backed interaction
- launch `uvicorn`

## Business Context

This repo is built around one core idea:

**the hard part of contract intelligence is not finding documents, it is reconstructing current contract truth from fragmented lifecycle artifacts**

Real contract corpora are not one clean executed agreement per relationship. They are a time series of:
- base agreements
- renewals and extensions
- amendments and modifications
- pricing updates
- support and context documents

That means the live commercial state usually does not live in one PDF. It has to be reconstructed.

This system is designed to:
- normalize raw PDFs into usable page-level artifacts
- classify each artifact by lifecycle role
- separate governing state from later change
- preserve page-level evidence
- load the resulting intelligence into a structured serving layer
- expose that intelligence through an API, web app, and assistant

## Product Model

The system answers from reconstructed contract state, not from raw documents alone.

At a high level it is trying to support questions like:
- what contract governs this relationship?
- what changed after the governing agreement?
- what is the current pricing or term state?
- what evidence supports that conclusion?

That is why the repo is organized around:
- normalization
- document-role interpretation
- governing-state extraction
- change extraction
- evidence-preserving retrieval

## Architecture Overview

At the highest level, the codebase is a layered system:

1. a filesystem-first pipeline that turns raw PDFs into canonical normalized artifacts
2. a structured loading layer that projects those artifacts into a SQLite data mart
3. an application layer that serves corpus views, assistant workflows, and the web UI

The repo structure mirrors that architecture directly:

- `packages/pipeline/`
  Raw document ingestion, normalization, understanding stages, and DB loading.
- `packages/data_store/`
  SQLite connection management, migrations, schema SQL, commands, and query modules.
- `packages/app_services/`
  Service-layer composition for app and assistant behavior.
- `apps/api/`
  FastAPI transport layer and embedded runtime wiring.
- `apps/web/`
  React + Vite frontend.
- `packages/llm/`
  Agent packages, single-shot transform packages, shared runtimes, and local tools.

The conceptual model is:

`raw PDFs -> normalized page artifacts + manifests -> structured understanding outputs -> SQLite serving mart -> API + frontend + assistant`

## Core User Questions

The most important user flows in this system are:

1. discover the relevant vendor or relationship
2. identify the governing artifact
3. distinguish governing documents from deltas and context
4. reconstruct what changed over time
5. ground the answer in specific pages
6. translate contract language into business meaning

That user journey is why the codebase is structured as a state-reconstruction system rather than a generic PDF chat stack.

## High-Level Codebase Map

```text
apps/
  api/                FastAPI transport layer and embedded runtime wiring
  web/                React + Vite frontend
packages/
  app_services/       service-layer composition for corpus and chat features
  data_store/         SQLite connection, migrations, queries, schema SQL
  llm/                agents, transforms, shared runtime, local tools
  pipeline/           inventory, normalization, extraction, loading
  schemas/            typed contracts used across boundaries
data/
  raw/contracts/      source PDFs
  processed/          canonical filesystem artifacts and reports
  app/                SQLite serving database
scripts/              canonical and operator-facing CLIs
```

The repo is intentionally split into two planes:

### 1. Pipeline plane

The pipeline is filesystem-first. It takes raw PDFs and writes inspectable artifacts under `data/processed/`.

### 2. App plane

The app is the read layer on top of those artifacts. It exposes a REST API, a web frontend, and a persisted assistant runtime.

The easiest mental model is:

- `data/raw/contracts/` is the source corpus
- `data/processed/contracts/{doc_id}/` is the canonical per-document processing state
- `manifest.json` is the control-plane file for each processed document
- `data/app/app.db` is the read-optimized serving mart
- `apps/api/app.py` is the main runtime entrypoint

## Design Decisions

There are a few design choices that shape the entire repo.

### Filesystem-first pipeline

The pipeline does not treat the DB as the working state.

Instead it writes:
- per-document folders
- per-page artifacts
- manifest metadata
- stage reports
- staged dry-run outputs for model-backed stages

That makes the pipeline:
- inspectable
- incremental
- easier to debug
- safer to rerun selectively

The core manifest-driven normalization surface lives under:
- [packages/pipeline/normalize/pdf_pages.py](packages/pipeline/normalize/pdf_pages.py)
- [packages/schemas](packages/schemas)

### Structured serving layer after processing

The SQLite layer is loaded after the canonical artifacts exist. It is a serving/data-mart layer, not the primary processing layer.

That split is visible in:
- canonical artifact loading code: [packages/pipeline/contract_intelligence_db/loaders](packages/pipeline/contract_intelligence_db/loaders)
- DB schema SQL: [packages/data_store/contract_intelligence/schema/001_init.sql](packages/data_store/contract_intelligence/schema/001_init.sql)
- DB views: [packages/data_store/contract_intelligence/schema/003_views.sql](packages/data_store/contract_intelligence/schema/003_views.sql)

### Clear boundaries between transport, service, and DB

The backend is designed so:
- route handlers own HTTP transport concerns
- app services own application composition
- query modules own SQL
- shared schema/models translate explicitly at boundaries

The service layer does not reach through to handwritten SQL directly. SQL stays in `packages/data_store/.../queries/`.

A concrete example:
- transport: [apps/api/routes/corpus_documents/handler.py](apps/api/routes/corpus_documents/handler.py)
- service: [packages/app_services/corpus/documents.py](packages/app_services/corpus/documents.py)
- DB query: [packages/data_store/contract_intelligence/queries/search.py](packages/data_store/contract_intelligence/queries/search.py)
- transport response types: [apps/api/routes/corpus_documents/schema.py](apps/api/routes/corpus_documents/schema.py)

That separation is deliberate. It keeps the backend testable, composable, and less likely to leak DB abstractions through HTTP boundaries.

## The Pipeline: Raw PDFs To Normalized Outputs

The normalization stack is intentionally layered. It tries the cheapest, most deterministic surfaces first, then escalates only when quality signals indicate that more work is needed.

The top-level orchestrator is:
- [packages/pipeline/run_pipeline.py](packages/pipeline/run_pipeline.py)
- [scripts/run_normalize_pipeline.py](scripts/run_normalize_pipeline.py)

The pipeline stages are:

1. inventory
2. deterministic text extraction
3. deterministic image orientation validation
4. OCR fallback
5. LLM recommendation recompute
6. canonical LLM markdown normalization
7. optional vision-first markdown normalization
8. canonical LLM repair normalization
9. final pipeline-state audit and assembled normalized document output
10. token inventory and readiness reporting

### Stage 0: Inventory

Purpose:
- index raw PDFs
- create per-document folders
- establish the initial manifest structure

Code:
- [packages/pipeline/ingest/inventory.py](packages/pipeline/ingest/inventory.py)
- [scripts/inventory_contracts.py](scripts/inventory_contracts.py)

### Stage 1: Deterministic text extraction

Purpose:
- extract text directly from the PDF where possible
- assign page-level quality flags
- emit rendered page PNGs only for pages that look like image analysis may be needed

This is the first pass because it is cheap and deterministic.

Core behavior:
- writes `pages/{page}.txt`
- computes page quality signals such as `ocr_recommended`, `suspected_scanned_page`, `possible_table_or_form_content`
- emits `pages/{page}.png` only when the page looks like downstream OCR or image-led work may be needed

Code:
- [packages/pipeline/normalize/pdf_pages.py](packages/pipeline/normalize/pdf_pages.py)
- [scripts/normalize_contracts_txt.py](scripts/normalize_contracts_txt.py)

Things to look at in code:
- `page_quality_signals(...)`
- `should_generate_page_image(...)`
- `document_quality_flags(...)`

### Stage 2: Image preparation / orientation validation

Purpose:
- validate that page images are upright before OCR or image-led LLM work
- persist the validated image path and rotation metadata into the manifest

This stage sits between deterministic text extraction and downstream OCR/vision work because bad orientation corrupts both.

Core behavior:
- prefers OCR-backed scoring when OSD is weak
- writes validated upright images
- updates manifest fields like `validated_image_path`, `image_rotation_degrees`, `image_orientation_method`

Code:
- [packages/pipeline/normalize/image_orientation.py](packages/pipeline/normalize/image_orientation.py)
- [scripts/normalize_contracts_image_orientation.py](scripts/normalize_contracts_image_orientation.py)

### Stage 3: OCR fallback

Purpose:
- run OCR only for pages that the text stage flagged as weak or image-based
- derive OCR-specific quality flags that drive later LLM escalation

This is not “OCR everything.” It is selective.

Core behavior:
- targets pages through [packages/pipeline/normalize/ocr_selection.py](packages/pipeline/normalize/ocr_selection.py)
- writes `pages/{page}.ocr.txt`
- computes OCR-specific flags like:
  - `ocr_low_confidence`
  - `ocr_possible_table_or_form_content`
  - `ocr_suspected_garbled_text`
  - `llm_markdown_recommended`
  - `llm_repair_recommended`
  - `likely_blank_page`
  - `skip_llm_repair`

Code:
- [packages/pipeline/normalize/ocr_pages.py](packages/pipeline/normalize/ocr_pages.py)
- [packages/pipeline/normalize/ocr_selection.py](packages/pipeline/normalize/ocr_selection.py)
- [scripts/normalize_contracts_ocr.py](scripts/normalize_contracts_ocr.py)
- [scripts/normalize_contracts_ocr_parallel.py](scripts/normalize_contracts_ocr_parallel.py)

### Stage 4: Recompute LLM routing flags

Purpose:
- centralize the decision about which pages should receive LLM treatment after OCR and image prep are done

This prevents each later stage from inventing its own routing heuristics.

Code:
- [packages/pipeline/normalize/llm_selection.py](packages/pipeline/normalize/llm_selection.py)
- [packages/pipeline/normalize/recompute_llm_flags.py](packages/pipeline/normalize/recompute_llm_flags.py)
- [scripts/recompute_llm_flags.py](scripts/recompute_llm_flags.py)

Key routing concepts in code:
- `is_markdown_candidate(...)`
- `is_repair_candidate(...)`
- `is_vision_markdown_candidate(...)`
- skip logic for blank / low-information pages

### Stage 5: Canonical LLM image orientation

Purpose:
- optional second-pass LLM orientation correction for image pages that still warrant model-backed orientation decisions

This is more expensive and more selective than deterministic orientation.

Code:
- [packages/pipeline/normalize/llm_image_orientation.py](packages/pipeline/normalize/llm_image_orientation.py)
- [scripts/normalize_contracts_llm_image_orientation.py](scripts/normalize_contracts_llm_image_orientation.py)

### Stage 6: Canonical LLM markdown normalization

Purpose:
- recover reading order and layout structure for pages where OCR/text surfaces are insufficient, especially table/form-heavy pages

Core behavior:
- uses text plus image context
- writes `pages/{page}.md`
- marks `llm_markdown_generated`

Code:
- [packages/pipeline/normalize/llm_markdown.py](packages/pipeline/normalize/llm_markdown.py)
- [packages/llm/transforms/markdown_normalization](packages/llm/transforms/markdown_normalization)
- [scripts/normalize_contracts_llm_markdown.py](scripts/normalize_contracts_llm_markdown.py)

### Stage 7: Canonical vision-first markdown normalization

Purpose:
- optional image-led markdown generation for pages where the image should be treated as the primary source of truth

This is separate from normal markdown because it is a distinct strategy, not just “more markdown.”

Core behavior:
- staged run/apply pattern
- writes `pages/{page}.vision.md`
- optimized for image-led pages and hard visual layouts

Code:
- [packages/pipeline/normalize/vision_markdown.py](packages/pipeline/normalize/vision_markdown.py)
- [packages/llm/transforms/vision_markdown_normalization](packages/llm/transforms/vision_markdown_normalization)
- [scripts/normalize_contracts_vision_markdown.py](scripts/normalize_contracts_vision_markdown.py)

### Stage 8: Canonical LLM repair

Purpose:
- selectively repair the still-bad residue after text extraction, OCR, and markdown routing

This is intentionally later in the stack and intentionally narrow.

Core behavior:
- writes `pages/{page}.repair.md`
- marks `llm_repair_generated`

Code:
- [packages/pipeline/normalize/llm_repair.py](packages/pipeline/normalize/llm_repair.py)
- [packages/llm/transforms/repair_normalization](packages/llm/transforms/repair_normalization)
- [scripts/normalize_contracts_llm_repair.py](scripts/normalize_contracts_llm_repair.py)

### Stage 9: Assemble the canonical normalized document

Purpose:
- assemble one normalized document per source artifact from the best available page representation

This is the key “what downstream stages should read” surface.

The preferred page representation order is:
1. `repair_markdown`
2. `markdown`
3. `vision_markdown`
4. `ocr_text`
5. `text`

That order is implemented in:
- [packages/pipeline/normalize/assemble_normalized_document.py](packages/pipeline/normalize/assemble_normalized_document.py)

Why this order:
- use the most corrected and structured representation when available
- fall back to OCR before raw PDF text if OCR materially improved the surface
- keep the choice explicit and centralized

Canonical assembly code:
- [packages/pipeline/normalize/assemble_normalized_document.py](packages/pipeline/normalize/assemble_normalized_document.py)
- [scripts/assemble_normalized_documents.py](scripts/assemble_normalized_documents.py)

### Stage 10: Audit, analysis, and reports

Useful operator scripts:
- [scripts/audit_pipeline_state.py](scripts/audit_pipeline_state.py)
- [scripts/analyze_normalization_quality.py](scripts/analyze_normalization_quality.py)
- [scripts/analyze_token_inventory.py](scripts/analyze_token_inventory.py)
- [scripts/analyze_page_tokens.py](scripts/analyze_page_tokens.py)
- [scripts/estimate_normalized_tokens.py](scripts/estimate_normalized_tokens.py)

These are useful for understanding the corpus, not just running the transforms.

## Preferred Operators’ Script Surface

If you want to run the canonical path stage-by-stage, the main scripts are:

- [scripts/inventory_contracts.py](scripts/inventory_contracts.py)
- [scripts/normalize_contracts_txt.py](scripts/normalize_contracts_txt.py)
- [scripts/normalize_contracts_image_orientation.py](scripts/normalize_contracts_image_orientation.py)
- [scripts/normalize_contracts_ocr.py](scripts/normalize_contracts_ocr.py)
- [scripts/recompute_llm_flags.py](scripts/recompute_llm_flags.py)
- [scripts/normalize_contracts_llm_image_orientation.py](scripts/normalize_contracts_llm_image_orientation.py)
- [scripts/normalize_contracts_llm_markdown.py](scripts/normalize_contracts_llm_markdown.py)
- [scripts/normalize_contracts_vision_markdown.py](scripts/normalize_contracts_vision_markdown.py)
- [scripts/normalize_contracts_llm_repair.py](scripts/normalize_contracts_llm_repair.py)
- [scripts/assemble_normalized_documents.py](scripts/assemble_normalized_documents.py)

If you want the top-level orchestrator, use:
- [scripts/run_normalize_pipeline.py](scripts/run_normalize_pipeline.py)

## Classification And Extraction On Top Of Normalization

The product separates:
- governing state
- later change
- page-level evidence

That is exactly how the code is structured.

The pipeline first creates a canonical normalized reading surface.

Then the understanding layers sit on top of it:

### Procurement context

Purpose:
- establish whether the artifact belongs in the contracting/procurement universe at all
- identify buyer, seller, category, and what is being bought

Code:
- [packages/pipeline/procurement_context_stage.py](packages/pipeline/procurement_context_stage.py)
- [scripts/normalize_contracts_procurement_context.py](scripts/normalize_contracts_procurement_context.py)
- [packages/llm/transforms/procurement_context](packages/llm/transforms/procurement_context)

### Classification

Purpose:
- determine the document’s lifecycle role

This is the first key bridge between normalized text and contract-state reconstruction.

Code:
- [packages/pipeline/classification_stage.py](packages/pipeline/classification_stage.py)
- [scripts/normalize_contracts_classification.py](scripts/normalize_contracts_classification.py)
- [packages/llm/transforms/document_classification](packages/llm/transforms/document_classification)

### Governing domain notes

Purpose:
- extract the baseline governing picture for operative/guiding documents

Code:
- [packages/pipeline/governing_domain_notes_stage.py](packages/pipeline/governing_domain_notes_stage.py)
- [scripts/normalize_contracts_governing_domain_notes.py](scripts/normalize_contracts_governing_domain_notes.py)
- [packages/llm/transforms/governing_domain_notes](packages/llm/transforms/governing_domain_notes)

### Change extraction

Purpose:
- extract what changed, what prior artifact the change applies to, and the resulting state implications

This stage is explicitly classification-dependent.

It only routes documents that classification says are change artifacts. That dependency is deliberate: baseline truth and delta truth are different, so the system does not treat every document the same.

Code:
- [packages/pipeline/change_extraction_stage.py](packages/pipeline/change_extraction_stage.py)
- [scripts/normalize_contracts_change_extraction.py](scripts/normalize_contracts_change_extraction.py)
- [packages/llm/transforms/change_extraction](packages/llm/transforms/change_extraction)

### Page notes

Purpose:
- produce page-level retrieval notes that help the assistant and app narrow to relevant evidence quickly

Code:
- [packages/pipeline/page_notes_stage.py](packages/pipeline/page_notes_stage.py)
- [scripts/normalize_contracts_page_notes.py](scripts/normalize_contracts_page_notes.py)
- [packages/llm/transforms/page_notes](packages/llm/transforms/page_notes)

## Loading Canonical Artifacts Into A Structured Data Mart

Once canonical artifacts exist, the repo loads them into SQLite for app-facing reads.

That load process is intentionally separate from the filesystem-first pipeline.

Main loader entrypoint:
- [scripts/load_sqlite_contract_intelligence.py](scripts/load_sqlite_contract_intelligence.py)

Loader package:
- [packages/pipeline/contract_intelligence_db/loaders](packages/pipeline/contract_intelligence_db/loaders)

The loader step registry is here:
- [packages/pipeline/contract_intelligence_db/loaders/__init__.py](packages/pipeline/contract_intelligence_db/loaders/__init__.py)

The DB schema is here:
- [packages/data_store/contract_intelligence/schema/001_init.sql](packages/data_store/contract_intelligence/schema/001_init.sql)
- [packages/data_store/contract_intelligence/schema/002_indexes.sql](packages/data_store/contract_intelligence/schema/002_indexes.sql)
- [packages/data_store/contract_intelligence/schema/003_views.sql](packages/data_store/contract_intelligence/schema/003_views.sql)

Things to look at in the schema:
- `ci_documents`
- `ci_document_page_variants`
- `ci_procurement_context`
- `ci_classification`
- `ci_governing_notes`
- `ci_change_notes`
- `ci_page_notes`
- `v_ci_document_pages_best`
- readiness views like `ci_v_loader_ready_documents`

The DB and migration wiring lives here:
- [packages/data_store/connect.py](packages/data_store/connect.py)
- [packages/data_store/migrations.py](packages/data_store/migrations.py)

The key idea is:
- process first to manifests and files
- load second into a serving mart
- keep each layer honest about what it is responsible for

## App Layer

The app layer has three main pieces:
- REST API
- web frontend
- persisted assistant runtime

### Backend transport

The FastAPI entrypoint is:
- [apps/api/app.py](apps/api/app.py)

It wires:
- corpus browsing endpoints
- document detail endpoints
- thread and assistant endpoints
- frontend static serving when the built web bundle has been deployed

### Frontend bundling into the API

The frontend is standard React + Vite under:
- [apps/web](apps/web)

The built frontend can be copied into the API static directory and then served directly by FastAPI:
- deploy script: [scripts/deploy_web_dist_to_api.py](scripts/deploy_web_dist_to_api.py)
- static serving code: [apps/api/routes/web_app/handler.py](apps/api/routes/web_app/handler.py)

That means deployment can be kept simple:
- build the frontend
- deploy the dist into the API static folder
- run `uvicorn`

Once deployed, the API can serve both the REST endpoints and the frontend bundle.

### Backend service layer

The service layer lives in:
- [packages/app_services/corpus](packages/app_services/corpus)
- [packages/app_services/chat_assistant](packages/app_services/chat_assistant)

This is where application behavior is composed out of:
- DB queries
- agent runtime interactions
- response shaping
- boundary translation into transport-safe models

Examples:
- corpus list service: [packages/app_services/corpus/documents.py](packages/app_services/corpus/documents.py)
- assistant thread creation: [packages/app_services/chat_assistant/create_thread.py](packages/app_services/chat_assistant/create_thread.py)

### DB / infra layer

The query and persistence surfaces are isolated under:
- [packages/data_store/contract_intelligence/queries](packages/data_store/contract_intelligence/queries)
- [packages/data_store/llm_agent_runtime/queries](packages/data_store/llm_agent_runtime/queries)
- [packages/data_store/llm_agent_runtime/commands](packages/data_store/llm_agent_runtime/commands)

This is where SQL and DB persistence details live.

That separation keeps:
- transport thin
- services composable
- DB logic centralized
- type translation explicit

## Embedded Agent Runtime

The repo includes a tailored persisted agent runtime that is designed to be embeddable and deployment-friendly.

The app-specific wiring is here:
- [apps/api/agent_runtime.py](apps/api/agent_runtime.py)

The shared runtime infrastructure is here:
- [packages/llm/shared/agent_runtime](packages/llm/shared/agent_runtime)

Important properties of the runtime:
- persisted SQLite-backed state
- resumable threads and turns
- multi-worker-safe claim/heartbeat model
- embeddable into the API lifecycle
- can also be run explicitly as a standalone worker

Relevant code:
- embedded service builder: [packages/llm/shared/agent_runtime/embedded_service.py](packages/llm/shared/agent_runtime/embedded_service.py)
- runtime loop: [packages/llm/shared/agent_runtime/loop.py](packages/llm/shared/agent_runtime/loop.py)
- worker: [packages/llm/shared/agent_runtime/worker.py](packages/llm/shared/agent_runtime/worker.py)
- registry: [packages/llm/shared/agent_runtime/registry.py](packages/llm/shared/agent_runtime/registry.py)
- tool execution context: [packages/llm/shared/agent_runtime/tools.py](packages/llm/shared/agent_runtime/tools.py)
- persisted runtime schema: [packages/data_store/llm_agent_runtime/schema/001_init.sql](packages/data_store/llm_agent_runtime/schema/001_init.sql)

Operator script:
- [scripts/run_agent_runtime_worker.py](scripts/run_agent_runtime_worker.py)

Why this matters:
- the API can run with an embedded worker for simple deployment
- the same runtime model can support explicit workers
- persisted turn/model/tool state makes interruption, recovery, and resume practical

## LLM Code Organization

The LLM layer is intentionally split into four buckets:

### Agents

Durable runtime agents live under:
- [packages/llm/agents/app/corpus_assistant](packages/llm/agents/app/corpus_assistant)
- [packages/llm/agents/app/thread_titling](packages/llm/agents/app/thread_titling)

These are real agents in the runtime sense: they define agent specs, tool wiring, and prompt surfaces for persisted threads.

### Transforms

Single-shot LLM task packages used by pipeline stages live under:
- [packages/llm/transforms](packages/llm/transforms)

These are not agents. They are task packages for one-shot model work.

Important transform packages:
- `document_classification`
- `procurement_context`
- `governing_domain_notes`
- `change_extraction`
- `page_notes`
- `markdown_normalization`
- `repair_normalization`
- `vision_markdown_normalization`
- `image_orientation_decision`

### Shared

Reusable runtime and task infrastructure lives under:
- [packages/llm/shared](packages/llm/shared)

This includes:
- agent runtime orchestration
- single-shot task runtime helpers
- strict schema support

### Tools

Reusable local tools live under:
- [packages/llm/tools](packages/llm/tools)

These are shared tool implementations rather than app routes or model prompts.

## Running The System

### Python setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend setup

```bash
cd apps/web
npm install
```

### Environment

Some model-backed stages expect credentials in `.env`.

### Canonical full pipeline

```bash
python3 scripts/run_normalize_pipeline.py
```

### Stage-by-stage pipeline

```bash
python3 scripts/inventory_contracts.py
python3 scripts/normalize_contracts_txt.py
python3 scripts/normalize_contracts_image_orientation.py
python3 scripts/normalize_contracts_ocr.py
python3 scripts/recompute_llm_flags.py
python3 scripts/normalize_contracts_llm_markdown.py
python3 scripts/normalize_contracts_llm_repair.py
python3 scripts/assemble_normalized_documents.py
```

Add optional stages when needed:

```bash
python3 scripts/normalize_contracts_llm_image_orientation.py
python3 scripts/normalize_contracts_vision_markdown.py
```

### Understanding stages

```bash
python3 scripts/normalize_contracts_procurement_context.py
python3 scripts/normalize_contracts_classification.py
python3 scripts/normalize_contracts_governing_domain_notes.py
python3 scripts/normalize_contracts_change_extraction.py
python3 scripts/normalize_contracts_page_notes.py
```

### Load the structured data mart

```bash
python3 scripts/load_sqlite_contract_intelligence.py
```

### Run the API

```bash
uvicorn apps.api.app:app --reload
```

### Run the web app in dev mode

```bash
cd apps/web
npm run dev
```

### Build and deploy the frontend bundle into the API

```bash
cd apps/web
npm run build
cd ../..
python3 scripts/deploy_web_dist_to_api.py
uvicorn apps.api.app:app --reload
```

### Run the standalone worker

```bash
python3 scripts/run_agent_runtime_worker.py
```

## Suggested Reading Order

If you want to understand the codebase quickly, use this order:

1. [packages/pipeline/run_pipeline.py](packages/pipeline/run_pipeline.py)
2. [packages/pipeline/normalize/pdf_pages.py](packages/pipeline/normalize/pdf_pages.py)
3. [packages/pipeline/normalize/image_orientation.py](packages/pipeline/normalize/image_orientation.py)
4. [packages/pipeline/normalize/ocr_pages.py](packages/pipeline/normalize/ocr_pages.py)
5. [packages/pipeline/normalize/llm_selection.py](packages/pipeline/normalize/llm_selection.py)
6. [packages/pipeline/normalize/assemble_normalized_document.py](packages/pipeline/normalize/assemble_normalized_document.py)
7. [packages/pipeline/classification_stage.py](packages/pipeline/classification_stage.py)
8. [packages/pipeline/governing_domain_notes_stage.py](packages/pipeline/governing_domain_notes_stage.py)
9. [packages/pipeline/change_extraction_stage.py](packages/pipeline/change_extraction_stage.py)
10. [packages/pipeline/contract_intelligence_db/loaders](packages/pipeline/contract_intelligence_db/loaders)
11. [packages/data_store/contract_intelligence/schema/001_init.sql](packages/data_store/contract_intelligence/schema/001_init.sql)
12. [apps/api/app.py](apps/api/app.py)
13. [apps/api/agent_runtime.py](apps/api/agent_runtime.py)
14. [packages/llm/agents/app/corpus_assistant](packages/llm/agents/app/corpus_assistant)
15. [apps/web/src/app/App.tsx](apps/web/src/app/App.tsx)

## What To Look For

The repo is strongest when read as a system, not as a single model prompt.

The important questions are:
- does the normalization stack create trustworthy reading surfaces?
- does classification separate governing state from later change?
- do extraction stages depend on that role interpretation rather than flattening everything together?
- does the serving layer preserve evidence and explicit structure?
- does the app sit on top of reconstructed intelligence rather than naive document search?

That is the conceptual model, and it is also how the codebase is organized.

## Future Work

The next logical improvements are mostly in canonicalization, linkage, and current-state reconstruction.

- normalize buyer, seller, and affiliate names into cleaner canonical entities
- strengthen cross-document linkage between governing artifacts and later deltas
- normalize key identifiers such as contract numbers, purchase orders, task orders, and amendment numbers
- improve table- and form-heavy normalization for pricing schedules, rate cards, and fee structures
- tighten confidence calibration and escalation rules for low-trust extraction outputs
- build a stronger derived current-state layer that composes governing state plus later changes
- expand corpus audit metrics around stage yield, extraction coverage, and failure modes
