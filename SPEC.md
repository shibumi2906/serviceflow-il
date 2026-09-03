# ServiceFlow IL — техническая спецификация

## 1. Назначение документа

Этот документ является главным заданием для поэтапной разработки проекта с помощью Codex.

Codex обязан:

- реализовывать только явно указанную текущую фазу;
- не добавлять компоненты из следующих фаз «на будущее»;
- сохранять работоспособность уже завершённых фаз;
- завершать каждую фазу проверками, документацией и отдельным Git-коммитом;
- не выполнять действия в AWS без явного разрешения пользователя;
- перед любым действием, способным создать расходы, назвать создаваемый ресурс и возможный источник расходов;
- не считать фазу завершённой, пока не выполнены её критерии приёмки.

Если реализация расходится с этим документом, приоритет имеет этот документ. Существенные изменения архитектуры сначала оформляются как ADR и согласовываются с пользователем.

---

## 2. Обзор проекта

### 2.1. Название

**ServiceFlow IL**

### 2.2. Краткое описание

ServiceFlow IL — небольшое web-приложение для управления заявками сервисной компании. Клиент или оператор создаёт заявку, сотрудник принимает её в работу, меняет статус, добавляет комментарии и прикрепляет файлы. Система хранит полную историю действий.

Примеры потенциальных пользователей:

- ремонтные и монтажные компании;
- клининг;
- обслуживание зданий;
- управляющие компании;
- небольшие подрядчики;
- сервисные подразделения малого бизнеса.

### 2.3. Основная учебная цель

Последовательно освоить production-style развёртывание Python-backend в AWS, добавляя за одну фазу только одну новую область сложности.

### 2.4. Портфельная цель

Готовый проект должен подтверждать, что разработчик умеет:

- проектировать и реализовывать FastAPI-приложение;
- работать с PostgreSQL, миграциями и транзакциями;
- контейнеризировать приложение;
- разворачивать контейнер в Amazon ECS Fargate;
- настраивать ECR, VPC, ALB, security groups и RDS;
- безопасно передавать секреты;
- хранить файлы в S3;
- собирать логи и метрики в CloudWatch;
- описывать инфраструктуру кодом;
- строить CI/CD без постоянных AWS access keys;
- диагностировать проблемы по слоям;
- осознанно развивать синхронную систему в event-driven архитектуру.

### 2.5. Принцип проекта

Предметная область должна быть достаточно реалистичной для портфолио, но не должна заслонять AWS.

Проект не является AI-приложением. AI-анализ вложений может быть добавлен только после завершения основной AWS-части и не входит в обязательный объём.

---

## 3. Границы проекта

### 3.1. Обязательный результат основной версии

После завершения основной версии пользователь может:

1. войти в систему;
2. создать заявку;
3. просмотреть список и карточку заявки;
4. назначить ответственного;
5. изменить статус и приоритет;
6. добавить комментарий;
7. просмотреть историю изменений;
8. прикрепить файл к заявке;
9. скачать разрешённое вложение через безопасную временную ссылку;
10. использовать приложение, развёрнутое в AWS.

### 3.2. Что намеренно не входит в первую версию

- Kubernetes и Amazon EKS;
- микросервисная архитектура;
- Lambda, SQS, EventBridge и Step Functions до отдельной фазы расширения;
- DynamoDB;
- Redis;
- WebSocket и realtime-обновления;
- мобильное приложение;
- платежи и подписки;
- интеграции с WhatsApp, Telegram, email или CRM;
- сложный календарь и маршрутизация выездных сотрудников;
- полноценная multi-tenant SaaS-биллинг модель;
- генеративный AI как обязательная часть продукта;
- отдельный SPA/frontend-проект.

### 3.3. Допустимая модель использования

Первая версия обслуживает одну организацию. Архитектура доменной модели не должна мешать будущему добавлению `organization_id`, но преждевременно реализовывать multi-tenancy запрещено.

---

## 4. Пользователи и роли

### 4.1. Роли

#### Administrator

- создаёт и деактивирует сотрудников;
- видит все заявки;
- назначает ответственных;
- меняет любой статус и приоритет;
- видит журнал действий.

#### Dispatcher

- создаёт заявки;
- видит все заявки;
- назначает ответственных;
- меняет статус и приоритет;
- добавляет комментарии и вложения.

#### Technician

- видит назначенные ему заявки;
- меняет статус только в пределах разрешённого workflow;
- добавляет комментарии и вложения.

Внешний клиентский кабинет в первую версию не входит. Данные клиента вводит сотрудник.

### 4.2. Аутентификация

- локальная аутентификация по email и паролю;
- пароль хранится только в виде современного стойкого хеша;
- авторизация выполняется на сервере;
- browser-сессия хранится в защищённой cookie;
- cookie: `HttpOnly`, `SameSite=Lax`, `Secure` в production;
- защита изменяющих HTML-форм от CSRF обязательна;
- деактивированный пользователь не может войти или продолжить работу после истечения/отзыва сессии.

Amazon Cognito в основной объём не входит: он добавил бы отдельную область AWS-диагностики, не необходимую для цели проекта.

---

## 5. Функциональные требования

### 5.1. Пользователи

- первый administrator создаётся отдельной CLI-командой, а не публичной регистрацией;
- administrator может создавать сотрудника с ролью;
- email уникален без учёта регистра;
- пользователь может быть активным или деактивированным;
- удаление пользователя с историческими действиями запрещено.

### 5.2. Клиенты

Карточка клиента содержит:

- имя или название;
- телефон;
- email, если есть;
- адрес, если есть;
- свободную заметку;
- дату создания и изменения.

Телефон и email валидируются, но допускается отсутствие одного из них. Для заявки должен существовать клиент.

### 5.3. Заявки

Заявка содержит:

- неизменяемый UUID;
- короткий человекочитаемый номер;
- клиента;
- заголовок;
- описание;
- статус;
- приоритет;
- ответственного сотрудника или `null`;
- автора создания;
- дату создания;
- дату последнего изменения;
- дату завершения или `null`;
- версию записи для защиты от потерянных обновлений.

Приоритеты:

- `LOW`;
- `NORMAL`;
- `HIGH`;
- `URGENT`.

Статусы:

- `NEW`;
- `ASSIGNED`;
- `IN_PROGRESS`;
- `WAITING_CUSTOMER`;
- `COMPLETED`;
- `CANCELLED`.

### 5.4. Разрешённые переходы статусов

| Исходный статус | Разрешённые следующие статусы |
|---|---|
| `NEW` | `ASSIGNED`, `CANCELLED` |
| `ASSIGNED` | `IN_PROGRESS`, `NEW`, `CANCELLED` |
| `IN_PROGRESS` | `WAITING_CUSTOMER`, `COMPLETED`, `CANCELLED` |
| `WAITING_CUSTOMER` | `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| `COMPLETED` | `IN_PROGRESS` только для Administrator/Dispatcher |
| `CANCELLED` | `NEW` только для Administrator/Dispatcher |

Дополнительные правила:

- переход в `ASSIGNED` невозможен без ответственного;
- назначение ответственного для `NEW` может автоматически перевести заявку в `ASSIGNED`;
- `completed_at` устанавливается при переходе в `COMPLETED` и очищается при повторном открытии;
- запрещённый переход возвращает доменную ошибку, а не меняет данные частично.

### 5.5. Комментарии

- комментарий принадлежит одной заявке и одному автору;
- текст не может быть пустым;
- комментарии после создания не редактируются и не удаляются;
- время хранится в UTC;
- список отображается в хронологическом порядке.

### 5.6. История действий

История append-only и содержит:

- тип события;
- заявку;
- автора;
- timestamp UTC;
- безопасный структурированный payload с изменившимися полями.

Минимальные события:

- `REQUEST_CREATED`;
- `STATUS_CHANGED`;
- `PRIORITY_CHANGED`;
- `ASSIGNEE_CHANGED`;
- `COMMENT_ADDED`;
- `ATTACHMENT_ADDED`;
- `ATTACHMENT_DELETED`.

Пароли, session tokens, presigned URLs и секреты никогда не попадают в историю или логи.

### 5.7. Поиск и фильтрация

Список заявок поддерживает:

- фильтр по статусу;
- фильтр по приоритету;
- фильтр по ответственному;
- поиск по номеру, заголовку, имени клиента и телефону;
- сортировку по дате изменения;
- серверную пагинацию.

### 5.8. Вложения

Вложения добавляются только на фазе S3.

Правила:

- разрешённые типы: PDF, JPEG, PNG, TXT;
- максимальный размер по умолчанию: 10 MiB, значение конфигурируемое;
- бинарные данные не проходят через приложение при скачивании;
- загрузка и скачивание выполняются через короткоживущие presigned URLs;
- S3 bucket закрыт от публичного доступа;
- object key генерируется сервером и не содержит исходный путь пользователя;
- metadata в PostgreSQL создаётся только для разрешённого пользователя;
- незавершённые загрузки очищаются lifecycle policy или отдельной процедурой;
- удаление логическое на уровне приложения; физическая политика удаления явно документируется.

---

## 6. Интерфейс

### 6.1. Технология

Интерфейс реализуется серверными HTML-шаблонами FastAPI/Jinja2. Допускается HTMX для небольших интерактивных операций. Отдельный React/Vue/Next.js frontend запрещён в основной версии.

### 6.2. Язык и направление

- основной интерфейс — иврит;
- весь layout имеет `dir="rtl"` и `lang="he"`;
- технические identifiers и значения enum остаются на английском в коде и БД;
- пользователь видит переведённые названия статусов и ошибок;
- даты и номера отображаются понятно для пользователя в Израиле;
- README и техническая документация пишутся на английском.

### 6.3. Обязательные экраны

- вход;
- список заявок;
- создание заявки;
- карточка заявки;
- клиенты;
- управление сотрудниками для administrator;
- понятные страницы ошибок 403, 404 и 500.

Дизайн должен быть аккуратным, адаптивным и пригодным для демонстрации, но не должен превращаться в отдельный frontend-проект.

---

## 7. API

HTML-интерфейс и REST API используют один application layer. Бизнес-правила нельзя дублировать в route handlers.

Минимальный REST API:

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/logout

POST   /api/v1/customers
GET    /api/v1/customers
GET    /api/v1/customers/{customer_id}
PATCH  /api/v1/customers/{customer_id}

POST   /api/v1/requests
GET    /api/v1/requests
GET    /api/v1/requests/{request_id}
PATCH  /api/v1/requests/{request_id}
POST   /api/v1/requests/{request_id}/comments
GET    /api/v1/requests/{request_id}/history

POST   /api/v1/requests/{request_id}/attachments/initiate
POST   /api/v1/requests/{request_id}/attachments/{attachment_id}/complete
GET    /api/v1/requests/{request_id}/attachments/{attachment_id}/download

GET    /health/live
GET    /health/ready
```

Требования:

- OpenAPI генерируется FastAPI;
- ошибки имеют единый JSON-формат: `code`, `message`, `details`, `request_id`;
- входные и выходные модели разделены;
- пагинация имеет предсказуемый контракт;
- `PATCH` не может молча перезаписать более новую версию заявки;
- readiness проверяет критические зависимости, liveness не зависит от БД;
- публичная документация API в production либо закрывается аутентификацией, либо отключается конфигурацией.

---

## 8. Модель данных

Минимальные таблицы:

### `users`

- `id UUID PK`;
- `email CITEXT UNIQUE NOT NULL` или эквивалентный функциональный unique index;
- `password_hash TEXT NOT NULL`;
- `display_name TEXT NOT NULL`;
- `role TEXT/ENUM NOT NULL`;
- `is_active BOOLEAN NOT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`;
- `updated_at TIMESTAMPTZ NOT NULL`.

### `customers`

- `id UUID PK`;
- `name TEXT NOT NULL`;
- `phone TEXT NULL`;
- `email TEXT NULL`;
- `address TEXT NULL`;
- `note TEXT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`;
- `updated_at TIMESTAMPTZ NOT NULL`.

### `service_requests`

- `id UUID PK`;
- `request_number BIGINT/sequence UNIQUE NOT NULL`;
- `customer_id UUID FK NOT NULL`;
- `title TEXT NOT NULL`;
- `description TEXT NOT NULL`;
- `status TEXT/ENUM NOT NULL`;
- `priority TEXT/ENUM NOT NULL`;
- `assigned_to UUID FK NULL`;
- `created_by UUID FK NOT NULL`;
- `version INTEGER NOT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`;
- `updated_at TIMESTAMPTZ NOT NULL`;
- `completed_at TIMESTAMPTZ NULL`.

### `comments`

- `id UUID PK`;
- `request_id UUID FK NOT NULL`;
- `author_id UUID FK NOT NULL`;
- `body TEXT NOT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`.

### `request_events`

- `id UUID PK`;
- `request_id UUID FK NOT NULL`;
- `actor_id UUID FK NULL`;
- `event_type TEXT NOT NULL`;
- `payload JSONB NOT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`.

### `attachments`

Добавляется только в фазе S3:

- `id UUID PK`;
- `request_id UUID FK NOT NULL`;
- `uploaded_by UUID FK NOT NULL`;
- `original_name TEXT NOT NULL`;
- `object_key TEXT UNIQUE NOT NULL`;
- `content_type TEXT NOT NULL`;
- `size_bytes BIGINT NOT NULL`;
- `status TEXT NOT NULL`;
- `created_at TIMESTAMPTZ NOT NULL`;
- `completed_at TIMESTAMPTZ NULL`;
- `deleted_at TIMESTAMPTZ NULL`.

Все схемные изменения выполняются только через Alembic. `create_all()` в runtime запрещён.

---

## 9. Технический стек

- Python 3.12;
- FastAPI;
- Uvicorn;
- Jinja2;
- SQLAlchemy 2.x;
- Alembic;
- Pydantic 2.x и `pydantic-settings`;
- PostgreSQL 16;
- pytest;
- Ruff;
- mypy;
- Docker и Docker Compose;
- Terraform для итоговой AWS-инфраструктуры;
- GitHub Actions для CI/CD;
- AWS: ECR, ECS Fargate, ALB, RDS PostgreSQL, S3, CloudWatch, IAM, Secrets Manager;
- SQS и DLQ только в фазе расширения.

Зависимости фиксируются lock-файлом. Выбор конкретного package manager должен быть единым для всего проекта и зафиксирован в ADR.

---

## 10. Архитектура приложения

### 10.1. Слои

```text
Presentation: HTTP routes, HTML, API schemas
Application: use cases, authorization orchestration, transactions
Domain: entities, enums, business rules, domain errors
Infrastructure: SQLAlchemy repositories, S3, configuration, logging
```

Требования:

- route handlers остаются тонкими;
- domain не импортирует FastAPI, SQLAlchemy или AWS SDK;
- application layer управляет use cases и границами транзакций;
- инфраструктурные реализации заменяемы в тестах;
- бизнес-правила тестируются без AWS;
- AWS SDK-вызовы из presentation layer запрещены.

### 10.2. Предлагаемая структура репозитория

```text
serviceflow-il/
├── src/serviceflow/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── presentation/
│   │   ├── api/
│   │   ├── web/
│   │   ├── templates/
│   │   └── static/
│   ├── config.py
│   └── main.py
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── infra/terraform/
│   ├── modules/
│   └── environments/dev/
├── scripts/
├── docs/
│   ├── adr/
│   ├── architecture/
│   ├── runbooks/
│   └── screenshots/
├── .github/workflows/
├── Dockerfile
├── compose.yaml
├── Makefile
├── README.md
└── SPEC.md
```

---

## 11. Итоговая AWS-архитектура основной версии

```text
Internet
   |
   v
Application Load Balancer
   |
   v
ECS Fargate service: FastAPI
   |                 |
   v                 v
RDS PostgreSQL       S3 private bucket

ECR stores image
Secrets Manager supplies DB credentials
CloudWatch receives logs, metrics and alarms
IAM roles grant least-privilege access
GitHub Actions authenticates through OIDC
Terraform describes persistent infrastructure
```

### 11.1. Сеть

- отдельная VPC для проекта;
- минимум две Availability Zones для ALB subnet mapping;
- ALB находится в public subnets;
- RDS находится в private DB subnets и не имеет public access;
- для учебной dev-среды ECS tasks допускается размещать в public subnets с public IP, чтобы не оплачивать NAT Gateway;
- security group ALB принимает HTTP/HTTPS из интернета;
- security group ECS принимает application port только от ALB security group;
- security group RDS принимает PostgreSQL только от ECS security group;
- административный доступ к БД из интернета не открывается;
- NAT Gateway в проекте запрещён без отдельного решения пользователя из-за постоянной стоимости.

### 11.2. ECS/Fargate

- один ECS service;
- `desired_count = 1` в dev;
- минимальный разумный размер task: 0.25 vCPU / 0.5 GiB, если приложение стабильно проходит health checks;
- rolling deployment;
- container health check;
- ECS deployment circuit breaker с rollback;
- task execution role отделена от task role;
- immutable image tags на основе Git commit SHA;
- тег `latest` не является источником production deployment.

### 11.3. RDS

- PostgreSQL;
- Single-AZ для учебной dev-среды;
- минимальный подходящий instance class, например `db.t4g.micro`, если доступен в выбранном регионе;
- storage encryption включён;
- automated backups с небольшим retention;
- deletion protection в постоянной demo-среде, но конфигурируемо отключаема для временной учебной среды;
- схема обновляется контролируемой командой миграции, а не автоматически каждым web-контейнером;
- секрет подключения не хранится в Git или Terraform state в открытом виде.

### 11.4. S3

- Block Public Access включён;
- default encryption включено;
- доступ только task role;
- CORS ограничен нужными методами и origin;
- lifecycle rule очищает незавершённые multipart uploads;
- bucket name генерируется и не захардкожен;
- presigned URL живёт минимально необходимое время.

### 11.5. Observability

- структурированные JSON-логи в production;
- correlation/request ID проходит через запрос и попадает в ответ и лог;
- CloudWatch log group имеет ограниченный retention;
- обязательные alarms: ECS running task count, ALB unhealthy targets, ALB 5xx, RDS storage/CPU либо connection pressure;
- dashboard показывает базовое состояние приложения;
- чувствительные данные и полные тела пользовательских запросов не логируются.

---

## 12. Безопасность

- принцип least privilege для IAM;
- никаких AWS access keys в репозитории, Docker image или GitHub secrets;
- GitHub Actions использует AWS OIDC и ограниченную deploy role;
- root AWS account не используется для разработки и deployment;
- секреты не передаются через build arguments;
- production config отделён от local config;
- входные данные валидируются;
- SQL только через ORM/параметризованные запросы;
- HTML экранируется;
- upload filename не используется как S3 key;
- security headers добавляются приложением или ALB;
- зависимости проверяются на известные уязвимости в CI;
- контейнер запускается не от root;
- Docker image не содержит `.git`, тестовые данные, `.env` или локальные credentials;
- публичные endpoints ограничены только необходимыми маршрутами;
- readiness не раскрывает connection strings и внутренние ошибки.

HTTPS с ACM и собственным доменом — отдельное улучшение. Если домена нет, портфельная демонстрация может использовать HTTP ограниченное время, но README обязан честно указать это ограничение. Нельзя заявлять production-ready security без HTTPS.

---

## 13. Управление стоимостью AWS

Проект учебный и должен минимизировать риск непредвиденных расходов.

Обязательные правила:

- используется только одна среда `dev`, пока пользователь явно не запросит другую;
- каждый AWS-ресурс получает теги `Project`, `Environment`, `ManagedBy` и `Owner` без персональных данных;
- до deployment документируется ожидаемая месячная стоимость постоянно работающей среды;
- отдельно перечисляются ресурсы с почасовой или постоянной оплатой: ALB, Fargate task, RDS, Secrets Manager, public IPv4, logs и storage;
- NAT Gateway не создаётся;
- Multi-AZ RDS не создаётся;
- количество задач равно одной;
- CloudWatch log retention ограничен;
- AWS Budget и billing alerts настраиваются до длительного запуска среды;
- предоставляются команды безопасного `terraform destroy` и список ресурсов, которые могут сохраниться после destroy;
- перед destroy пользователь подтверждает, нужно ли сохранить DB snapshot и файлы S3;
- никакой нагрузочный тест в AWS без отдельного разрешения;
- после учебной сессии ресурсы либо выключаются/удаляются, либо пользователь явно решает оставить demo онлайн.

Terraform plan обязательно проверяется перед apply. Codex не выполняет `terraform apply` или `terraform destroy` без явного разрешения пользователя на конкретный plan/target environment.

---

## 14. Конфигурация

Конфигурация задаётся переменными среды и валидируется при запуске.

Минимальные параметры:

```text
APP_ENV
APP_DEBUG
APP_BASE_URL
APP_SECRET_KEY
DATABASE_URL
SESSION_COOKIE_SECURE
LOG_LEVEL
AWS_REGION
S3_BUCKET_NAME
PRESIGNED_URL_TTL_SECONDS
MAX_UPLOAD_SIZE_BYTES
```

Правила:

- `.env.example` содержит только безопасные примеры;
- реальные `.env` игнорируются Git;
- приложение завершает запуск с понятной ошибкой при отсутствии обязательной конфигурации;
- production не имеет небезопасных default secrets;
- AWS region выбирается параметром; ресурсы не должны быть неявно распределены по регионам.

---

## 15. Тестирование и качество

### 15.1. Обязательные проверки

- unit tests доменных правил;
- integration tests repositories и migrations на PostgreSQL;
- API tests прав доступа и ошибок;
- tests status workflow;
- tests optimistic concurrency;
- tests authentication/session/CSRF;
- S3 adapter tests через mock/fake на обычном CI;
- smoke test Docker image;
- smoke test deployed `/health/live` и `/health/ready`;
- Terraform `fmt`, `validate` и lint/security scan;
- Ruff format/check;
- mypy;
- dependency/security scan.

### 15.2. Test isolation

- обычные тесты не обращаются к реальному AWS;
- тесты не зависят от порядка запуска;
- integration DB создаётся отдельно от dev DB;
- время и UUID подменяются там, где это требуется для детерминизма;
- локальная проверка выполняется одной документированной командой.

### 15.3. Минимальный quality gate

Pull request или main pipeline не проходит, если:

- есть failing tests;
- Ruff или mypy завершаются ошибкой;
- migration chain повреждена;
- Docker image не собирается;
- Terraform validation не проходит для фаз, где Terraform уже введён.

Искусственная цель 100% coverage не устанавливается. Критические доменные правила и безопасность должны быть покрыты полностью; итоговый coverage публикуется и не должен снижаться без объяснения.

---

## 16. Поэтапная реализация

Каждая фаза реализуется отдельным запросом к Codex. Следующая фаза начинается только после приёмки пользователем предыдущей.

### Phase 0 — проектный baseline и защита от расходов

Цель: создать контролируемый фундамент без AWS-ресурсов.

Работы:

- структура репозитория;
- `SPEC.md`, README skeleton, contributing notes;
- Python project и lock-файл;
- lint/type/test configuration;
- ADR-001: modular monolith;
- ADR-002: server-rendered Hebrew UI;
- ADR-003: phased AWS adoption;
- `.gitignore`, `.env.example`;
- Makefile или единый task runner;
- документ `docs/aws-cost-safety.md`;
- CI только для lint/type/unit tests;
- первый пустой FastAPI app с liveness endpoint.

Запрещено:

- создавать AWS-ресурсы;
- добавлять Terraform resources;
- реализовывать бизнес-функции.

Критерии приёмки:

- приложение запускается локально;
- `/health/live` возвращает 200;
- все проверки выполняются одной командой;
- CI проходит;
- нет secrets и случайных credentials;
- создан отдельный коммит.

### Phase 1 — локальное полноценное приложение

Цель: завершить бизнес-функциональность до AWS.

Работы:

- domain/application/infrastructure/presentation layers;
- PostgreSQL через Docker Compose;
- Alembic migrations;
- users, customers, requests, comments, events;
- роли и разрешения;
- authentication, secure sessions, CSRF;
- REST API;
- Hebrew-first RTL web UI;
- фильтры, поиск, пагинация;
- seed/demo data;
- unit и integration tests;
- health/readiness endpoints;
- локальный runbook.

Вложения на этой фазе не реализуются.

Критерии приёмки:

- чистый checkout поднимается по README;
- миграции применяются с нуля;
- все основные пользовательские сценарии работают;
- запрещённые действия дают 403 или доменную ошибку;
- история соответствует изменениям;
- повторное сохранение старой версии не затирает новую;
- тесты и quality gate проходят;
- приложение проверено в Docker Compose;
- создан отдельный коммит.

### Phase 2 — Docker image, ECR и первый Fargate smoke deployment

Цель: понять путь контейнера от локальной сборки до запущенной ECS task, не добавляя ALB и RDS.

Работы:

- production multi-stage Dockerfile;
- non-root runtime user;
- локальный container smoke test;
- минимальный Terraform bootstrap для ECR и необходимых IAM roles;
- публикация image в ECR с Git SHA tag;
- ECS cluster, task definition и одна временная Fargate task/service;
- CloudWatch application logs;
- отдельный smoke mode приложения без бизнес-записи, если cloud DB ещё отсутствует;
- runbook диагностики ECR → task definition → task → logs.

Допускается временное использование default VPC или минимальной явно описанной сети только для smoke deployment. Это промежуточное состояние и не считается итоговой архитектурой.

Запрещено:

- ALB;
- RDS;
- S3;
- постоянная публичная production-эксплуатация smoke mode.

Критерии приёмки:

- образ воспроизводимо собирается;
- image находится в ECR под immutable tag;
- Fargate task переходит в `RUNNING`;
- liveness проверяется согласованным способом;
- логи видны в CloudWatch;
- остановленная task не оставляет непонятных активных ресурсов;
- Terraform plan и состояние документированы;
- создан отдельный коммит.

### Phase 3 — VPC, ALB и стабильный HTTP-маршрут

Цель: понять путь запроса Internet → ALB → ECS.

Работы:

- отдельная VPC;
- public subnets минимум в двух AZ;
- route tables и Internet Gateway;
- ALB, target group и listener;
- ECS service с одной task;
- security groups по источникам, а не широким port rules;
- ALB health checks;
- deployment circuit breaker;
- CloudWatch metrics и базовые alarms для ALB/ECS;
- runbook диагностики сети и unhealthy target.

RDS ещё не добавляется. Приложение работает в ограниченном smoke/demo режиме без заявлений о persistence.

Критерии приёмки:

- публичный ALB endpoint отвечает;
- ECS port недоступен напрямую из интернета;
- target healthy;
- остановка/ошибка контейнера видна в health status и логах;
- нет NAT Gateway;
- Terraform повторно применим без незапланированных изменений;
- создан отдельный коммит.

### Phase 4 — RDS PostgreSQL и постоянные данные

Цель: запустить полное приложение с managed PostgreSQL.

Работы:

- private DB subnets;
- DB subnet group;
- RDS PostgreSQL Single-AZ;
- encryption и backups;
- security group RDS только от ECS;
- controlled migration task/command;
- application readiness зависит от БД;
- connection pool с безопасными лимитами;
- RDS alarms;
- runbook database connectivity и migrations;
- процедура backup/restore rehearsal либо документированная проверка snapshot strategy.

Критерии приёмки:

- RDS не имеет public access;
- полное приложение работает через ALB;
- данные сохраняются после перезапуска ECS task;
- миграции применяются один раз контролируемо;
- rollback приложения не повреждает схему;
- connection errors диагностируются по runbook;
- тестовые credentials отсутствуют в Git;
- создан отдельный коммит.

### Phase 5 — Secrets Manager и укрепление безопасности

Цель: удалить runtime secrets из небезопасной конфигурации.

Работы:

- DB credentials и application secret хранятся в Secrets Manager;
- ECS task definition получает secrets безопасным способом;
- execution role/task role имеют минимальные разные permissions;
- secret values не появляются в Terraform output, logs или CI;
- security headers;
- production cookie settings;
- dependency и container scans;
- IAM policy review;
- security runbook.

Критерии приёмки:

- приложение запускается после новой task deployment;
- secret не виден в repository, GitHub Actions logs и Terraform outputs;
- task не может читать посторонний secret;
- security tests проходят;
- создан отдельный коммит.

### Phase 6 — S3-вложения

Цель: освоить безопасное объектное хранилище без очередей и фоновых workers.

Работы:

- private S3 bucket;
- attachment metadata migration;
- initiate/complete upload flow;
- presigned upload/download URLs;
- validation type/size/status;
- права доступа к вложениям;
- S3 lifecycle rules;
- audit events;
- tests через adapter fake/mock;
- runbook S3 access и CORS.

Критерии приёмки:

- разрешённый файл загружается и скачивается;
- bucket и objects не публичны;
- другой/неавторизованный пользователь не получает ссылку;
- недопустимый type/size отклоняется;
- незавершённая загрузка не отображается как готовая;
- ECS task role имеет доступ только к bucket проекта и нужным actions;
- создан отдельный коммит.

После этой фазы получается законченная основная портфельная версия.

### Phase 7 — Terraform completeness и CI/CD через GitHub OIDC

Цель: сделать deployment воспроизводимым и безопасным.

Работы:

- привести всю постоянную инфраструктуру под Terraform;
- remote state strategy документируется и вводится только осознанно;
- GitHub OIDC provider/deploy role;
- pipeline: checks → image build → ECR push → ECS deployment;
- deploy только immutable Git SHA tag;
- manual approval/environment protection для deployment;
- rollback/runbook;
- генерация architecture diagram и portfolio screenshots;
- README с deployment, cost и trade-offs.

Критерии приёмки:

- pipeline не использует долгоживущие AWS keys;
- failing checks блокируют deployment;
- успешный deployment подтверждается health check;
- неуспешный deployment откатывается или останавливается с понятным статусом;
- `terraform plan` после apply не показывает drift в управляемых ресурсах;
- создан отдельный коммит.

### Phase 8 — необязательное event-driven расширение

Цель: после освоения базового AWS добавить асинхронную обработку файлов.

Бизнес-причина: тяжёлая проверка или обработка вложения не должна увеличивать время ответа API.

Архитектура:

```text
S3 upload completed
        |
        v
       SQS
        |
        v
Fargate worker or Lambda
        |
        v
PostgreSQL processing result

failed messages -> DLQ
```

Работы:

- outbox либо другой надёжный способ публикации события;
- SQS queue и DLQ;
- visibility timeout и redrive policy;
- idempotent consumer;
- bounded retries;
- processing status в БД;
- метрики queue depth, age и DLQ messages;
- replay procedure;
- failure-injection tests.

Критерии приёмки:

- повторная доставка не создаёт повторный результат;
- poison message попадает в DLQ после ограниченного числа попыток;
- API остаётся доступным при остановленном worker;
- после восстановления worker backlog обрабатывается;
- оператор имеет документированную процедуру replay;
- создан отдельный коммит.

AI-классификация документа допускается только отдельной следующей фазой поверх стабильного processing contract.

---

## 17. Диагностика по слоям

Для каждой AWS-фазы создаётся отдельный runbook. Диагностика выполняется снаружи внутрь:

1. DNS/URL и клиентский запрос;
2. ALB listener и target health;
3. ECS service, desired/running count и stopped task reason;
4. container health и CloudWatch logs;
5. application configuration;
6. security groups и route tables;
7. RDS status, connectivity и migrations;
8. S3 permissions/CORS/presigned flow;
9. SQS/DLQ только после Phase 8.

Runbook не должен ограничиваться списком команд: для каждой проверки указываются ожидаемый результат и следующая ветка поиска.

---

## 18. Документация для портфолио

Итоговый README на английском обязан содержать:

- задачу и целевую аудиторию;
- короткое demo GIF/video или screenshots без персональных данных;
- актуальную architecture diagram;
- объяснение выбора ECS/Fargate вместо Lambda/EKS;
- объяснение выбора PostgreSQL вместо DynamoDB;
- описание phased evolution;
- security decisions;
- observability;
- local setup;
- deployment overview;
- tests и CI/CD;
- approximate AWS cost;
- известные ограничения;
- trade-offs и возможные следующие шаги.

Нельзя использовать формулировки `production-ready`, `highly available` или `zero-downtime`, если соответствующие свойства не проверены и не обеспечены текущей конфигурацией.

В `docs/architecture/` сохраняются диаграммы фаз, а в `docs/adr/` — важные решения и отвергнутые альтернативы.

---

## 19. Definition of Done для любой фазы

Фаза завершена только если:

- реализован весь её scope;
- не реализован scope следующих фаз;
- код отформатирован и проходит static checks;
- все относящиеся тесты проходят;
- новые миграции проверены с чистой БД и на upgrade path;
- документация и `.env.example` актуальны;
- secrets и персональные данные отсутствуют;
- локальная или AWS-проверка выполнена в соответствии с фазой;
- добавлен/обновлён runbook;
- пользователь получил точный отчёт;
- изменения зафиксированы отдельным Git-коммитом после разрешения пользователя или согласно его установленному workflow.

---

## 20. Обязательный формат отчёта Codex после каждой фазы

```text
Phase N completed / blocked

Implemented:
- ...

Important files:
- ...

Verification performed:
- command/check -> result

AWS resources created or changed:
- resource -> purpose -> cost implication

Known limitations:
- ...

Git status / commit:
- ...

Next phase was not started.
```

Если фаза заблокирована, Codex обязан указать:

- точный блокер;
- проверенные факты;
- что не было изменено;
- минимальный выбор, требуемый от пользователя;
- безопасный следующий шаг.

---

## 21. Правила работы Codex с AWS

1. Сначала читать `SPEC.md`, текущий phase prompt, README, ADR и `git status`.
2. Не исправлять и не перезаписывать посторонние пользовательские изменения.
3. Не использовать root user и не создавать долгоживущие access keys.
4. Не выводить credentials и secret values в терминал, отчёт или файлы.
5. Сначала выполнять read-only проверки и `terraform plan`.
6. Перед `apply`, deployment, database migration в AWS или `destroy` остановиться и получить явное разрешение пользователя.
7. Не создавать NAT Gateway, EKS, Multi-AZ RDS, дополнительные среды или платные security/observability products без отдельного решения.
8. Не удалять RDS, S3 data, snapshots, Terraform state или ECR images без подтверждения конкретной цели.
9. Любой временный ресурс должен иметь понятную процедуру удаления.
10. Не переходить к следующей фазе автоматически.

---

## 22. Финальные критерии проекта

Основной проект считается завершённым после Phase 7, если:

- приложение работает локально и в AWS;
- HTTP-запрос проходит через ALB в ECS Fargate;
- бизнес-данные хранятся в private RDS PostgreSQL;
- вложения безопасно хранятся в private S3;
- secrets не находятся в коде или CI;
- логи, метрики и основные alarms доступны в CloudWatch;
- инфраструктура воспроизводима через Terraform;
- deployment выполняется GitHub Actions через OIDC;
- тесты и quality gates проходят;
- стоимость и процедура удаления среды документированы;
- README и демонстрационные материалы позволяют понять проект за несколько минут;
- разработчик может объяснить назначение каждого AWS-сервиса и путь диагностики сбоя.

Phase 8 является самостоятельным портфельным улучшением и не блокирует завершение основной версии.

---

## 23. Рекомендуемый первый запрос к Codex

```text
Прочитай SPEC.md полностью и реализуй только Phase 0.

Не создавай AWS-ресурсы и не добавляй инфраструктуру следующих фаз.
Сначала проверь состояние репозитория и сообщи, если существующие файлы или изменения конфликтуют со спецификацией. Затем реализуй Phase 0, выполни все доступные проверки и представь отчёт строго в формате раздела 20 SPEC.md.

Следующую фазу не начинай. Коммит создавай только если это разрешено текущими инструкциями пользователя.
```
