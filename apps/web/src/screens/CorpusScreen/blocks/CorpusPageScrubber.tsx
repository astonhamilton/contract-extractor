import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import {
  AlignLeft,
  ChevronDown,
  ChevronUp,
  FileText,
  FileWarning,
} from "lucide-react";
import type {
  CorpusDocument,
  CorpusPage,
} from "@/screens/CorpusScreen/CorpusScreen.types";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import styles from "./CorpusPageScrubber.module.css";

type CorpusPageScrubberProps = {
  activePage: CorpusPage | null;
  activePageIndex: number;
  activePagePreviewPending: boolean;
  document: CorpusDocument;
  onOpenRepresentation: (pageNumber: number) => void;
  onPageIndexChange: (index: number) => void;
  pagesFetching: boolean;
};

type DragState = {
  activePageIndex: number;
  pointerId: number;
  startY: number;
};

type PageImageProps = {
  alt: string;
  className: string;
  draggable?: boolean;
  previewText?: string;
  pending?: boolean;
  src: string;
  variant: "rail" | "preview";
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function PageSurface({
  alt,
  className,
  draggable = false,
  pending = false,
  previewText,
  src,
  variant,
}: PageImageProps) {
  const hasSrc = src.trim().length > 0;
  const [status, setStatus] = useState<"loading" | "loaded" | "failed">(
    hasSrc ? "loading" : "failed",
  );

  useEffect(() => {
    if (!hasSrc) {
      setStatus("failed");
      return;
    }

    setStatus("loading");

    const stallTimer = window.setTimeout(() => {
      setStatus((current) => (current === "loading" ? "failed" : current));
    }, 5000);

    return () => {
      window.clearTimeout(stallTimer);
    };
  }, [hasSrc, src]);

  if (pending && variant === "preview") {
    return (
      <span
        className={`${className} ${styles.previewLoading}`}
        data-variant={variant}
      >
        <Spinner className={styles.previewLoadingSpinner} />
        <span>Loading page preview...</span>
      </span>
    );
  }

  if (!hasSrc || status === "failed") {
    if (previewText && variant === "preview") {
      return (
        <span
          className={`${className} ${styles.textFallback}`}
          data-variant={variant}
        >
          <span className={styles.textFallbackLabel}>
            <AlignLeft size={variant === "preview" ? 16 : 12} aria-hidden="true" />
            Text preview
          </span>
          <span className={styles.textFallbackBody}>{previewText}</span>
        </span>
      );
    }

    return (
      <span className={`${className} ${styles.imageFallback}`}>
        <FileWarning size={18} aria-hidden="true" />
        <span>Preview unavailable</span>
      </span>
    );
  }

  return (
    <img
      alt={alt}
      className={`${className} ${status === "loaded" ? styles.imageLoaded : ""}`}
      draggable={draggable}
      onError={() => setStatus("failed")}
      onLoad={() => setStatus("loaded")}
      src={src}
    />
  );
}

export function CorpusPageScrubber({
  activePage,
  activePageIndex,
  activePagePreviewPending,
  document,
  onOpenRepresentation,
  onPageIndexChange,
  pagesFetching,
}: CorpusPageScrubberProps) {
  const [dragging, setDragging] = useState(false);
  const dragState = useRef<DragState | null>(null);
  const railRef = useRef<HTMLDivElement | null>(null);

  const maxIndex = document.pages.length - 1;

  useEffect(() => {
    const activeButton = railRef.current?.querySelector(
      '[data-active-page="true"]',
    );
    activeButton?.scrollIntoView({
      block: "nearest",
      inline: "nearest",
    });
  }, [activePageIndex]);

  function moveBy(delta: number): void {
    onPageIndexChange(clamp(activePageIndex + delta, 0, maxIndex));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "ArrowDown" || event.key === "ArrowRight") {
      event.preventDefault();
      moveBy(1);
    }

    if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
      event.preventDefault();
      moveBy(-1);
    }

    if (event.key === "Home") {
      event.preventDefault();
      onPageIndexChange(0);
    }

    if (event.key === "End") {
      event.preventDefault();
      onPageIndexChange(maxIndex);
    }
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>): void {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragState.current = {
      activePageIndex,
      pointerId: event.pointerId,
      startY: event.clientY,
    };
    setDragging(true);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>): void {
    const state = dragState.current;
    if (!state || state.pointerId !== event.pointerId) {
      return;
    }

    const pageDelta = Math.round((state.startY - event.clientY) / 54);
    onPageIndexChange(clamp(state.activePageIndex + pageDelta, 0, maxIndex));
  }

  function endDrag(): void {
    dragState.current = null;
    setDragging(false);
  }

  return (
    <article className={styles.root}>
      <div className={styles.header}>
        <div>
          <p>Available pages</p>
          <h2>{activePage ? `Page ${activePage.pageNumber}` : "No page selected"}</h2>
        </div>
        <div className={styles.controls}>
          <IconButton
            aria-label="Previous page"
            disabled={activePageIndex <= 0}
            onClick={() => moveBy(-1)}
            tooltip="Previous page"
          >
            <ChevronUp size={16} aria-hidden="true" />
          </IconButton>
          <span>
            {activePageIndex + 1} / {document.pages.length}
          </span>
          <span
            aria-label={pagesFetching ? "Loading page window" : undefined}
            className={styles.loadingSlot}
            role={pagesFetching ? "status" : undefined}
          >
            {pagesFetching ? <Spinner className={styles.spinner} /> : null}
          </span>
          <IconButton
            aria-label="Next page"
            disabled={activePageIndex >= maxIndex}
            onClick={() => moveBy(1)}
            tooltip="Next page"
          >
            <ChevronDown size={16} aria-hidden="true" />
          </IconButton>
          <IconButton
            aria-label="Open page representation"
            disabled={!activePage}
            onClick={() => activePage && onOpenRepresentation(activePage.pageNumber)}
            tooltip="Open representation"
          >
            <FileText size={16} aria-hidden="true" />
          </IconButton>
        </div>
      </div>

      <div
        aria-label="Scrub document pages"
        className={styles.scrubber}
        onKeyDown={handleKeyDown}
        onPointerCancel={endDrag}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        role="slider"
        aria-valuemax={document.pages.length}
        aria-valuemin={1}
        aria-valuenow={activePageIndex + 1}
        tabIndex={0}
      >
        <div className={styles.rail} aria-label="Page thumbnails" ref={railRef}>
          {document.pages.map((page, index) => (
            <button
              aria-label={`Open page ${page.pageNumber}`}
              className={index === activePageIndex ? styles.railActive : styles.railItem}
              data-active-page={index === activePageIndex ? "true" : undefined}
              key={page.pageNumber}
              onClick={(event) => {
                event.stopPropagation();
                onPageIndexChange(index);
              }}
              onPointerDown={(event) => {
                event.stopPropagation();
              }}
              type="button"
            >
              <PageSurface
                alt=""
                className={styles.railImage}
                draggable={false}
                previewText={page.previewText}
                src={page.thumbUrl}
                variant="rail"
              />
              <span>{page.pageNumber}</span>
            </button>
          ))}
        </div>

        <div className={styles.stage} data-dragging={dragging ? "true" : "false"}>
          <div className={styles.previewShell}>
            {activePage ? (
              <PageSurface
                alt={`Preview of page ${activePage.pageNumber}`}
                className={styles.preview}
                draggable={false}
                pending={activePagePreviewPending}
                previewText={activePage.previewText}
                src={activePage.previewUrl}
                variant="preview"
              />
            ) : null}
          </div>
        </div>
      </div>
    </article>
  );
}
