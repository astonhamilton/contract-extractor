import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

type Parser<T> = (raw: string) => T;
type Stringifier<T> = (value: T) => string;
type StorageKind = "local" | "session";

type UseLocalStorageStateOptions<T> = {
  parse?: Parser<T>;
  stringify?: Stringifier<T>;
  storage?: StorageKind;
};

function resolveInitialValue<T>(value: T | (() => T)): T {
  return typeof value === "function" ? (value as () => T)() : value;
}

function defaultParse<T>(raw: string): T {
  return JSON.parse(raw) as T;
}

function defaultStringify<T>(value: T): string {
  return JSON.stringify(value);
}

function resolveStorage(kind: StorageKind): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return kind === "session" ? window.sessionStorage : window.localStorage;
}

function readStoredValue<T>(
  key: string,
  initialValue: T,
  parse: Parser<T>,
  storageKind: StorageKind,
): T {
  const storage = resolveStorage(storageKind);
  if (storage === null) {
    return initialValue;
  }

  try {
    const stored = storage.getItem(key);
    return stored === null ? initialValue : parse(stored);
  } catch {
    return initialValue;
  }
}

/**
 * Persist a small piece of UI state in localStorage or sessionStorage.
 */
export default function useStoredState<T>(
  key: string,
  initialValue: T | (() => T),
  options: UseLocalStorageStateOptions<T> = {},
): [T, Dispatch<SetStateAction<T>>] {
  const parse = options.parse ?? defaultParse<T>;
  const stringify = options.stringify ?? defaultStringify<T>;
  const storageKind = options.storage ?? "local";

  const [value, setValue] = useState<T>(() =>
    readStoredValue(key, resolveInitialValue(initialValue), parse, storageKind),
  );

  useEffect(() => {
    const storage = resolveStorage(storageKind);
    if (storage === null) {
      return;
    }

    try {
      storage.setItem(key, stringify(value));
    } catch {
      // Ignore storage write failures in the mock frontend.
    }
  }, [key, storageKind, stringify, value]);

  return [value, setValue];
}
