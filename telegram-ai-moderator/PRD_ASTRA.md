# PRD / ТЗ для Astra
## Telegram AI Moderator + Browser Inspector Mode

**Проект:** Telegram AI Moderator  
**Репозиторий:** `Joker5000/Joker5000.github.io`  
**Рабочая ветка:** `telegram-ai-moderator`  
**Корневая папка:** `telegram-ai-moderator/`  
**Приоритет:** высокий  
**Язык продукта:** русский  
**Целевая среда:** Linux VM для backend + обычный браузер для админов + Telegram Bot API  
**Основная идея:** полноценный AI-модератор Telegram-группы с обычной админ-панелью и отдельным игровым режимом рассмотрения нарушений, визуально и по механике максимально близким к интерфейсу проверки документов из Papers, Please, но адаптированным под Telegram.

---

# 1. Главная цель

Создать законченную систему модерации Telegram-группы, которая:

1. читает сообщения и события группы;
2. применяет детерминированные правила и AI-анализ;
3. выявляет спам, рекламу, скам, угрозы, флуд, рейды, повторные нарушения и потенциальный ban evasion;
4. не принимает необратимые решения без заданной политики подтверждения;
5. уведомляет владельца и второго администратора;
6. формирует полноценное досье пользователя;
7. позволяет рассматривать дело:
   - быстро, кнопками внутри Telegram;
   - через обычную веб-панель;
   - через игровой Browser Inspector Mode;
8. выполняет реальное действие в Telegram после решения администратора;
9. ведёт полный журнал действий;
10. остаётся удобным для установки на обычную VM одной командой.

---

# 2. Важный продуктовый принцип

В системе должны быть два полностью разделённых AI-контура.

## 2.1. Moderation AI

Отвечает только за анализ нарушений.

Он:
- читает правила;
- анализирует сообщение;
- учитывает контекст;
- создаёт incident;
- присваивает category;
- выдаёт factual reason;
- указывает confidence;
- не использует характер персонажа;
- не шутит;
- не принимает решение о личности пользователя;
- не должен повышать наказание из-за манеры общения.

## 2.2. Character / Social AI

Отвечает только за образ бота.

Он может:
- иногда отвечать в чате;
- реагировать emoji;
- иметь имя;
- иметь характер;
- менять описание/стиль речи;
- поддерживать образ живого AI-модератора.

Character AI **никогда не должен влиять на severity / punishment / confidence Moderation AI**.

---

# 3. Текущий код и существующая основа

Перед изменениями Astra обязана сначала проаудировать существующий код.

Уже существуют или частично существуют:

- `app/main.py`
- `app/db.py`
- `app/moderation.py`
- `app/personality.py`
- `app/command_worker.py`
- `app/web.py`
- `app/keyboards.py`
- `docker-compose.yml`
- `install.sh`
- PostgreSQL
- Redis
- русская Telegram admin panel
- web admin panel
- Character Studio
- incidents
- warnings
- admin allowlist
- moderation command queue
- Browser Inspector prototypes
- `browser-port/`
- экспериментальный `papers-game-bridge/`

Нельзя без необходимости переписывать проект с нуля.

Сначала:
1. понять что уже работает;
2. составить карту файлов;
3. отметить broken / incomplete parts;
4. сохранить совместимость с installer/update flow;
5. только затем вносить изменения.

---

# 4. Роли пользователей

## 4.1. Owner

Единственный главный владелец.

Права:
- полный доступ;
- добавление/удаление других администраторов;
- настройка AI;
- настройка правил;
- управление автоматическими наказаниями;
- Character Studio;
- Browser Inspector;
- просмотр всех логов;
- экспорт/backup;
- emergency stop.

Owner задаётся через:

`OWNER_TELEGRAM_ID`

---

## 4.2. Admin

Добавляется Owner.

Может:
- рассматривать дела;
- warning;
- mute;
- ban, если разрешено политикой;
- пользоваться Inspector Mode;
- смотреть историю;
- смотреть правила.

Не должен иметь права удалить Owner.

---

## 4.3. Ordinary user

Не имеет доступа к:
- `/admin`;
- private admin callbacks;
- web GUI;
- case data;
- logs;
- AI configuration.

Нельзя считать скрытие кнопки системой безопасности.

Каждый endpoint, callback и command должен **серверно проверять admin ID**.

---

# 5. Telegram bot

## 5.1. Язык

Весь пользовательский интерфейс бота — на русском.

Внутренние имена переменных/кода могут быть английскими.

---

## 5.2. Основные команды

Минимум:

- `/start`
- `/admin`
- `/myid`
- `/admins`
- `/addadmin <id>`
- `/deladmin <id>`
- `/webpass <password>`
- `/status`
- `/rules`
- `/cases`

---

## 5.3. Telegram admin case card

Когда Moderation AI создаёт дело, оба администратора должны получить карточку:

- номер дела;
- имя;
- @username;
- Telegram user ID;
- категория;
- confidence;
- причина;
- количество предыдущих warning;
- количество предыдущих incidents;
- дата вступления, если известна;
- кнопки.

Кнопки:

- 🟢 ПОМИЛОВАТЬ
- 🔴 ПРЕДУПРЕЖДЕНИЕ
- 🔇 МУТ
- ⛔ БАН
- 🎮 ОТКРЫТЬ ДЕЛО

Если case уже закрыт другим администратором, повторное действие запрещается.

---

# 6. AI moderation engine

## 6.1. Категории

Минимум:

- spam
- flood
- scam
- phishing
- ads
- harassment
- threat
- nsfw
- impersonation
- suspicious_links
- raid
- repeated_violation
- ban_evasion
- rule
- other

---

## 6.2. AI response schema

Все ответы анализатора должны валидироваться.

Пример:

```json
{
  "violation": true,
  "category": "ads",
  "score": 0.87,
  "reason": "Повторная публикация ссылки на сторонний Telegram-канал вопреки правилу #4.",
  "matched_rules": [4],
  "evidence_message_ids": [123, 124]
}
```

Если JSON malformed:
- не наказывать пользователя;
- записать ошибку;
- fallback в deterministic detector.

---

## 6.3. Message context

AI должен получать не только одно сообщение.

Нужен конфиг:

- последние N сообщений пользователя;
- последние N сообщений чата при необходимости;
- активные rules;
- warning history;
- prior incidents.

Нельзя передавать Character prompt в Moderation AI.

---

# 7. Rules system

Админ должен иметь возможность написать правило обычным русским языком.

Пример:

> За рекламу сторонних Telegram-каналов сначала удаляй сообщение и давай предупреждение. При повторе в течение недели мут на сутки. После третьего нарушения предложи бан.

Система должна преобразовать это в структурированную rule policy:

- title;
- description;
- category;
- priority;
- offense window;
- action 1;
- action 2;
- action 3;
- requires approval;
- enabled.

Админ должен увидеть preview перед применением.

---

# 8. Санкции

Уровни:

1. no action
2. notice
3. delete
4. warning
5. mute
6. ban request
7. ban

Рекомендуемый режим по умолчанию:

`ASSIST`

В ASSIST:
- очевидный spam может удаляться;
- warning может быть автоматическим, если правило явно разрешает;
- mute/ban требуют admin approval.

---

# 9. Atomic decisions

Критически важно.

Два администратора могут открыть одно дело одновременно.

Нужно:
- row lock;
- compare-and-set;
- command status;
- incident status;
- idempotency.

Пример states:

- OPEN
- PROCESSING
- WARNED
- MUTED
- BANNED
- PARDONED
- FAILED

После первого успешного решения остальные клиенты должны увидеть:

> Дело уже рассмотрено.

---

# 10. User dossier

Система должна вести профиль пользователя.

Поля:

- telegram_id;
- username;
- display_name;
- current profile photo file_id;
- first_seen_at;
- joined_at, если событие было реально поймано ботом;
- last_seen_at;
- message_count_seen_by_bot;
- warnings;
- mutes;
- bans;
- incident_count;
- last incidents;
- risk signals;
- invite source, если доступно.

---

# 11. Ограничения Telegram API

Нельзя выдумывать данные.

Не показывать как факт:

- IP;
- device ID;
- IMEI;
- SIM;
- телефон;
- точную дату создания Telegram-аккаунта;
- настоящий hardware fingerprint.

Поле "Дата создания аккаунта" **не показывать как реальную дату**, если Telegram API не дал её.

Вместо этого:

- "Впервые замечен ботом";
- "Вступил в чат", если зафиксировано;
- "Сообщений учтено ботом".

---

# 12. Anti-alt / ban evasion

Это вероятностный модуль.

Сигналы:

- similarity username;
- similarity display name;
- avatar pHash;
- linguistic similarity;
- repeated phrases;
- same links/domains;
- immediate join after ban;
- same invite source;
- similar posting patterns;
- interaction graph;
- repeated self-identifying info.

Результат:

> Возможный ban evasion, confidence 0–1.

Нельзя утверждать "это точно тот же человек".

---

# 13. Social AI / Character Studio

В GUI:

- имя;
- описание;
- style preset;
- custom persona;
- emoji set;
- reply chance;
- reaction chance;
- cooldown;
- enabled/disabled;
- allowed chats;
- quiet hours.

Presets:

- Friendly
- Serious
- Ironic
- Anime helper
- Custom

---

# 14. Browser Inspector Mode — основная игровая фича

## 14.1. Цель

Создать standalone браузерную сцену, которую можно открыть без самой Papers, Please.

Она должна работать как полноценный интерфейс рассмотрения реальных Telegram incidents.

Визуальный референс:
- пользовательский screenshot Papers, Please;
- `LittleBigBug/papers`;
- `https://anban-live.vercel.app/`.

Astra должна сама открыть и изучить доступные референсы, если окружение позволяет.

---

# 15. Inspector Mode — композиция

Целевая игровая сцена:

**фиксированная базовая canvas / viewport: 1600×900**

С масштабированием whole-scene через CSS transform.

Не строить responsive layout путём перерасположения элементов.

На маленьком экране:
- сохранять композицию;
- просто масштабировать сцену.

---

# 16. Верхняя часть сцены

Должны быть:

- checkpoint yard;
- очередь;
- полосы движения;
- barrier;
- guard silhouettes;
- booth;
- visitor window;
- current user/NPC;
- speech bubble.

NPC должен представлять пользователя текущего incident.

Если есть Telegram photo:
- использовать её как основу портрета;
- стилизовать под pixel/monochrome presentation;
- не изменять смысл изображения.

---

# 17. Desk

На столе:

- рабочая поверхность;
- левое окно посетителя;
- speaker/microphone;
- tray;
- date/calendar;
- weight-like UI decoration;
- документы;
- stamp mechanism;
- return documents slot.

---

# 18. Документ 1 — Telegram passport

Должен быть draggable.

Поля:

- Telegram photo;
- display_name;
- @username;
- user ID;
- first_seen_at;
- joined_at;
- messages seen;
- warning count;
- mute count;
- previous cases;
- current status.

Внизу можно использовать MRZ-like декоративную строку.

---

# 19. Документ 2 — Message history sheet

Отдельный draggable paper.

Должен отображать:

- timestamp;
- message;
- flagged messages;
- pagination;
- scroll;
- highlight evidence.

AI evidence messages должны визуально выделяться.

---

# 20. Документ 3 — AI notebook

Жёлтый блокнот.

Поля:

- case ID;
- category;
- confidence;
- complaint labels;
- matched rules;
- prior warnings;
- previous cases;
- concise factual reason;
- recommendation to admin.

Он должен выглядеть как официальный служебный документ, а не современная dashboard card.

---

# 21. Stamp drawer

Критический acceptance requirement.

Штампы **не должны постоянно лежать на экране как обычные кнопки**.

Требуется настоящий drawer interaction:

1. housing закрыт;
2. admin нажимает/тянет механизм;
3. drawer физически выдвигается;
4. становятся видны stamp heads;
5. passport надо переместить в stamping zone;
6. действие недоступно вне stamping zone;
7. stamp head физически опускается;
8. воспроизводится stamp animation;
9. на passport появляется imprint;
10. drawer задвигается;
11. incident переходит в processing;
12. backend выполняет реальное Telegram action;
13. после успеха passport можно вернуть.

Штампы:

- APPROVED → PARDON
- DENIED → WARNING

Отдельно:

- MUTE
- BAN

BAN должен иметь дополнительное подтверждение.

---

# 22. Return document flow

После решения:

1. stamp imprint остаётся;
2. return slot активируется;
3. admin возвращает документы;
4. papers анимированно уходят;
5. NPC уходит;
6. следующий incident загружается;
7. новое дело начинается без reload всей страницы, если возможно.

---

# 23. Browser state machine

Не делать интерфейс набором несвязанных DOM callbacks.

Создать state machine.

Пример:

- BOOT
- LOADING_CASE
- ARRIVAL
- DOCUMENTS_ISSUED
- INSPECTION
- STAMP_DRAWER_OPEN
- DECIDED
- ACTION_PROCESSING
- ACTION_SUCCESS
- ACTION_FAILED
- RETURN_DOCUMENTS
- EXIT
- NEXT_CASE

Каждый state должен иметь допустимые transitions.

---

# 24. Browser → backend API

Нужны endpoints:

## GET /api/game/next

Возвращает следующий OPEN incident.

## GET /api/game/case/{id}

Полное досье.

## POST /api/game/case/{id}/decision

Payload:

```json
{
  "action": "allow|warn|mute|ban"
}
```

Ответ:

```json
{
  "ok": true,
  "case_status": "processing"
}
```

Browser не должен считать действие успешным, пока backend не подтвердил его.

---

# 25. Реальные Telegram actions

Backend bot worker выполняет:

- allow → no Telegram punishment;
- warning → DB warning + optional public notice;
- mute → `restrict_chat_member`;
- ban → `ban_chat_member`.

При Telegram error:

- command FAILED;
- incident возвращается в OPEN или ERROR;
- GUI показывает ошибку;
- нельзя рисовать успешный stamp как финально выполненный, если action реально провалился.

---

# 26. Web admin panel

Обычная web panel остаётся.

Разделы:

- Dashboard
- Cases
- Users
- Rules
- Admins
- AI
- Character Studio
- Inspector Mode
- Logs
- Settings
- System status

---

# 27. Security

Обязательно:

- passwords hashed PBKDF2/Argon2/bcrypt;
- session secret;
- CSRF protection;
- admin allowlist;
- brute-force login rate limit;
- HTTPS для публичной панели;
- PostgreSQL/Redis без public port;
- secrets только в `.env`;
- chmod 600;
- no secrets in GitHub;
- audit log;
- command idempotency;
- prompt-injection separation;
- validate AI JSON.

---

# 28. Privacy / retention

Настройки:

- сколько дней хранить raw message history;
- сколько хранить incident evidence;
- max messages per user dossier;
- export/delete tools для owner.

По умолчанию не хранить больше данных, чем требуется модерации.

---

# 29. VM deployment

Цель:

Ubuntu 22.04 / 24.04.

One-command installer:

```bash
curl -fsSL <RAW_INSTALL_URL> | sudo bash
```

Installer должен:

- проверить OS;
- установить Docker;
- установить Compose;
- создать app dir;
- сгенерировать PostgreSQL password;
- session secret;
- game bridge token;
- запросить Bot Token;
- запросить Owner Telegram ID;
- создать `.env`;
- chmod 600;
- build;
- start;
- показать next steps.

---

# 30. CLI

Команда:

`moderator`

Подкоманды:

- status
- logs
- start
- stop
- restart
- update
- config
- backup
- restore
- doctor
- uninstall

---

# 31. Backups

Нужны:

- PostgreSQL dump;
- retention;
- manual backup;
- restore;
- restore confirmation;
- backup integrity check.

---

# 32. Наблюдаемость

Добавить:

- structured logs;
- health endpoint;
- DB status;
- Redis status;
- Telegram connectivity;
- AI provider status;
- worker queue depth;
- failed command count.

---

# 33. Performance

Не отправлять каждый message в LLM без необходимости.

Pipeline:

1. deterministic filters;
2. cached user state;
3. cheap spam/flood/link detection;
4. AI only if needed.

---

# 34. Необходимые deterministic modules

Минимум:

- flood detector;
- repeated-message detector;
- mass-link detector;
- mention spam;
- raid/join-rate detector;
- suspicious-domain detector;
- repeat offender;
- simple regex rules.

---

# 35. Independent verifier agents

Astra должна использовать независимые проверяющие контуры.

Не считать задачу законченной только потому, что основной агент написал код.

## 35.1. Security verifier

Проверяет:

- auth bypass;
- IDOR;
- CSRF;
- leaked secrets;
- unprotected endpoints;
- race conditions;
- callback forgery;
- SQL injection;
- command replay.

## 35.2. Telegram verifier

Проверяет реальные flows:

- warning;
- mute;
- ban;
- allow;
- missing permissions;
- user left chat;
- user already banned;
- second admin race.

## 35.3. UI visual verifier

Для Inspector Mode:

- screenshots at 1600×900;
- compare against reference composition;
- stamp drawer position;
- passport position;
- AI notebook position;
- messages paper position;
- NPC window;
- no overlapping documents at initial state;
- pixel snapping;
- no antialiasing where avoidable.

## 35.4. Interaction verifier

Автоматически проверяет:

- drag passport;
- stamp outside zone denied;
- drag to zone;
- open drawer;
- stamp;
- imprint appears;
- return documents;
- next case.

## 35.5. Regression verifier

Проверяет:

- `moderator update`;
- fresh install;
- DB migration;
- old DB upgrade;
- web panel login;
- Telegram panel.

---

# 36. Visual QA process

Каждая значимая версия Inspector должна иметь реальные browser screenshots.

Не использовать AI-generated mockup как доказательство готовности.

Для каждой итерации:

1. запустить приложение;
2. открыть case;
3. снять screenshot:
   - initial scene;
   - documents issued;
   - stamp drawer closed;
   - stamp drawer open;
   - passport under stamp;
   - stamped passport;
4. сравнить;
5. исправить.

---

# 37. Запрещено считать выполнением

Нельзя писать "готово", если:

- код не запускался;
- UI не открывался;
- screenshot не снят;
- action не проверен;
- DB migration не проверена;
- browser console содержит errors;
- Telegram worker не подтверждает action.

---

# 38. UX: два режима рассмотрения

## Fast mode

Telegram card / обычная GUI карточка.

Для быстрых решений.

## Game mode

Полный Inspector.

Для атмосферного рассмотрения.

Оба используют одно incident state и одну command queue.

---

# 39. Audio

Опционально, но желательно:

- drawer slide;
- paper pickup;
- paper drop;
- stamp hit;
- warning buzzer;
- case completed.

Audio toggle обязателен.

Не использовать сторонние copyrighted audio assets без явного разрешения.

---

# 40. Visual assets / reference handling

Цель пользователя — максимально близкое ощущение Papers, Please.

Astra должна:
- сохранять композицию;
- сохранять масштаб;
- воспроизводить механику;
- воспроизводить характер анимаций;
- использовать pixel-art presentation.

Если конкретный asset разрешён пользователем и его лицензия допускает reuse — можно использовать.

Если лицензия не подтверждена:
- не копировать asset в репозиторий;
- сделать функционально эквивалентный собственный pixel asset.

---

# 41. LittleBigBug/papers

Reference:

`https://github.com/LittleBigBug/papers`

Полезные architectural точки:

- traveller selection;
- traveller name replacement;
- booth engine;
- stamp handling;
- processing finish;
- detain;
- shot;
- paper injection.

Не переносить Unity/BepInEx dependency в финальный browser mode.

Итоговая версия должна работать без установленной Papers, Please.

---

# 42. anban-live

Reference:

`https://anban-live.vercel.app/`

Astra должна изучить:
- layout;
- document positioning;
- animations;
- drawer interaction;
- scaling method;
- whether public source repository exists.

Если source найден:
- проверить license;
- только после этого решать, что можно переиспользовать.

---

# 43. Browser technical approach

Предпочтительно:

- HTML
- CSS
- JS/TypeScript

Допустимо:
- Canvas
- PixiJS
- Phaser

Если обычный DOM мешает pixel-perfect animation, Astra может мигрировать Inspector Mode на Canvas/PixiJS.

Web admin panel при этом остаётся обычным HTML/FastAPI.

---

# 44. Рекомендуемая архитектура frontend

```text
browser-port/
├── index.html
├── src/
│   ├── game.ts
│   ├── state-machine.ts
│   ├── api.ts
│   ├── scene/
│   │   ├── checkpoint.ts
│   │   ├── desk.ts
│   │   ├── traveler.ts
│   │   └── stamps.ts
│   ├── documents/
│   │   ├── passport.ts
│   │   ├── messages.ts
│   │   └── ai-report.ts
│   └── audio/
├── assets/
└── tests/
```

---

# 45. Data model

Core tables:

- admins
- users/user_profiles
- message_log
- rules
- warnings
- punishments
- incidents
- incident_evidence
- moderation_commands
- admin_actions
- app_settings
- audit_log
- alt_candidates

---

# 46. Incident snapshot

После создания incident сохранить snapshot данных, чтобы дело не менялось задним числом из-за новых сообщений.

Snapshot:

- trigger message;
- evidence message IDs;
- username at time;
- display name;
- photo file id;
- AI result;
- matched rules;
- warning count;
- timestamps.

---

# 47. Admin audit

Каждое решение:

- case id;
- admin id;
- action;
- source:
  - telegram
  - web
  - inspector;
- timestamp;
- action result;
- Telegram API result;
- error if failed.

---

# 48. Acceptance criteria — MVP

MVP считается готовым, если:

1. VM устанавливается одной командой.
2. Бот подключается к Telegram.
3. Owner открывает /admin.
4. Ordinary user не получает доступ.
5. Второй admin добавляется owner.
6. Сообщения логируются.
7. Rule можно создать.
8. AI создаёт incident.
9. Два admin получают card.
10. Case открывается в web.
11. Inspector Mode получает те же данные.
12. Passport показывает Telegram photo.
13. Messages sheet показывает историю.
14. AI notebook показывает complaint.
15. Stamp drawer выдвигается.
16. Passport надо поставить в stamp zone.
17. Stamp animation работает.
18. Backend выполняет warning.
19. Backend выполняет mute.
20. Backend выполняет ban.
21. Concurrent second admin action rejected.
22. Failed Telegram action отражается как failed.
23. Документы возвращаются.
24. Следующий case открывается.
25. Реальные screenshots приложены к QA report.

---

# 49. Acceptance criteria — визуальный Inspector

Визуальная проверка:

- сцена выглядит как единая игра, а не dashboard;
- элементы выровнены по pixel grid;
- документы имеют разные paper materials;
- passport визуально читается;
- Telegram photo интегрирована естественно;
- AI notebook жёлто-зелёный;
- message history отдельным листом;
- stamp mechanism является физическим объектом;
- drawer действительно движется;
- stamp heads имеют механическую анимацию;
- passport imprint остаётся после stamp;
- return flow анимирован;
- нет современных rounded-card элементов внутри game viewport.

---

# 50. Порядок реализации для Astra

## Phase 0 — Audit
- прочитать весь проект;
- поднять локально;
- проверить installer;
- составить issues.

## Phase 1 — Backend correctness
- migrations;
- incidents;
- command queue;
- audit;
- Telegram actions;
- auth.

## Phase 2 — Moderation engine
- deterministic modules;
- AI context;
- rules;
- schema validation.

## Phase 3 — User dossier
- profile;
- history;
- photo;
- stats;
- snapshot.

## Phase 4 — Standard admin GUI
- cases;
- users;
- rules;
- settings;
- logs.

## Phase 5 — Browser Inspector
- state machine;
- scene;
- documents;
- stamps;
- return flow.

## Phase 6 — Pixel visual QA
- screenshots;
- compare;
- iterate.

## Phase 7 — Anti-alt / raids
- risk scoring;
- explainable signals.

## Phase 8 — Social AI
- character;
- reactions;
- cooldown;
- Character Studio.

## Phase 9 — hardening
- security audit;
- tests;
- backup/restore;
- docs.

---

# 51. Astra execution rules

Astra должна работать как самостоятельный lead engineer.

Требуется:

- не ограничиваться прототипами;
- не оставлять fake buttons;
- не подменять реальные integration tests моками в финальной проверке;
- не переписывать рабочие части без причины;
- делать маленькие проверяемые commits;
- сохранять backward compatibility;
- запускать проект после изменений;
- исправлять console/runtime errors;
- вести TODO только для реально отложенных задач;
- использовать доступные инструменты, интернет-референсы и независимые проверяющие контуры;
- документировать найденные ограничения Telegram API;
- не заявлять о готовности, пока acceptance criteria не проверены.

---

# 52. Финальный результат

Пользователь должен получить систему, где AI пишет админу:

> Обнаружено потенциальное нарушение. Дело #428.

Админ может:

### Быстро
нажать кнопку в Telegram.

### Обычным способом
открыть case в dashboard.

### В игровом режиме
открыть Inspector Mode, увидеть Telegram-пользователя в окне, получить его паспорт, лист сообщений и AI-блокнот, вручную изучить дело, выдвинуть механизм штампов, положить паспорт под stamp, принять решение и вернуть документы.

После этого выбранное действие **реально выполняется в Telegram**, логируется и синхронно закрывает дело у второго администратора.

Это и есть целевой продукт.
