export const CORPUS_PAGES_WINDOW_SIZE = 10;

export function calculatePageWindowForPage(
  pageNumber: number,
  pageSize: number,
): number {
  return Math.floor((pageNumber - 1) / pageSize) + 1;
}
