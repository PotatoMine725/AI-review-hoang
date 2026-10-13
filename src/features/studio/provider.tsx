"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { initialStudio, parseStudio, STUDIO_KEY, type StudioState } from "./model";

type Store = StudioState & { ready: boolean; error: boolean; commit: (update: (state: StudioState) => StudioState) => void };
const Context = createContext<Store | null>(null);
export function StudioProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialStudio);
  const current = useRef(state);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    const restore = () => {
      if (!alive) return;
      try {
        const raw = localStorage.getItem(STUDIO_KEY);
        const restored = raw ? parseStudio(raw) : structuredClone(initialStudio);
        current.current = restored; setState(restored); setError(false); setReady(true);
      } catch { setError(true); setReady(false); }
    };
    queueMicrotask(restore);
    const sync = (event: StorageEvent) => { if (event.key === STUDIO_KEY) restore(); };
    window.addEventListener("storage", sync);
    return () => { alive = false; window.removeEventListener("storage", sync); };
  }, []);
  function commit(update: (state: StudioState) => StudioState) {
    if (!ready) throw new Error("storage");
    try {
      const raw = localStorage.getItem(STUDIO_KEY);
      if (raw && parseStudio(raw).revision !== current.current.revision) throw new Error("conflict");
      const next = { ...update(current.current), revision: current.current.revision + 1 };
      parseStudio(JSON.stringify(next));
      localStorage.setItem(STUDIO_KEY, JSON.stringify(next));
      current.current = next; setState(next); setError(false);
    } catch { setError(true); throw new Error("storage"); }
  }
  return <Context.Provider value={{ ...state, ready, error, commit }}>{children}</Context.Provider>;
}
export function useStudio() {
  const context = useContext(Context);
  if (!context) throw new Error("StudioProvider required");
  return context;
}
