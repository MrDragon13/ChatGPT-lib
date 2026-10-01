import { MagnifyingGlass } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useAppContext } from "../../app/AppShell";
import { workHref } from "../../app/router";
import { tmdbImageUrl } from "../../data/assets";
import type { WebWork } from "../../data/types";
import { cardMotion, revealMotion } from "../../motion/transitions";
import {
  filterLibrary,
  libraryFiltersFromSearchParams,
  libraryFiltersToSearchParams,
  type LibraryFilters,
} from "./selectors";
import "./library.css";

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function posterUrl(work: WebWork): string | null {
  const assets = record(work.metadata.external.assets);
  const poster = record(assets?.poster);
  return tmdbImageUrl(typeof poster?.path === "string" ? poster.path : null, "w500");
}

function workTitle(work: WebWork): string {
  return String(work.identity.title_ru ?? work.identity.title_original ?? work.id);
}

function genreOptions(works: WebWork[], vocabulary: Record<string, { label_ru: string }>) {
  const values = new Set<string>();
  for (const work of works) stringArray(work.metadata.external.genres).forEach((genre) => values.add(genre));
  return [...values]
    .map((value) => ({ value, label: vocabulary[value]?.label_ru ?? value }))
    .sort((left, right) => left.label.localeCompare(right.label, "ru-RU"));
}

function yearOptions(works: WebWork[]): number[] {
  return [...new Set(works.map((work) => work.identity.year).filter((year): year is number => typeof year === "number"))].sort(
    (left, right) => right - left,
  );
}

export function LibraryPage() {
  const { manifest, target } = useAppContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = libraryFiltersFromSearchParams(searchParams);
  const results = useMemo(() => filterLibrary(manifest, target, filters), [filters, manifest, target]);
  const genres = useMemo(() => genreOptions(manifest.works, manifest.vocabulary), [manifest]);
  const years = useMemo(() => yearOptions(manifest.works), [manifest.works]);
  const reduceMotion = useReducedMotion();

  const update = (patch: Partial<LibraryFilters>) => {
    const next = { ...filters, ...patch };
    setSearchParams(libraryFiltersToSearchParams(next, target), { replace: true });
  };

  return (
    <section className="library-page" aria-labelledby="library-title">
      <motion.header
        className="library-intro"
        data-motion={reduceMotion ? "reduced" : "full"}
        initial={reduceMotion ? false : revealMotion.hidden}
        animate={revealMotion.visible}
        transition={reduceMotion ? { duration: 0 } : revealMotion.transition}
      >
        <p className="eyebrow">Вся коллекция</p>
        <div>
          <h1 id="library-title">Медиатека</h1>
          <p>{results.length} из {manifest.works.length}</p>
        </div>
      </motion.header>

      <form className="library-filters" onSubmit={(event) => event.preventDefault()}>
        <label className="search-field">
          <span>Поиск</span>
          <span className="search-field__control">
            <MagnifyingGlass aria-hidden="true" />
            <input
              type="search"
              value={filters.query}
              placeholder="Название фильма или сериала"
              onChange={(event) => update({ query: event.target.value })}
            />
          </span>
        </label>

        <label>
          <span>Просмотр</span>
          <select value={filters.viewing} onChange={(event) => update({ viewing: event.target.value as LibraryFilters["viewing"] })}>
            <option value="all">Все</option>
            <option value="unwatched">Не смотрели</option>
            <option value="watched">Просмотрено</option>
          </select>
        </label>

        <label>
          <span>Жанр</span>
          <select value={filters.genre ?? ""} onChange={(event) => update({ genre: event.target.value || null })}>
            <option value="">Все жанры</option>
            {genres.map((genre) => (
              <option value={genre.value} key={genre.value}>{genre.label}</option>
            ))}
          </select>
        </label>

        <label>
          <span>Год</span>
          <select value={filters.year ?? ""} onChange={(event) => update({ year: event.target.value ? Number(event.target.value) : null })}>
            <option value="">Все годы</option>
            {years.map((year) => (
              <option value={year} key={year}>{year}</option>
            ))}
          </select>
        </label>
      </form>

      {results.length ? (
        <div className="library-grid" aria-live="polite">
          {results.map((work) => {
            const poster = posterUrl(work);
            return (
              <motion.a
                className="library-card"
                href={workHref(work.id, target)}
                key={work.id}
                whileHover={reduceMotion ? undefined : cardMotion.hover}
                whileTap={reduceMotion ? undefined : cardMotion.tap}
                transition={reduceMotion ? { duration: 0 } : cardMotion.transition}
              >
                <span className="library-card__poster">
                  {poster ? <img src={poster} alt="" loading="lazy" /> : <span className="library-card__missing" aria-hidden="true">Нет постера</span>}
                </span>
                <span className="library-card__copy">
                  <strong>{workTitle(work)}</strong>
                  <small>{[work.identity.year, work.identity.title_original !== work.identity.title_ru ? work.identity.title_original : null].filter(Boolean).join(" · ")}</small>
                </span>
              </motion.a>
            );
          })}
        </div>
      ) : (
        <div className="library-zero" role="status">
          <p className="eyebrow">Ничего не найдено</p>
          <h2>С такими фильтрами пусто</h2>
          <p>Измените поиск, жанр, год или статус просмотра — данные медиатеки не изменятся.</p>
          <button type="button" onClick={() => update({ query: "", viewing: "all", genre: null, year: null })}>Сбросить фильтры</button>
        </div>
      )}
    </section>
  );
}
