import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { loadManifest } from "../data/client";
import type { TargetId, WebManifest } from "../data/types";
import { libraryHref, resolveTarget } from "./router";

type AppContextValue = {
  manifest: WebManifest;
  target: TargetId;
};

const AppContext = createContext<AppContextValue | null>(null);

export function useAppContext(): AppContextValue {
  const value = useContext(AppContext);
  if (!value) throw new Error("App context is unavailable");
  return value;
}

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [manifest, setManifest] = useState<WebManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    loadManifest()
      .then((value) => {
        if (active) setManifest(value);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить медиатеку");
      });
    return () => {
      active = false;
    };
  }, []);

  const target = useMemo(() => {
    if (!manifest) return null;
    return resolveTarget(manifest, new URLSearchParams(location.search));
  }, [location.search, manifest]);

  if (error) {
    return (
      <main className="state-message" role="alert">
        <h1>Медиатека недоступна</h1>
        <p>{error}</p>
      </main>
    );
  }

  if (!manifest || !target) {
    return (
      <main className="state-message" aria-busy="true" aria-live="polite">
        <p>Загружаем медиатеку…</p>
      </main>
    );
  }

  const value = { manifest, target } satisfies AppContextValue;

  return (
    <AppContext.Provider value={value}>
      <div className="app-shell">
        <header className="site-header">
          <Link className="brand" to={`/today?target=${encodeURIComponent(target)}`}>
            Наше кино
          </Link>
          <nav aria-label="Основная навигация">
            <Link to={`/today?target=${encodeURIComponent(target)}`}>Сегодня</Link>
            <a href={libraryHref(target)}>Медиатека</a>
          </nav>
        </header>
        <main id="content">{children}</main>
      </div>
    </AppContext.Provider>
  );
}
