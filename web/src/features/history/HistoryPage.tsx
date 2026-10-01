import { motion, useReducedMotion } from "motion/react";
import { useMemo } from "react";

import { useAppContext } from "../../app/AppShell";
import { workHref } from "../../app/router";
import type { TargetId } from "../../data/types";
import { cardMotion, revealMotion } from "../../motion/transitions";
import { buildHistoryItems, type HistoryItemModel } from "./selectors";
import "./history.css";

const reactionLabels: Record<string, string> = {
  liked: "Понравилось",
  disliked: "Не понравилось",
  neutral: "Нейтрально",
  mixed: "Смешанные впечатления",
  unknown: "Без реакции",
};

function formatActivity(item: HistoryItemModel): string {
  if (!item.activityAt) return "Дата не указана";
  const date = new Date(item.activityAt);
  if (Number.isNaN(date.getTime())) return item.activityAt;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(item.activityPrecision === "exact" ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function reactionLabel(value: string): string {
  return reactionLabels[value] ?? value;
}

type HistoryViewProps = {
  items: HistoryItemModel[];
  target: TargetId;
  reduceMotion: boolean;
};

export function HistoryView({ items, target, reduceMotion }: HistoryViewProps) {
  return (
    <section className="history-page" aria-labelledby="history-title">
      <motion.header
        className="history-intro"
        data-motion={reduceMotion ? "reduced" : "full"}
        initial={reduceMotion ? false : revealMotion.hidden}
        animate={revealMotion.visible}
        transition={reduceMotion ? { duration: 0 } : revealMotion.transition}
      >
        <div className="history-intro__title">
          <h1 id="history-title">История</h1>
          <p>{items.length} в истории</p>
        </div>
        <p className="history-intro__lede">Просмотры и отзывы в порядке последних изменений.</p>
      </motion.header>

      {items.length ? (
        <ol className="history-list">
          {items.map((item) => (
            <li key={item.id}>
              <motion.a
                className="history-item"
                href={workHref(item.id, target)}
                whileHover={reduceMotion ? undefined : cardMotion.hover}
                whileTap={reduceMotion ? undefined : cardMotion.tap}
                transition={reduceMotion ? { duration: 0 } : cardMotion.transition}
              >
                <time className="history-item__date" dateTime={item.activityAt || undefined}>
                  {formatActivity(item)}
                </time>
                <span className="history-item__poster">
                  {item.posterUrl ? (
                    <img src={item.posterUrl} alt="" loading="lazy" />
                  ) : (
                    <span className="history-item__missing" aria-hidden="true">Нет постера</span>
                  )}
                </span>
                <span className="history-item__copy">
                  <span className="history-item__heading">
                    <strong>{item.title}</strong>
                    {item.year !== null ? <small>{item.year}</small> : null}
                  </span>
                  {item.rating !== null || item.reaction ? (
                    <span className="history-item__signals">
                      {item.rating !== null ? <span>{item.rating}/10</span> : null}
                      {item.reaction ? <span>{reactionLabel(item.reaction)}</span> : null}
                    </span>
                  ) : null}
                  {item.feedbackSummary ? <p>{item.feedbackSummary}</p> : null}
                </span>
              </motion.a>
            </li>
          ))}
        </ol>
      ) : (
        <div className="history-zero" role="status">
          <h2>Здесь пока пусто</h2>
          <p>После просмотра или отзыва фильм появится здесь.</p>
        </div>
      )}
    </section>
  );
}

export function HistoryPage() {
  const { manifest, target } = useAppContext();
  const items = useMemo(() => buildHistoryItems(manifest, target), [manifest, target]);
  const reduceMotion = Boolean(useReducedMotion());
  return <HistoryView items={items} target={target} reduceMotion={reduceMotion} />;
}
