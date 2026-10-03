# Media intelligence

Этот документ описывает текущую recommendation/taste reasoning model. Она строит объяснимые выводы из пользовательских сигналов и semantic knowledge, но не сводит вкус к одному opaque score.

## Базовый принцип

Media intelligence разделяет четыре слоя:

1. factual metadata о произведении;
2. semantic fingerprint произведения;
3. user evidence — ratings, reactions, feedback, explicit preferences, interest и interactions;
4. inferred taste hypotheses с provenance и evidence pointers.

Смешивание этих слоёв создаёт self-reinforcing выводы, поэтому provenance сохраняется явно.

## Evidence hierarchy

Практический приоритет:

1. explicit stable user statements;
2. повторяющиеся correlations, подтверждённые независимыми сигналами;
3. один rating-derived correlation как слабое/ограниченное evidence.

Inferred output **не является independent evidence** для другого inferred output. Гипотеза может быть пересчитана из raw/explicit evidence, но не должна усиливаться только потому, что предыдущая версия уже существовала.

## Taste context

`taste_context` — компактный read model для reasoning. Он может включать:

- explicit preferences/constraints;
- inferred hypotheses;
- representative liked/disliked works;
- recent meaningful feedback;
- exclusions;
- strongest evidence-backed affinities;
- explicit work similarity;
- для `couple` — agreement/disagreement без скрытого усреднения.

Taste context — память/контекст, а не готовая формула ranking.

## Internal и external recommendation routing

### Internal

Если пользователь явно просит «что посмотреть из моей медиатеки?», candidate boundary — локальная библиотека/index.

### External

Обычная просьба «посоветуй фильм» использует external discovery по умолчанию. Локальная media library служит памятью о вкусах, evidence, exclusions и semantic anchors, но не ограничивает каталог кандидатов.

Временные ограничения вроде mood, runtime или «не сегодня» относятся к текущему request context и не превращаются в permanent preference без explicit stable statement.

## Explicit similarity

User-declared work similarity — полезная cross-work связь для рекомендаций, сравнений и explanations.

Ключевой инвариант: **similarity не является preference сама по себе**. Assertion «A похож на B» не означает автоматически «мне нравится trait X» и не должна одна создавать affinity/stable taste hypothesis.

Similarity может усиливать reasoning, когда рядом есть independent evidence: например, пользователь любит A, считает A похожим на B и отдельно положительно оценил B. При противоположных ratings та же similarity полезна как counterexample.

LLM-derived semantic similarity остаётся derived knowledge и не выдаётся за explicit пользовательское утверждение.

## Candidate assessment

Для вопроса «понравится ли мне X?» используется `assess_candidate`.

`assess_candidate` — **read-only** capability. Он может работать как с canonical work, так и с external candidate и не обязан добавлять внешний фильм в library.

Контекст оценки включает:

- target taste evidence;
- candidate metadata/semantic fingerprint, если доступен;
- concrete liked/disliked anchors;
- explicit similarity relations;
- optional current request text/constraints.

Сам assessment не записывает prediction в canonical taste state.

## Формат вывода assessment

Финальный user-facing вывод остаётся **qualitative**:

- `likely / mixed / unlikely` или эквивалентная естественная формулировка;
- confidence `low / medium / high`;
- positive reasons;
- risks/counterevidence;
- concrete evidence works;
- distinction explicit vs inferred provenance.

Запрещена fake precise probability вроде «82%». Также нет обязательного **opaque match score**, который скрывает, почему модель пришла к выводу.

Если candidate identity/fingerprint или пользовательского evidence мало, правильный результат — lower confidence, а не выдуманная точность.

## Couple reasoning

`couple` — отдельный group target. Совместный recommendation reasoning учитывает сигналы обоих участников и explicit group data, но не превращает разные вкусы в молчаливое среднее.

Полезные состояния:

- agreement — оба сигнала поддерживают candidate;
- disagreement — один сигнал поддерживает, другой создаёт риск;
- sparse evidence — для одного участника данных недостаточно.

Explanation должно показывать конфликт, если он влияет на выбор.

## Reanalysis

Запрос переанализа вкуса строит новый context из текущего raw/explicit evidence и заменяет inferred hypotheses через typed operation. Reanalysis не должен считать старые inferred hypotheses независимыми подтверждениями.

Similarity может быть дополнительным мостом между evidence works, но не заменяет ratings/reactions/feedback как independent user signal.

## Explainability rules

Хорошее объяснение рекомендации или assessment:

- называет конкретные works/traits;
- различает explicit user knowledge и inferred conclusions;
- показывает risks, а не только supports;
- учитывает текущий request context отдельно от stable taste;
- не изображает derived inference как факт, сообщённый пользователем.
