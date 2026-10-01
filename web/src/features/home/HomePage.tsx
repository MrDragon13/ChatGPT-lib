import { ArrowRight, Clock } from "@phosphor-icons/react";

import { workHref } from "../../app/router";
import { useAppContext } from "../../app/AppShell";
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

function CandidateThumb({ candidate, target }: { candidate: HomeCandidate; target: string }) {
  return (
    <a className="candidate-thumb" href={workHref(candidate.id, target)}>
      <span className="candidate-thumb__image" aria-hidden="true">
        {candidate.posterUrl ? <img src={candidate.posterUrl} alt="" loading="lazy" /> : <span />}
      </span>
      <span className="candidate-thumb__copy">
        <strong>{candidate.title}</strong>
        <small>{formatMeta(candidate).slice(0, 2).join(" · ")}</small>
      </span>
    </a>
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
    <section className="poster-section" aria-labelledby={`rail-${title}`}>
      <div className="section-heading">
        <h2 id={`rail-${title}`}>{title}</h2>
      </div>
      <div className="poster-rail">
        {items.map((item) => (
          <a className="poster-card" href={workHref(item.id, target)} key={item.id}>
            <span className="poster-card__art">
              {item.posterUrl ? <img src={item.posterUrl} alt="" loading="lazy" /> : <span aria-hidden="true" />}
            </span>
            <span className="poster-card__copy">
              <strong>{item.title}</strong>
              <small>{formatMeta(item).slice(0, 2).join(" · ")}</small>
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}

export function HomePage() {
  const { manifest, target } = useAppContext();
  const model = buildHomeViewModel(manifest, target);

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

  const hero = model.hero;
  const reasons = hero.reasonLabels.slice(0, 3);

  return (
    <div className="home-page">
      <section
        className={`cinema-hero${hero.backdropUrl ? " cinema-hero--with-image" : ""}`}
        style={hero.backdropUrl ? { "--hero-backdrop": `url("${hero.backdropUrl}")` } as React.CSSProperties : undefined}
        aria-labelledby="hero-title"
      >
        <div className="cinema-hero__scrim" aria-hidden="true" />
        <div className="cinema-hero__content">
          <p className="eyebrow">Сегодня · {target === "couple" ? "для двоих" : "для вас"}</p>
          <h1 id="hero-title">{hero.title}</h1>
          {hero.titleOriginal && hero.titleOriginal !== hero.title ? (
            <p className="cinema-hero__original">{hero.titleOriginal}</p>
          ) : null}
          <div className="cinema-hero__meta" aria-label="Сведения о фильме">
            {hero.year ? <span>{hero.year}</span> : null}
            {hero.runtimeMin ? (
              <span>
                <Clock aria-hidden="true" weight="regular" /> {hero.runtimeMin} мин
              </span>
            ) : null}
            {hero.genreLabels.slice(0, 2).map((genre) => (
              <span key={genre}>{genre}</span>
            ))}
          </div>
          {reasons.length ? (
            <div className="cinema-hero__reason">
              <span>Почему сейчас</span>
              <p>{reasons.join(" · ")}</p>
            </div>
          ) : null}
          <a className="hero-action" href={workHref(hero.id, target)}>
            Подробнее <ArrowRight aria-hidden="true" weight="bold" />
          </a>
        </div>

        <div className="cinema-hero__poster" aria-hidden="true">
          {hero.posterUrl ? <img src={hero.posterUrl} alt="" /> : <span />}
        </div>

        {model.alternatives.length ? (
          <div className="cinema-hero__alternatives" aria-label="Ещё варианты">
            <span className="cinema-hero__alternatives-label">Ещё варианты</span>
            {model.alternatives.map((candidate) => (
              <CandidateThumb candidate={candidate} target={target} key={candidate.id} />
            ))}
          </div>
        ) : null}
      </section>

      {target !== "couple" ? <PosterRail title="Для двоих" items={model.couple} target="couple" /> : null}
      <PosterRail title="Недавно смотрели" items={model.recent} target={target} />
    </div>
  );
}
