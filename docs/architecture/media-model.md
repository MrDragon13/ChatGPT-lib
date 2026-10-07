# Media domain model

Этот документ описывает текущую v6 модель media data: что хранится как canonical, что является derived, как разделены viewers/targets, semantics, feedback и taste evidence.

## Canonical data

Основные пути:

- `media/data/works/` — одно произведение на YAML-файл;
- `media/data/collections/` — серии/франшизы;
- `media/data/lists/` — target-scoped списки;
- `media/data/interactions/` — recommendation interaction events;
- `media/data/relations/similarity/` — explicit target-specific similarity;
- `media/data/tombstones/` — redirects после identity merge;
- `media/preferences/explicit/` — явно заявленные устойчивые preferences/rules;
- `media/preferences/inferred/` — evidence-backed taste hypotheses;
- `media/config/` — viewers/groups и технические настройки;
- `media/vocabulary.yaml` — controlled semantic vocabulary.

Generated files не являются canonical и не редактируются вручную как источник новых фактов.

После v6 reset активные works/collections/similarity/interactions/inferred preferences начинаются пустыми. Это валидное canonical состояние.

## Логические слои work

Физически work остаётся одним YAML, но логически состоит из независимых слоёв:

1. **identity** — формат, названия, год, stable external IDs;
2. **metadata** — фактические сведения о произведении;
3. **semantics** — controlled semantic fingerprint;
4. **viewer/group state** — viewing, rating, reaction, feedback и другие subjective signals.

Изменение viewer feedback само по себе не делает metadata или semantics устаревшими. Изменение dynamic provider metrics само по себе не инвалидирует semantic fingerprint.

## Targets

- `primary` — основной пользователь;
- `partner` — отдельный viewer;
- `couple` — group target.

`couple` не является скрытым средним. Disagreement должен оставаться видимым. Subjective state не переносится между targets автоматически.

Для автоматического taste reanalysis независимые checkpoints существуют только у `primary` и `partner`; `couple` проверяет состояния участников и не имеет третьего счётчика.

## Explicit и inferred evidence

Explicit evidence — то, что пользователь сообщил напрямую: viewing/rating/reaction/feedback, explicit preference, interest или similarity assertion.

Inferred preference — гипотеза, построенная из независимого evidence. Она не становится самостоятельным evidence для следующего inference.

Свежий explicit signal имеет приоритет над устаревшей inferred interpretation.

## Feedback history и material evidence

History может содержать `event_id` и `material_evidence`.

Для taste checkpoint один пользовательский эпизод даёт максимум одно новое material event. Cosmetic summary edit, retry, `no_change` или metadata-only mutation не продвигают checkpoint.

Содержательная текстовая причина, которая должна влиять на taste, нормализуется в explicit `feedback.signals`; `feedback.summary` сам по себе остаётся human-readable текстом.

## Semantic fingerprint

Semantic fingerprint описывает work, не зрителя.

Он строится из фактической semantic input projection, controlled vocabulary и версии алгоритма. Rating/reaction/feedback пользователя не входят в semantic input.

Для reuse используются:

- semantic input digest;
- vocabulary digest;
- algorithm version.

Если вход и версия не изменились, fingerprint используется повторно.

## Metadata freshness

Metadata делится минимум на:

- identity-critical facts;
- относительно статические факты;
- dynamic metrics.

Stale optional metadata не блокирует human feedback существующего work.

## Viewer digest

`compute_viewer_digest(work, target)` зависит только от состояния конкретного target. Изменение metadata, semantics или другого viewer не меняет этот digest.

Digest используется как дешёвая precondition-защита от stale/repeated write.

Internal `media/generated/index.jsonl` хранит target digests для быстрого Broker/LLM read path. Public Web manifest эти digests не публикует.

## WorkRef

Операции могут ссылаться на:

- canonical work через `work_id`;
- external work через stable provider identity и display snapshot.

External reference сам по себе не создаёт canonical work, viewing, rating, reaction или interest.

## Explicit similarity

Similarity хранится отдельно и является:

- subjective;
- target-specific;
- undirected;
- способной связывать canonical и external endpoints.

Одна relation определяется как `(target, unordered pair)`. Similarity — evidence/hint для поиска, recommendation и explanation, но не preference сама по себе.

Когда external endpoint позже становится canonical work с той же stable identity, deterministic reconciliation нормализует relation без побочного создания viewer signals.

## Derived data

Из canonical state строятся:

- retrieval index;
- profiles/affinities;
- cached reanalysis status;
- taste/recommendation contexts;
- временный runtime SQLite;
- Web manifest;
- Web projection similarity.

`changed_domains` описывает, что изменилось. Отдельный dependency planner строит `DirtyPlan` и определяет минимальный набор derived outputs. Один output пересобирается максимум один раз за transaction.

## Pre-v6 archive

`docs/archive/media-library-before-v6-reset-2026-10-07.md` — human-readable историческая памятка.

Она **не является canonical data**, не участвует автоматически в taste/recommendation input и не является machine-readable restore source.

При повторном прохождении старого фильма архив может использоваться только как нейтральный checklist; старый rating/reaction/feedback не подмешивается в новый ответ без явного запроса пользователя.

## Инварианты

- canonical нельзя заменять generated state;
- unknown лучше guessed identity;
- target нельзя менять молча;
- explicit evidence выше inferred interpretation;
- semantic fingerprint описывает work, а не viewer reaction;
- similarity — evidence/hint, не preference;
- external reference не создаёт work автоматически;
- archive не является intelligence input;
- пустая библиотека — валидное состояние;
- provider outage не должен разрушать уже сохранённую stable identity.
