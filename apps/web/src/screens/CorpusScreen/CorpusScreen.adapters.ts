import {
  displayExtractedParty,
  displayValue,
  formatCorpusLabel,
} from "@/domain/corpus/corpusLabels";
import type {
  CorpusDocumentDetailApiResponse,
  CorpusDocumentPageApiResponse,
  CorpusDocumentPagesApiResponse,
  CorpusDocumentsApiItem,
} from "@/services/corpus/corpusApi";
import type {
  CorpusDocument,
  CorpusPage,
  CorpusSummary,
} from "@/screens/CorpusScreen/CorpusScreen.types";

const DEFAULT_PAGE_SIZE = {
  width: 612,
  height: 792,
};

type PageThumbnailSpec = {
  thumbUrl: string;
  previewUrl: string;
  fullUrl?: string;
  width: number;
  height: number;
};

function getPageThumbnailSpec(
  _page: Pick<CorpusDocumentPageApiResponse, "page_number">,
): PageThumbnailSpec {
  return {
    thumbUrl: "",
    previewUrl: "",
    fullUrl: undefined,
    ...DEFAULT_PAGE_SIZE,
  };
}

function mapPage(
  page: Pick<CorpusDocumentPageApiResponse, "page_number"> &
    Partial<Pick<CorpusDocumentPageApiResponse, "preview">>,
  options: { loaded: boolean },
): CorpusPage {
  const thumbnail = getPageThumbnailSpec(page);

  return {
    pageNumber: page.page_number,
    loaded: options.loaded,
    thumbUrl: thumbnail.thumbUrl,
    previewUrl: thumbnail.previewUrl,
    previewText: page.preview?.trim() || undefined,
    fullUrl: thumbnail.fullUrl,
    sourcePath: "",
    width: thumbnail.width,
    height: thumbnail.height,
  };
}

function synthesizePages(pageCount: number): CorpusPage[] {
  return Array.from({ length: Math.max(0, pageCount) }, (_, index) =>
    mapPage({ page_number: index + 1 }, { loaded: false }),
  );
}

function overlayLoadedPages(
  pages: CorpusPage[],
  response: CorpusDocumentPagesApiResponse | null | undefined,
): CorpusPage[] {
  if (!response) {
    return pages;
  }

  const loadedPages = new Map(
    response.items.map((page) => [page.page_number, mapPage(page, { loaded: true })]),
  );

  return pages.map((page) => loadedPages.get(page.pageNumber) ?? page);
}

function listSummary(item: CorpusDocumentsApiItem): CorpusSummary {
  return {
    parties: [
      displayExtractedParty(item.buyer),
      displayExtractedParty(item.seller),
    ],
    procurementCategory: "Not found in initial extraction",
    subject: item.overview || "Not available",
  };
}

function detailSummary(detail: CorpusDocumentDetailApiResponse): CorpusSummary {
  const buyer = detail.procurement_context.buyer;
  const seller = detail.procurement_context.seller;
  const procurementCategory = detail.procurement_context.procurement_category;

  return {
    parties: [displayExtractedParty(buyer), displayExtractedParty(seller)],
    procurementCategory: procurementCategory
      ? formatCorpusLabel(procurementCategory)
      : displayValue(procurementCategory),
    subject: displayValue(detail.procurement_context.what_is_being_bought),
  };
}

export function mapCorpusListDocument(
  item: CorpusDocumentsApiItem,
): CorpusDocument {
  const cover = mapPage({ page_number: 1 }, { loaded: false });
  const pages = synthesizePages(item.page_count);

  return {
    id: item.doc_id,
    title: item.title,
    sourceFolder: item.source_filename,
    sourceFileSizeBytes: item.source_pdf_size_bytes ?? undefined,
    pageCount: item.page_count,
    availablePages: item.page_count,
    coverUrl: cover.thumbUrl,
    summary: listSummary(item),
    pages,
  };
}

export function mapCorpusSelectedDocument(args: {
  detail: CorpusDocumentDetailApiResponse;
  fallback?: CorpusDocument | null;
  pages?: CorpusDocumentPagesApiResponse | null;
}): CorpusDocument {
  const { detail, fallback = null, pages: pagesResponse = null } = args;
  const pageCount = pagesResponse?.total ?? detail.document.page_count;
  const pages = overlayLoadedPages(synthesizePages(pageCount), pagesResponse);
  const coverPage = pages[0] ?? mapPage({ page_number: 1 }, { loaded: false });

  return {
    id: detail.document.doc_id,
    title: detail.document.title,
    sourceFolder: detail.document.source_filename,
    sourceFileSizeBytes: detail.document.source_pdf_size_bytes ?? undefined,
    pageCount,
    availablePages: pageCount,
    coverUrl: coverPage.thumbUrl,
    summary: detailSummary(detail),
    pages: pages.length > 0 ? pages : fallback?.pages ?? [],
  };
}
