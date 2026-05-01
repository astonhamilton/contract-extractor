export function formatCorpusLabel(value: string): string {
  return value.replace(/_/g, " ");
}

export function formatRepresentationLabel(value: string | null | undefined): string {
  if (!hasText(value)) {
    return "Unknown";
  }
  if (value === "page_notes") {
    return "Cliff note";
  }
  return formatCorpusLabel(value);
}

export function hasText(value: string | null | undefined): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function displayValue(value: string | null | undefined): string {
  return hasText(value) ? value : "Not found in initial extraction";
}

export function isMeaningfulExtractedValue(
  value: string | null | undefined,
): value is string {
  if (!hasText(value)) {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized !== "unknown seller" && normalized !== "unknown buyer";
}

export function displayExtractedParty(value: string | null | undefined): string {
  return isMeaningfulExtractedValue(value)
    ? value
    : "Not found in initial extraction";
}
