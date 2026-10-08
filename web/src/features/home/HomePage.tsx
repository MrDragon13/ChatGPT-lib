import { ArrowRight, Clock } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { workHref } from "../../app/router";
import { useAppContext } from "../../app/AppShell";
import { cardMotion, heroMotion, revealMotion } from "../../motion/transitions";
import type { HomeCandidate, HomeTasteModel } from "./selectors";
import { buildHomeViewModel } from "./selectors";
import "./home.css";
import "./intelligence.css";

function formatMeta(candidate: HomeCandidate): string[] {
  const values: string[] = [];
  if (candidate.year) values.push(String(candidate.year));
  if (candidate.runtimeMin) values.push(`${candidate.runtimeMin} мин`);
  values.push(...candidate.genreLabels.slice(0, 2));
  return values;
}

function confidenceLabel(value: string | null): string | null {
  const labels: Record<string, string> = {
    exact: "точно",
    high: "высокая уверенность",
    medium: "средняя уверенность",
    low: "низкая уверенность",
  };
  return value ? labels[value] ?? null : null;
}

function TasteSection({ taste, target }: { taste: HomeTasteModel; target: string }) {
  const reduceMotion = useReducedMotion();
  const title = target === "couple" ? "Наш вкус" : target === "partner" ? "Вкус партнёра" : "Мой вкус";
  return (
    <motion.section
      className="taste-section"
      aria-labelledby="taste-section-title"
      data-testid="taste-section"
      initial={reduceMotion ? false : revealMotion.hidden}
      whileInView={revealMotion.visible}
      viewport={{ once: true, amount: 0.16 }}
      transition={reduceMotion ? { duration: 0 } : revealMotion.transition}
    >
      <div className="taste-section__heading">
        <p className="eyebrow">Профиль</p>
        <h2 id="taste-section-title">{title}</h2>
      </div>
      <div className="taste-section__body">
        {taste.strongest.length ? (
          <div className="taste-affinities" aria-label="Сильные сигналы вкуса">
            {taste.strongest.map((item) => (
              <div className="taste-affinity" key={item.term}>
                <strong>{item.label}</strong>
                <span>
                  {item.score >= 0 ? "Скорее нравится" : "Скорее не нравится"} · {item.evidenceCount} подтвержд.
                </span>
              </div>
            ))}
          </div>
        ) : null}

        {taste.explicit.length || taste.inferred.length ? (
          <div className="taste-statements">
            {taste.explicit.length ? (
              <div>
                <h3>Сказано явно</h3>
                <ul>
                  {taste.explicit.map((item) => (
                    <li key={item.id}>
                      <p>{item.statement}</p>
                      {item.label ? <span className="taste-statement__meta">{item.label}</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {taste.inferred.length ? (
              <div>
                <h3>Наблюдения</h3>
                <ul>
                  {taste.inferred.map((item) => (
                    <li key={item.id}>
                      <p>{item.statement}</p>
                      <span className="taste-statement__meta">
                        Гипотеза{confidenceLabel(item.confidence) ? ` · ${confidenceLabel(item.confidence)}` : ""}
                      </span>
                      {item.evidence.length ? (
                        <details className="taste-evidence">
                          <summary>Почему система так думает?</summary>
                          <ul>
                            {item.evidence.map((evidence) => (
                              <li key={evidence.workId}>
                                <a href={workHref(evidence.workId, target)}>{evidence.title}</a>
                              </li>
                            ))}
                          </ul>
                        </details>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {taste.couple ? (
          <div className="taste-couple">
            <h3>Для двоих</h3>
            <p><strong>{taste.couple.agreements}</strong> совпадений</p>
            <p><strong>{taste.couple.disagreements}</strong> расхождений</p>
          </div>
        ) : null}
      </div>
    </motion.section>
  );
}

function CandidateThumb({
  candidate,
  target,
  onPreview,
}: {
  candidate: HomeCandidate;
  target: string;
  onPreview: () => void;
}) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.a
      className="candidate-thumb"
      href={workHref(candidate.id, target)}
      onPointerEnter={onPreview}
      onFocus={onPreview}
      whileHover={reduceMotion ? undefined : cardMotion.hover}
      whileTap={reduceMotion ? undefined : cardMotion.tap}
      transition={reduceMotion ? { duration: 0 } : cardMotion.transition}
    >
      <span className="candidate-thumb__image" aria-hidden="true">
        {candidate.posterUrl ? <img src={candidate.posterUrl} alt="" loading="lazy" /> : <span />}
      </span>
      <span className="candidate-thumb__copy">
        <strong>{candidate.title}</strong>
        <small>{formatMeta(candidate).slice(0, 2).join(" · ")}</small>
      </span>
    </motion.a>
  );
}

function PosterRail({
  title,
  items,
  target,
}: {
  title: string;
  items: HomeCandidate[];
  target: string;
}) {
  const reduceMotion = useReducedMotion();
  if (!items.length) return null;
  const headingId = `rail-${title.replaceAll(" ", "-").toLowerCase()}`;
  return (
    <motion.section
      className="poster-section"
      aria-labelledby={headingId}
      initial={reduceMotion ? false : revealMotion.hidden}
      whileInView={revealMotion.visible}
      viewport={{ once: true, amount: 0.18 }}
      transition={reduceMotion ? { duration: 0 } : revealMotion.transition}
    >
      <div className="section-heading">
        <h2 id={headingId}>{title}</h2>
      </div>
      <div className="poster-rail">
        {items.map((item) => (
          <motion.a
            className="poster-card"
            href={workHref(item.id, target)}
            key={item.id}
            whileHover={reduceMotion ? undefined : cardMotion.hover}
            whileTap={reduceMotion ? undefined : cardMotion.tap}
            transition={reduceMotion ? { duration: 0 } : cardMotion.transition}
          >
            <span className="poster-card__art">
              {item.posterUrl ? <img src={item.posterUrl} alt="" loading="lazy" /> : <span aria-hidden="true" />}
            </span>
            <span className="poster-card__copy">
              <strong>{item.title}</strong>
              <small>{formatMeta(item).slice(0, 2).join(" · ")}</small>
            </span>
          </motion.a>
        ))}
      </div>
    </motion.section>
  );
}

export function HomePage() {
  const { manifest, target } = useAppContext();
  const model = buildHomeViewModel(manifest, target);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  if (!model.hero) {
    const libraryIsEmpty = manifest.works.length === 0;
    return (
      <section
        className="home-empty"
        aria-labelledby="home-empty-title"
        data-testid="home-empty"
        data-motion={reduceMotion ? "reduced" : "full"}
      >
        <p className="eyebrow">Сегодня</p>
        <h1 id="home-empty-title">Пока без готовой рекомендации</h1>
        <p>
          {libraryIsEmpty
            ? "Медиатека пока пуста. Добавьте первый фильм через ChatGPT — после сохранения он появится здесь."
            : "Подходящего кандидата сейчас нет. Можно открыть медиатеку и выбрать вручную."}
        </p>
        <a className="text-link" href={`#/library?target=${encodeURIComponent(target)}`}>
          Открыть медиатеку <ArrowRight aria-hidden="true" weight="bold" />
        </a>
      </section>
    );
  }

  const activeHero =
    [model.hero, ...model.alternatives].find((candidate) => candidate.id === previewId) ?? model.hero;
  const reasons = activeHero.reasonLabels.slice(0, 3);

  return (
    <div className="home-page">
      {model.reanalysisDue ? (
        <aside className="home-reanalysis-notice" role="status" data-testid="reanalysis-notice">
          <strong>Профиль вкуса накопил новые оценки.</strong>
          <span>Перед следующим точным подбором обновите анализ в киноассистенте.</span>
        </aside>
      ) : null}
      <section
        className="cinema-hero"
        aria-labelledby="hero-title"
        data-testid="cinema-hero"
        data-motion={reduceMotion ? "reduced" : "full"}
      >
        <AnimatePresence initial={!reduceMotion}>
          {activeHero.backdropUrl ? (
            <motion.div
              className="cinema-hero__backdrop"
              key={activeHero.id}
              style={{ backgroundImage: `url("${activeHero.backdropUrl}")` }}
              initial={reduceMotion ? false : { opacity: 0, scale: 1.025 }}
              animate={{ opacity: 0.78, scale: 1.012 }}
              exit={reduceMotion ? undefined : { opacity: 0, scale: 1.006 }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.72, ease: [0.32, 0.72, 0, 1] }}
              aria-hidden="true"
            />
          ) : null}
        </AnimatePresence>
        <div className="cinema-hero__scrim" aria-hidden="true" />

        <motion.div
          className="cinema-hero__content"
          key={activeHero.id}
          initial={reduceMotion ? false : heroMotion.initial}
          animate={heroMotion.enter}
          transition={reduceMotion ? { duration: 0 } : heroMotion.transition}
        >
          <p className="eyebrow">Сегодня · {target === "couple" ? "для двоих" : "для вас"}</p>
          <h1 id="hero-title">{activeHero.title}</h1>
          {activeHero.titleOriginal && activeHero.titleOriginal !== activeHero.title ? (
            <p className="cinema-hero__original">{activeHero.titleOriginal}</p>
          ) : null}
          <div className="cinema-hero__meta" aria-label="Сведения о фильме">
            {activeHero.year ? <span>{activeHero.year}</span> : null}
            {activeHero.runtimeMin ? (
              <span>
                <Clock aria-hidden="true" weight="regular" /> {activeHero.runtimeMin} мин
              </span>
            ) : null}
            {activeHero.genreLabels.slice(0, 2).map((genre) => (
              <span key={genre}>{genre}</span>
            ))}
          </div>
          {reasons.length ? (
            <div className="cinema-hero__reason">
              <span>Почему сейчас</span>
              <p>{reasons.join(" · ")}</p>
            </div>
          ) : null}
          <motion.a
            className="hero-action"
            href={workHref(activeHero.id, target)}
            whileTap={reduceMotion ? undefined : cardMotion.tap}
            transition={reduceMotion ? { duration: 0 } : cardMotion.transition}
          >
            Подробнее <ArrowRight aria-hidden="true" weight="bold" />
          </motion.a>
        </motion.div>

        <motion.div
          className="cinema-hero__poster"
          key={`poster-${activeHero.id}`}
          initial={reduceMotion ? false : { opacity: 0, y: 18, rotate: 0.4 }}
          animate={{ opacity: 1, y: 0, rotate: reduceMotion ? 0 : 1.4 }}
          transition={reduceMotion ? { duration: 0 } : heroMotion.transition}
          aria-hidden="true"
        >
          {activeHero.posterUrl ? <img src={activeHero.posterUrl} alt="" /> : <span />}
        </motion.div>

        {model.alternatives.length ? (
          <div className="cinema-hero__alternatives" aria-label="Ещё варианты">
            <span className="cinema-hero__alternatives-label">Ещё варианты</span>
            {model.alternatives.map((candidate) => (
              <CandidateThumb
                candidate={candidate}
                target={target}
                key={candidate.id}
                onPreview={() => setPreviewId(candidate.id)}
              />
            ))}
          </div>
        ) : null}
      </section>

      {model.taste ? <TasteSection taste={model.taste} target={target} /> : null}
      <PosterRail title="Посмотреть следующим" items={model.next} target={target} />
      {target !== "couple" ? <PosterRail title="Для двоих" items={model.couple} target="couple" /> : null}
      <PosterRail title="Недавно смотрели" items={model.recent} target={target} />
    </div>
  );
}
