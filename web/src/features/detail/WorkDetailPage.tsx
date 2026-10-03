import { Clock, PencilSimple, Plus, Star } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { Fragment, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { useAppContext } from "../../app/AppShell";
import { useBrokerSession } from "../../broker/BrokerSessionProvider";
import type { TargetId } from "../../data/types";
import { revealMotion } from "../../motion/transitions";
import { FeedbackEditor } from "./FeedbackEditor";
import { buildWorkDetailView, type DetailSignal, type WorkDetailModel } from "./selectors";
import "./detail.css";
import "./intelligence.css";

const TARGET_LABELS: Record<string, string> = {
  primary: "Я",
  partner: "Партнёр",
  couple: "Вместе",
};

const REACTION_LABELS: Record<string, string> = {
  liked: "Понравилось",
  disliked: "Не понравилось",
  neutral: "Нейтрально",
  mixed: "Смешанное впечатление",
  unknown: "Без реакции",
};

const VIEWING_LABELS: Record<string, string> = {
  watched: "Просмотрено",
  unwatched: "Не смотрели",
  partial: "Начато",
  dropped: "Брошено",
  forgotten: "Почти не помним",
};

function formatExternalRating(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

function emptySignalMessage(target: TargetId): string {
  if (target === "primary") return "Пока нет моего впечатления.";
  if (target === "partner") return "Пока нет впечатления партнёра.";
  if (target === "couple") return "Пока нет общего впечатления.";
  return "Пока нет записанного впечатления.";
}

function targetImpressionLabel(target: TargetId): string {
  if (target === "primary") return "моё впечатление";
  if (target === "partner") return "впечатление партнёра";
  if (target === "couple") return "общее впечатление";
  return "впечатление";
}

function SignalPanel({
  target,
  signal,
  active,
  editAction,
  column,
}: {
  target: TargetId;
  signal: DetailSignal | null;
  active: boolean;
  editAction?: React.ReactNode;
  column: number;
}) {
  return (
    <article
      className={`signal-panel${active ? " signal-panel--active" : ""}`}
      style={{ gridColumn: column, gridRow: 1 }}
    >
      <div className="signal-panel__heading">
        <h3>{TARGET_LABELS[target] ?? target}</h3>
      </div>
      {signal ? (
        <>
          <dl>
            {signal.rating !== null ? (
              <div>
                <dt>Оценка</dt>
                <dd>{signal.rating}/10</dd>
              </div>
            ) : null}
            {signal.reaction ? (
              <div>
                <dt>Реакция</dt>
                <dd>{REACTION_LABELS[signal.reaction] ?? signal.reaction}</dd>
              </div>
            ) : null}
            {signal.viewingStatus ? (
              <div>
                <dt>Просмотр</dt>
                <dd>{VIEWING_LABELS[signal.viewingStatus] ?? signal.viewingStatus}</dd>
              </div>
            ) : null}
          </dl>
          {signal.feedbackSummary ? <p className="signal-panel__summary">{signal.feedbackSummary}</p> : null}
        </>
      ) : (
        <p className="signal-panel__empty">{emptySignalMessage(target)}</p>
      )}
      {editAction ? <div className="signal-panel__action">{editAction}</div> : null}
    </article>
  );
}

export function WorkDetailView({
  view,
  activeTarget,
  editControl,
  editActions,
  editingTarget = null,
  editorPanel,
}: {
  view: WorkDetailModel;
  activeTarget: TargetId;
  editControl?: React.ReactNode;
  editActions?: Partial<Record<TargetId, React.ReactNode>>;
  editingTarget?: TargetId | null;
  editorPanel?: React.ReactNode;
}) {
  const reduceMotion = useReducedMotion();
  const targetIds = Object.keys(view.signals) as TargetId[];
  const orderedTargets = [activeTarget, ...targetIds.filter((target) => target !== activeTarget)];

  const hasCredits = view.directors.length > 0 || view.cast.length > 0;
  const revealInitial = reduceMotion ? false : revealMotion.hidden;
  const revealTransition = reduceMotion ? { duration: 0 } : revealMotion.transition;
  const signalColumnCount = Math.min(Math.max(orderedTargets.length, 1), 3);

  return (
    <article className="detail-page">
      <motion.header
        className={`detail-hero${view.backdropUrl ? " detail-hero--with-image" : ""}`}
        data-motion={reduceMotion ? "reduced" : "full"}
        style={
          view.backdropUrl
            ? ({ "--detail-backdrop": `url("${view.backdropUrl}")` } as React.CSSProperties)
            : undefined
        }
        initial={revealInitial}
        animate={revealMotion.visible}
        transition={revealTransition}
      >
        <div className="detail-hero__scrim" aria-hidden="true" />
        <div className="detail-hero__poster" aria-hidden="true">
          {view.posterUrl ? <img src={view.posterUrl} alt="" /> : <span>Нет постера</span>}
        </div>
        <div className="detail-hero__copy">
          <p className="eyebrow">Карточка фильма</p>
          <h1>{view.title}</h1>
          {view.titleOriginal && view.titleOriginal !== view.title ? (
            <p className="detail-hero__original">{view.titleOriginal}</p>
          ) : null}
          <div className="detail-hero__meta">
            {view.year ? <span>{view.year}</span> : null}
            {view.runtimeMin ? (
              <span><Clock aria-hidden="true" /> {view.runtimeMin} мин</span>
            ) : null}
            {view.genreLabels.map((genre) => <span key={genre}>{genre}</span>)}
          </div>
          {view.synopsis ? <p className="detail-hero__synopsis">{view.synopsis}</p> : null}
        </div>
      </motion.header>

      <motion.section
        className="detail-signals"
        aria-labelledby="detail-signals-title"
        initial={revealInitial}
        whileInView={revealMotion.visible}
        viewport={{ once: true, amount: 0.16 }}
        transition={revealTransition}
      >
        <div className="detail-section-heading">
          <p className="eyebrow">Личное</p>
          <h2 id="detail-signals-title">Наши впечатления</h2>
        </div>
        <div className={`signal-grid signal-grid--${signalColumnCount}`}>
          {orderedTargets.map((target, index) => (
            <Fragment key={target}>
              <SignalPanel
                target={target}
                signal={view.signals[target] ?? null}
                active={target === activeTarget}
                editAction={editActions?.[target]}
                column={index + 1}
              />
              {editingTarget === target && editorPanel ? (
                <div className="feedback-editor-panel" data-edit-target={target}>
                  {editorPanel}
                </div>
              ) : null}
            </Fragment>
          ))}
        </div>
        {!editActions ? (editControl ?? (
          <div className="future-edit-boundary" data-testid="future-edit-boundary">
            <span>Режим только для чтения</span>
          </div>
        )) : null}
      </motion.section>

      {view.fingerprint.length ? (
        <motion.section
          className="detail-fingerprint"
          aria-labelledby="detail-fingerprint-title"
          initial={revealInitial}
          whileInView={revealMotion.visible}
          viewport={{ once: true, amount: 0.16 }}
          transition={revealTransition}
        >
          <div className="detail-section-heading">
            <p className="eyebrow">Характер фильма</p>
            <h2 id="detail-fingerprint-title">О фильме</h2>
          </div>
          <ul className="detail-fingerprint__traits">
            {view.fingerprint.map((trait) => (
              <li key={trait.term}>
                <strong>{trait.label}</strong>
                <span>{trait.source} · {trait.confidence} уверенность</span>
              </li>
            ))}
          </ul>
        </motion.section>
      ) : null}

      {view.similarities.length ? (
        <motion.section
          className="detail-similarities"
          aria-labelledby="detail-similarities-title"
          initial={revealInitial}
          whileInView={revealMotion.visible}
          viewport={{ once: true, amount: 0.16 }}
          transition={revealTransition}
        >
          <div className="detail-section-heading">
            <p className="eyebrow">По твоему мнению</p>
            <h2 id="detail-similarities-title">Похожие фильмы</h2>
          </div>
          <ul className="detail-similarities__list">
            {view.similarities.map((item) => (
              <li key={item.key}>
                {item.href ? (
                  <a className="detail-similarity__title" href={item.href}>
                    <strong>{item.title}</strong>
                    {item.year ? <span>{item.year}</span> : null}
                  </a>
                ) : (
                  <div className="detail-similarity__title">
                    <strong>{item.title}</strong>
                    <span>{[item.year, item.provider].filter(Boolean).join(" · ")}</span>
                  </div>
                )}
                {item.terms.length ? <p>{item.terms.join(" · ")}</p> : null}
                {item.note ? <p className="detail-similarity__note">{item.note}</p> : null}
              </li>
            ))}
          </ul>
        </motion.section>
      ) : null}

      {view.externalRating !== null ? (
        <motion.section
          className="detail-external"
          aria-labelledby="detail-external-title"
          initial={revealInitial}
          whileInView={revealMotion.visible}
          viewport={{ once: true, amount: 0.2 }}
          transition={revealTransition}
        >
          <div>
            <p className="eyebrow">Внешний контекст</p>
            <h2 id="detail-external-title">TMDB</h2>
          </div>
          <p className="external-score">
            <Star aria-hidden="true" weight="fill" />
            <strong>{formatExternalRating(view.externalRating)}</strong>
            <span>/10{view.externalVotes !== null ? ` · ${view.externalVotes.toLocaleString("ru-RU")} оценок` : ""}</span>
          </p>
        </motion.section>
      ) : null}

      {hasCredits ? (
        <motion.section
          className="detail-credits"
          aria-labelledby="detail-credits-title"
          initial={revealInitial}
          whileInView={revealMotion.visible}
          viewport={{ once: true, amount: 0.14 }}
          transition={revealTransition}
        >
          <div className="detail-section-heading">
            <p className="eyebrow">Создатели</p>
            <h2 id="detail-credits-title">Кто сделал фильм</h2>
          </div>
          {view.directors.length ? (
            <div className="credit-block">
              <h3>Режиссура</h3>
              <p>{view.directors.map((person) => person.name).join(", ")}</p>
            </div>
          ) : null}
          {view.cast.length ? (
            <div className="credit-block">
              <h3>В ролях</h3>
              <ul>
                {view.cast.slice(0, 10).map((person) => (
                  <li key={`${person.name}-${person.character ?? ""}`}>
                    <span>{person.name}</span>
                    {person.character ? <small>{person.character}</small> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </motion.section>
      ) : null}
    </article>
  );
}

export function WorkDetailPage() {
  const { id } = useParams();
  const { manifest, target, refreshManifest } = useAppContext();
  const broker = useBrokerSession();
  const view = id ? buildWorkDetailView(manifest, id, target) : null;
  const [editingTarget, setEditingTarget] = useState<TargetId | null>(null);
  const [loginTarget, setLoginTarget] = useState<TargetId | null>(null);

  useEffect(() => {
    setEditingTarget(null);
    setLoginTarget(null);
  }, [id, target]);

  useEffect(() => {
    if (!loginTarget || !broker.authenticated) return;
    setEditingTarget(loginTarget);
    setLoginTarget(null);
  }, [broker.authenticated, loginTarget]);

  if (!view) {
    return (
      <section className="detail-missing" role="status">
        <p className="eyebrow">Фильм не найден</p>
        <h1>Такой записи нет в медиатеке</h1>
        <a href={`#/library?target=${encodeURIComponent(target)}`}>Вернуться в медиатеку</a>
      </section>
    );
  }

  const beginEditing = (editTarget: TargetId) => {
    if (editingTarget || loginTarget) return;
    if (!broker.authenticated) {
      setLoginTarget(editTarget);
      broker.login();
      return;
    }
    setEditingTarget(editTarget);
  };

  const editActions = broker.configured
    ? (Object.keys(view.signals) as TargetId[]).reduce<Partial<Record<TargetId, React.ReactNode>>>((actions, editTarget) => {
        const signal = view.signals[editTarget] ?? null;
        const isEditing = editingTarget === editTarget;
        const isLoggingIn = loginTarget === editTarget;
        const disabled = Boolean(editingTarget || loginTarget);
        const actionVerb = signal ? "Изменить" : "Добавить";

        if (isEditing) {
          actions[editTarget] = (
            <span className="signal-panel__editing-status" role="status">
              Редактируется
            </span>
          );
          return actions;
        }

        actions[editTarget] = (
          <button
            className={`signal-panel__edit-button${disabled ? " signal-panel__edit-button--blocked" : ""}`}
            type="button"
            onClick={() => beginEditing(editTarget)}
            disabled={disabled}
            aria-label={`${actionVerb} ${targetImpressionLabel(editTarget)}`}
          >
            {signal ? <PencilSimple aria-hidden="true" /> : <Plus aria-hidden="true" />}
            <span>{isLoggingIn ? "Входим…" : actionVerb}</span>
          </button>
        );
        return actions;
      }, {})
    : undefined;

  const editSignal = editingTarget ? view.signals[editingTarget] ?? null : null;
  const canCopyPrimary = editingTarget === "couple" && !editSignal && Boolean(view.signals.primary);
  const editorPanel = editingTarget ? (
    <FeedbackEditor
      key={`${view.id}:${editingTarget}`}
      workId={view.id}
      target={editingTarget}
      signal={editSignal}
      templateSignal={canCopyPrimary ? view.signals.primary : null}
      templateSourceTarget={canCopyPrimary ? "primary" : undefined}
      broker={broker}
      refreshManifest={refreshManifest}
      open
      hideTrigger
      onOpenChange={(nextOpen) => {
        if (!nextOpen) setEditingTarget(null);
      }}
    />
  ) : undefined;

  return (
    <WorkDetailView
      view={view}
      activeTarget={target}
      editActions={editActions}
      editingTarget={editingTarget}
      editorPanel={editorPanel}
    />
  );
}
