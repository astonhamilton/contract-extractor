import { formatRepresentationLabel } from "@/domain/corpus/corpusLabels";
import type {
  CorpusPageContentView,
  CorpusPageDetailView,
} from "@/domain/corpus/corpusTypes";
import type {
  CorpusDocumentPageDetailApiResponse,
  CorpusDocumentPageDetailContentApiResponse,
} from "@/services/corpus/corpusApi";

function mapPageContent(
  content: CorpusDocumentPageDetailContentApiResponse,
  key: string,
  label: string,
): CorpusPageContentView {
  return {
    key,
    label,
    representation: content.representation,
    sourcePath: content.source_path,
    content: content.content,
    estimatedTokens: content.estimated_tokens,
    warnings: content.warnings,
    qualityFlags: content.quality_flags,
    pageRole: content.page_role,
    keyTerms: content.key_terms,
    relevanceTags: content.relevance_tags,
  };
}

export function mapCorpusDocumentPageDetail(
  response: CorpusDocumentPageDetailApiResponse,
): CorpusPageDetailView {
  const bestView = mapPageContent(
    response.best_content,
    response.best_content.representation ?? "best",
    formatRepresentationLabel(response.best_content.representation),
  );
  const variantViews = response.variants.map((variant, index) => {
    const representation = variant.representation ?? "variant";
    return mapPageContent(
      variant,
      `${representation}-${index}`,
      representation === "page_notes"
        ? "Summary"
        : formatRepresentationLabel(variant.representation),
    );
  });
  const summaryNote =
    variantViews.find((view) => view.representation === "page_notes") ?? null;
  const representationViews = variantViews.filter(
    (view) => view.representation !== "page_notes",
  );

  return {
    pageNumber: response.page.page_number,
    bestRepresentation: formatRepresentationLabel(response.page.best_representation),
    estimatedTokens: response.page.estimated_tokens,
    summaryNote,
    views: [bestView, ...representationViews],
  };
}
