import { useEffect, useState } from "react";

type StoredStateOptions = {
  storage?: "local" | "session";
};

function storageFor(kind: "local" | "session"): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return kind === "local" ? window.localStorage : window.sessionStorage;
}

export function useStoredState<T>(
  key: string,
  initialValue: T,
  options: StoredStateOptions = {},
) {
  const storageKind = options.storage ?? "local";
  const [value, setValue] = useState<T>(() => {
    const storage = storageFor(storageKind);
    const stored = storage?.getItem(key);
    if (!stored) {
      return initialValue;
    }
    try {
      return JSON.parse(stored) as T;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    const storage = storageFor(storageKind);
    storage?.setItem(key, JSON.stringify(value));
  }, [key, storageKind, value]);

  return [value, setValue] as const;
}
