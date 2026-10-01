# Media Web Experience — design

Дата: 2026-10-01  
Статус: **design approved in chat; written spec awaiting final user review**

## 1. Цель

Добавить к существующей персональной медиатеке кинематографичный веб-интерфейс на GitHub Pages.

Сайт нужен прежде всего для внутреннего использования владельцем репозитория и партнёром. Его главная задача — сделать уже накопленные данные визуальными и быстрыми в использовании: выбрать фильм на вечер, просмотреть личную медиатеку, увидеть собственные оценки и реакции, открыть подробную карточку произведения и понять, почему оно находится в фокусе.

Основной способ пополнения богатых данных остаётся прежним: разговор с LLM и существующий typed-command/write pipeline. Веб-интерфейс не создаёт второй источник истины.

Публичная достижимость сайта не считается проблемой: пользователь подтвердил, что возможная видимость его кинооценок, реакций и комментариев для посторонних приемлема. Поэтому v1 не вводит encryption/passphrase слой только ради сокрытия медиатеки.

## 2. Продуктовый контракт

1. Git/YAML остаётся canonical source of truth.
2. Frontend v1 полностью read-only относительно canonical data.
3. React-компоненты не читают и не редактируют YAML напрямую.
4. В production-компонентах нет встроенных mock-массивов фильмов.
5. Web build получает отдельный JSON manifest, построенный из существующей медиатеки штатным Python/domain-слоем.
6. Все обычные видимые тексты интерфейса — на русском языке; обязательные provider/legal notices могут сохранять требуемую источником формулировку.
7. Личный сигнал (`viewer_signals`, `group_signals`, explicit interest/preferences) визуально важнее публичных рейтингов.
8. Сайт не вводит новый скрытый recommendation score и не подменяет LLM как основной recommendation engine.
9. Будущие быстрые правки с сайта используют тот же typed-command / validation / receipt протокол, что LLM и CLI.
10. GitHub token, write credentials и provider secrets никогда не попадают в browser bundle.
11. Ratings, reactions, feedback и прочие данные медиатеки могут публиковаться в статическом read manifest без дополнительного encryption слоя.
12. Отсутствие требования конфиденциальности не ослабляет secret boundary: credentials, Actions secrets, provider tokens и будущая write-broker authentication остаются непубличными.

## 3. Область v1

### Входит

- React + Vite + TypeScript приложение в `web/`;
- Motion (`motion/react`) для переходов и интерактивности;
- статическая сборка и публикация через GitHub Pages;
- build-time exporter из canonical/derived media data в web manifest;
- главная страница как «вечерний программный гид»;
- медиатека с поиском и фильтрами;
- detail page фильма;
- переключение контекста просмотра (`Я`, `Партнёр`, `Вместе`) там, где соответствующие данные существуют;
- постеры/backdrops через уже сохранённые TMDB asset references;
- loading, empty и error состояния;
- responsive desktop/mobile;
- accessibility и reduced motion;
- русская локализация интерфейса.

### Не входит в v1

- browser-side редактирование canonical YAML;
- GitHub OAuth/token в браузере;
- passphrase/unlock/encryption слой для медиатеки;
- новый recommendation ML/ranking engine;
- серверная база данных;
- публичные аккаунты и многопользовательская авторизация;
- административный интерфейс;
- schema/vocabulary editing из сайта.

## 4. Будущий write-flow

Быстрые правки (`оценка`, `статус просмотра`, `reaction`, `interest`) являются фазой 2, но v1 должен оставить для них чистую архитектурную точку расширения.

Предпочтительный путь:

```text
React UI
  -> authenticated write broker
  -> typed media command
  -> existing validation / resolver / transaction service
  -> Git operation / canonical write
  -> generated rebuild
  -> refreshed Pages data
```

Write broker не имеет права принимать произвольный YAML, patch, filename или shell command. Он принимает только ограниченный typed payload существующей media domain-модели.

UI v1 поэтому строится так, чтобы блоки пользовательских сигналов могли позже получить edit affordance без изменения read-модели страницы.

Публичность read-сайта не означает публичность write-flow: будущий broker обязан иметь отдельную authentication/authorization boundary.

## 5. Архитектура данных для сайта

### 5.1 Web manifest

Добавляется штатный exporter в Python media-layer. Он читает canonical/derived данные через существующие parser/service boundaries и выпускает статическое JSON-представление для web build.

Логическая форма:

```text
build-time generated data
  manifest.json
  works/<id>.json   # допускается только если измеренный размер потребует chunking
```

Файлы web manifest являются build artifacts: они не становятся новым canonical storage и не коммитятся как ручные данные.

Manifest содержит только уже существующие факты:

- identity;
- poster/backdrop provider refs;
- runtime, genres, synopsis, people metadata;
- viewer/group signals;
- explicit interest;
- безопасные derived profile hints, если они уже существуют;
- ссылки между сущностями, необходимые UI.

Exporter не создаёт субъективных фактов и не заполняет пропуски догадками.

### 5.2 Recommendation semantics

v1 не создаёт opaque score.

Главный экран использует объяснимые источники:

- explicit interest/priority;
- unwatched state;
- существующие viewer/group preferences и generated profile evidence;
- текущие canonical metadata для фильтрации/контекста;
- deterministic fallback, если персонального сигнала недостаточно.

Если для полноценного «почему рекомендуем» требуется LLM-интерпретация, сайт показывает только те объяснения, которые можно вывести из сохранённых/derived фактов без генерации новых утверждений.

LLM остаётся каналом для более сложного запроса «подбери нам фильм сегодня».

### 5.3 Publication posture

Сайт рассчитан на внутреннее использование, но не требует privacy wall для данных медиатеки.

Разрешено публиковать в Pages artifact:

- названия и metadata фильмов;
- оценки;
- reactions;
- feedback summaries/signals;
- viewing status/history, если они уже входят в утверждённый manifest contract;
- viewer/group IDs, поскольку текущая модель использует анонимные стабильные IDs и не хранит имена/PII.

Запрещено публиковать:

- GitHub access tokens;
- Actions secrets;
- TMDB/API credentials;
- будущие write-broker credentials/session secrets;
- любые новые персональные данные, которых нет в canonical media model и которые не нужны UI.

Это сознательная продуктовая позиция, а не предположение о приватности GitHub Pages.

## 6. Frontend boundary

Предлагаемая структура:

```text
web/
  src/
    app/
    components/
    features/
      home/
      library/
      work-detail/
    data/
      client.ts
      types.ts
    motion/
    styles/
  index.html
  package.json
  vite.config.ts
```

Компоненты получают типизированные view models. Они не знают о YAML-схемах, GitHub API, Actions или canonical filenames.

Data adapter — единственная frontend-точка, знающая manifest contract.

## 7. Информационная архитектура

### 7.1 Главная

Главная — не dashboard и не таблица. Это «вечерний программный гид».

Первый viewport:

- один главный фильм;
- backdrop как основной визуальный материал;
- крупное русское название;
- год + хронометраж + несколько релевантных жанров;
- короткое объяснимое основание «почему сейчас»;
- действие `Подробнее`;
- 2–3 альтернативы второго уровня, не конкурирующие визуально с hero.

Дальше страница меняет ритм:

1. `Посмотреть следующим` — poster rail для релевантных unwatched/high-interest работ;
2. `Для двоих` — контекст couple, только если данных достаточно;
3. `Недавно в медиатеке` / `Недавно посмотрели` — выбирается по реально доступным датам и history, без фиктивной chronology;
4. `Вся медиатека` — переход в searchable library.

Пустой раздел не заполняется фейковым контентом: он скрывается либо получает честное empty state.

### 7.2 Медиатека

- полнотекстовый поиск по названиям;
- фильтры по viewing state, viewer context, жанрам и году;
- переключение «все / непросмотренные / просмотренные»;
- poster-first grid;
- никакой плоской data-table presentation;
- URL/search params сохраняют фильтры там, где это полезно.

### 7.3 Страница фильма

Приоритет информации:

1. backdrop/poster и identity;
2. персональные сигналы;
3. synopsis и canonical metadata;
4. люди/создатели;
5. внешний рейтинг как вторичный справочный сигнал.

`Ваше впечатление` / `Впечатление партнёра` / `Вместе` показываются раздельно и только при наличии соответствующих данных.

Будущий edit-flow встраивается именно сюда как локальная правка сигнала, а не как отдельная admin-страница.

## 8. Визуальное направление

### Design Read

Внутренний персональный киноинтерфейс для двух зрителей: editorial/cinematic experience с быстрым выбором, а не публичный каталог и не dashboard.

### Taste parameters

- `DESIGN_VARIANCE = 7`
- `MOTION_INTENSITY = 8`
- `VISUAL_DENSITY = 4`

### Visual thesis

**«Вечерний программный гид + личный киножурнал».**

Опорные качества MUBI/Netflix используются как уровень арт-дирекции и скорость выбора, но их интерфейс не копируется.

Композиция асимметричная: один сильный фильм доминирует в первом viewport, дальше poster rails и editorial blocks меняют масштаб и плотность.

### Цвет

- почти чёрный угольный base;
- холодный графит для вторичных поверхностей;
- молочно-белый основной текст;
- один тёплый tungsten/accent, напоминающий свет кинопроектора;
- цвет самих постеров/backdrops остаётся главным источником хроматического разнообразия;
- generic blue/purple AI gradients запрещены.

### Material

- очень лёгкое плёночное зерно;
- градиентные scrims используются только для читаемости текста поверх imagery;
- glass эффект допускается точечно для floating navigation/overlay, но не как универсальный card style;
- generic серые рамки и тяжёлые чёрные shadows не используются;
- карточки не обязаны иметь одинаковую оболочку: visual role определяется контентом.

## 9. Типографика

- premium Cyrillic-capable sans/grotesk family;
- крупные display-заголовки, плотный tracking;
- metadata остаётся спокойной и хорошо читаемой;
- Inter, Roboto, Arial, Open Sans и Helvetica не используются как выбранная brand typography;
- случайное смешивание serif/sans ради «премиальности» запрещено;
- маленькие uppercase eyebrow-labels используются редко, не над каждым разделом.

Конкретная гарнитура выбирается в `typeset` этапе после визуального comp, с обязательной проверкой кириллицы и production-доступности.

## 10. Motion

Motion — часть кинематографичного ощущения, но не источник информации.

Основная грамматика:

- hero change: controlled crossfade + spatial slide;
- poster rail: мягкая инерционная реакция и snap-поведение без scroll hijacking;
- hover/focus карточки: небольшой scale/translation и раскрытие secondary metadata;
- detail transition: shared-layout/continuity там, где это не ломает Pages routing;
- section reveal: ограниченный stagger/fade-up;
- никакой бесконечной декоративной анимации;
- transform/opacity only для частых transitions;
- `prefers-reduced-motion` убирает spatial motion и сохраняет всю функциональность.

## 11. Responsive

Desktop ориентир: 1440 px.

Mobile ориентир: 390 px.

На mobile:

- hero превращается в вертикальную киноафишу;
- backdrop остаётся главным визуальным слоем;
- отдельный большой poster скрывается или уменьшается, если создаёт дублирование;
- rails остаются touch-scroll;
- library становится двухколоночной poster grid, при очень узких размерах — одной колонкой;
- tap targets не меньше доступного touch baseline;
- desktop overlap/rotation не переносится на mobile автоматически.

## 12. Навигация

Минимальная v1-навигация:

- `Сегодня`
- `Медиатека`
- viewer context switch (`Я`, `Партнёр`, `Вместе`) — только если он реально влияет на представленную информацию.

Nav компактная, floating, не занимает большой процент viewport.

Не добавляем разделы ради полноты.

## 13. Изображения и TMDB attribution

Canonical Git хранит TMDB provider paths, а не binary assets.

Web layer строит image URLs из provider refs через централизованный asset helper. Компоненты не конструируют provider URL каждый самостоятельно.

Fallback-порядок:

1. backdrop/poster provider ref;
2. альтернативный доступный asset того же work;
3. специально оформленный placeholder без выдуманного изображения.

Никаких случайных stock movie posters или synthetic replacements для реально существующих фильмов.

Поскольку приложение использует TMDB data/images, v1 содержит раздел `О проекте` / credits с approved TMDB logo и обязательным notice:

> This product uses the TMDB API but is not endorsed or certified by TMDB.

Это единственное намеренное исключение из правила «весь интерфейс на русском»: сама навигация и пояснение вокруг attribution остаются русскими, обязательная provider-формулировка сохраняется без перевода.

TMDB attribution не должен визуально конкурировать с собственным продуктом.

## 14. GitHub Pages delivery

Добавляется отдельный Pages workflow, независимый от normal media write workflow.

Высокоуровневый pipeline:

```text
checkout main
-> setup Python
-> install media requirements
-> validate canonical data
-> build/rebuild generated data check
-> export web manifest
-> setup Node
-> install locked frontend dependencies
-> test/typecheck/build web
-> publish dist to GitHub Pages
```

Manifest может входить в опубликованный Pages artifact как обычный статический JSON/read payload.

Изменение media data после merge автоматически приводит к новой Pages build, чтобы сайт показывал актуальный `main`.

Pages workflow не получает TMDB read/enrichment secret: enrichment уже происходит в media workflow, сайт использует сохранённые provider refs.

Pages workflow не получает GitHub write token сверх минимально необходимого стандартному deploy mechanism и не используется для media mutation.

## 15. Routing на GitHub Pages

v1 использует **hash routing**.

Причины:

- надёжный refresh/deep link на GitHub Pages без custom 404 routing;
- минимальная инфраструктура;
- не требует серверного rewrite layer;
- совместим с repository subpath.

Vite должен работать под project-site base path и не предполагать root `/`.

Если в будущем появится отдельный gateway/domain с rewrite support, переход на history routing будет отдельным решением.

## 16. Accessibility

Минимальный shipping gate:

- WCAG AA contrast для текста и интерактивных элементов;
- полностью usable keyboard navigation;
- видимый `:focus-visible`;
- semantic headings/landmarks;
- alt text / decorative treatment для imagery;
- no motion dependency;
- `prefers-reduced-motion`;
- hover state всегда имеет keyboard/focus equivalent;
- читабельность текста поверх backdrop проверяется на реальных изображениях, не только на design tokens.

## 17. Состояния

### Loading

Skeleton повторяет форму итогового poster/hero layout. Generic spinner как основной page state не используется.

### Empty

Русский, честный и контекстный текст. Например, если нет explicit interest, UI объясняет отсутствие раздела, а не изображает рекомендации.

### Error

Если manifest недоступен или повреждён, пользователь видит понятное локальное сообщение и возможность перезагрузить страницу. Ошибка не маскируется пустой медиатекой.

### Missing metadata

Неполные work records должны корректно отображаться. Отсутствующие runtime, synopsis, poster и т. п. не создают layout collapse.

## 18. Производительность

- статическая сборка;
- code splitting для detail/library по необходимости;
- изображения lazy-load вне первого viewport;
- hero image получает повышенный priority;
- Motion не подписывает React state на continuous scroll values;
- backdrop blur не используется на больших scrolling surfaces;
- производительность проверяется на mobile viewport;
- размер manifest измеряется до выбора single-file vs per-work split.

## 19. Тестирование

### Domain/export tests

- exporter использует реальные media parser/domain interfaces;
- manifest schema стабилен и валиден;
- viewer signals не теряются;
- canonical data не изменяется при export;
- missing optional metadata поддерживается;
- asset refs сериализуются корректно;
- exporter не сериализует credentials/secrets.

### Frontend tests

- data adapter/type contract;
- search/filter behavior;
- viewer context behavior;
- fallback states;
- no hard-coded production movie arrays;
- Russian UI strings для shipping surfaces, кроме обязательного TMDB notice.

### Build gates

- Python tests;
- canonical validator;
- rebuild check/doctor;
- frontend tests;
- TypeScript typecheck;
- production build;
- static artifact check на отсутствие credentials/secrets;
- accessibility audit;
- desktop/mobile screenshot review;
- Impeccable critique/audit/polish before merge.

## 20. Impeccable / Taste execution contract

Workflow default: **comp-first**.

После implementation plan визуальная реализация проходит в таком порядке:

1. `impeccable init` contract уже представлен `PRODUCT.md`;
2. direction/comp round для главной страницы;
3. `typeset`;
4. `colorize`;
5. React component build с `high-end-visual-design` и Taste dials `7 / 8 / 4`;
6. `animate`;
7. `critique` и один batch визуальных исправлений;
8. `audit` и исправление accessibility/DOM/performance проблем;
9. `polish`;
10. финальный screenshot review desktop + mobile;
11. `document` фиксирует реально построенный визуальный мир в `DESIGN.md` и `.impeccable/design.json`.

`DESIGN.md` намеренно создаётся после реализации, а не до неё: установленная версия Impeccable считает новый visual world фактом только после того, как он построен и прошёл finish review.

## 21. Критерии готовности v1

v1 считается готовой, когда:

- GitHub Pages публикует сайт из `main`;
- сайт строится только из repository-derived media data;
- canonical data остаётся untouched frontend-слоем;
- главный экран даёт быстрый персональный путь к выбору фильма;
- library и detail page работают на desktop/mobile;
- личные оценки/реакции визуально важнее внешнего рейтинга;
- интерфейс полностью на русском, кроме обязательного provider notice;
- отсутствуют production mock arrays;
- browser bundle/Pages artifact не содержат write credentials или provider secrets;
- keyboard/reduced-motion/contrast gates пройдены;
- TMDB attribution присутствует;
- Impeccable finish review завершён;
- `DESIGN.md` документирует фактическую визуальную систему;
- будущий write-broker можно добавить без изменения canonical read architecture.

## 22. Отложенные решения для implementation plan

Следующие детали не меняют утверждённую архитектуру и выбираются после измерения/прототипирования:

- single manifest vs manifest + per-work chunks;
- конкретная Cyrillic-capable font family;
- exact TMDB image size variants;
- минимальный набор deterministic home shelves при текущей плотности сигналов;
- форма будущей write-broker authentication.
