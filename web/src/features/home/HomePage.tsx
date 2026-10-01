import { ArrowRight, Clock } from "@phosphor-icons/react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { workHref } from "../../app/router";
import { useAppContext } from "../../app/AppShell";
import { cardMotion, heroMotion, revealMotion } from "../../motion/transitions";
import type { HomeCandidate } from "./selectors";
import { buildHomeViewModel } from "./selectors";
import "./home.css";

function formatMeta(candidate: HomeCandidate): string[] {
  const values: string[] = [];
  if (candidate.year) values.push(String(candidate.year));
  if (candidate.runtimeMin) values.push(`${candidate.runtimeMin} мин`);
  values.push(...candidate.genreLabels.slice(0, 2));
  return values;
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
  return (
    <motion.a
      className="candidate-thumb"
      href={workHref(candidate.id, target)}
      onPointerEnter={onPreview}
      onFocus={onPreview}
      whileHover={cardMotion.hover}
      whileTap={cardMotion.tap}
      transition={cardMotion.transition}
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
  if (!items.length) return null;
  return (
    <motion.section
      className="poster-section"
      aria-labelledby={`rail-${title}`}
      initial={revealMotion.hidden}
      whileInView={revealMotion.visible}
      viewport={{ once: true, amount: 0.18 }}
      transition={revealMotion.transition}
    >
      <div className="section-heading">
        <h2 id={`rail-${title}`}>{title}</h2>
      </div>
      <div className="poster-rail">
        {items.map((item) => (
          <motion.a
            className="poster-card"
            href={workHref(item.id, target)}
            key={item.id}
            whileHover={cardMotion.hover}
            whileTap={cardMotion.tap}
            transition={cardMotion.transition}
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

  if (!model.hero) {
    return (
      <section className="home-empty" aria-labelledby="home-empty-title">
        <p className="eyebrow">Сегодня</p>
        <h1 id="home-empty-title">Пока без готовой рекомендации</h1>
        <p>Медиатека на месте — можно выбрать фильм вручную и вернуться сюда позже.</p>
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
      <section className="cinema-hero" aria-labelledby="hero-title" data-testid="cinema-hero">
        <AnimatePresence initial={false}>
          {activeHero.backdropUrl ? (
            <motion.div
              className="cinema-hero__backdrop"
              key={activeHero.id}
              style={{ backgroundImage: `url("${activeHero.backdropUrl}")` }}
              initial={{ opacity: 0, scale: 1.025 }}
              animate={{ opacity: 0.78, scale: 1.012 }}
              exit={{ opacity: 0, scale: 1.006 }}
              transition={{ duration: 0.72, ease: [0.32, 0.72, 0, 1] }}
              aria-hidden="true"
            />
          ) : null}
        </AnimatePresence>
        <div className="cinema-hero__scrim" aria-hidden="true" />

        <motion.div
          className="cinema-hero__content"
          key={activeHero.id}
          initial={heroMotion.initial}
          animate={heroMotion.enter}
          transition={heroMotion.transition}
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
            whileTap={cardMotion.tap}
            transition={cardMotion.transition}
          >
            Подробнее <ArrowRight aria-hidden="true" weight="bold" />
          </motion.a>
        </motion.div>

        <motion.div
          className="cinema-hero__poster"
          key={`poster-${activeHero.id}`}
          initial={{ opacity: 0, y: 18, rotate: 0.4 }}
          animate={{ opacity: 1, y: 0, rotate: 1.4 }}
          transition={heroMotion.transition}
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

      {target !== "couple" ? <PosterRail title="Для двоих" items={model.couple} target="couple" /> : null}
      <PosterRail title="Недавно смотрели" items={model.recent} target={target} />
    </div>
  );
}
