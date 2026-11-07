# TaskFlow API

Асинхронный REST API личного таск-трекера: задачи с приоритетами, дедлайнами и описанием, персональные категории, поиск, фильтры, сортировка и статистика. Каждый пользователь видит только свои данные.

**Стек:** FastAPI · PostgreSQL + asyncpg · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 · JWT (PyJWT) + bcrypt · pytest · ruff · Docker Compose · GitHub Actions

## Архитектура

`Router → Service → Repository`

| Слой | Ответственность |
|---|---|
| `routers/` | HTTP: параметры, статус-коды, схемы ответа |
| `services/` | бизнес-правила; бросают доменные ошибки (`core/exceptions.py`), а не `HTTPException` |
| `repositories/` | запросы к БД |
| `models/`, `schemas/` | ORM-модели и Pydantic-схемы |
| `core/` | конфиг, безопасность, зависимости (`dependencies.py`), доменные ошибки |

Доменные ошибки превращаются в HTTP-ответы в одном месте — `main.py`.

## Запуск

```bash
cp .env.example .env        # заполнить DB_PASSWORD и JWT_SECRET_KEY
docker compose up --build   # применяет миграции и стартует API на :8000
```

Swagger: http://localhost:8000/docs (кнопка **Authorize** работает — логин через OAuth2 password flow).

Локально без Docker: `pip install -r requirements-dev.txt`, `alembic upgrade head`, `uvicorn main:app --reload`.

## Тесты и качество

Нужен запущенный PostgreSQL (`DATABASE_URL` из `.env`); тесты сами создают отдельную БД `taskflow_test`.

```bash
pytest --cov        # ~96% покрытия
ruff check .        # линтер
alembic check       # модели совпадают с миграциями
```

То же самое выполняет CI (`.github/workflows/ci.yml`) на каждый push и PR; порог покрытия — 90%.

## Эксплуатация

* Каждый запрос получает `X-Request-ID` (берётся из заголовка, если его прислал прокси). Он попадает во все строки лога и в ответ. `LOG_FORMAT=json` включает JSON-логи для агрегаторов.
* Rate limit хранится в памяти процесса: при нескольких воркерах/репликах лимит действует на каждый отдельно — для общего лимита нужен Redis. За reverse proxy запускайте uvicorn с `--proxy-headers`, иначе все клиенты будут для лимитера одним IP.
* Refresh-токены хранятся только в виде SHA-256, в базе нет пригодных к использованию сессий.

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register` | регистрация (логин 3–50 символов `[A-Za-z0-9_.-]`, пароль 8–72 байта) |
| POST | `/auth/login` | form-data `username`/`password` → `access_token` (30 мин) + `refresh_token` (7 дней). Лимит попыток по IP → 429 + `Retry-After` |
| POST | `/auth/refresh` | обмен refresh-токена на новую пару. Токен одноразовый: повторное использование считается кражей и отзывает все сессии пользователя |
| POST | `/auth/logout` | отзыв refresh-токена (идемпотентно, 204) |
| GET | `/auth/me` | текущий пользователь |
| GET/POST | `/tasks` | список / создание |
| GET | `/tasks/tags` | теги пользователя с количеством задач |
| GET | `/tasks/stats` | всего, выполнено, активно, просрочено, доля выполнения, разбивка по приоритетам |
| GET/PATCH/DELETE | `/tasks/{id}` | одна задача |
| GET/POST | `/categories` | список / создание (имя уникально для пользователя, иначе 409) |
| GET/PATCH/DELETE | `/categories/{id}` | одна категория; при удалении задачи остаются без категории |
| GET | `/health` | проверка живости и соединения с БД |

Поля задачи: `title`, `description`, `priority` (`low|medium|high`), `due_date` (с часовым поясом), `completed`, `category_id`, `tags` (до 10, нормализуются в нижний регистр, у каждого пользователя свои; в PATCH заменяют набор целиком); сервер ведёт `completed_at`, `created_at`, `updated_at`, `is_overdue`.

Фильтры `GET /tasks`: `completed`, `category_id`, `tag`, `priority`, `q` (поиск по названию и описанию), `due_before`, `due_after`, `overdue`, `sort_by` (`created_at|due_date|priority|title`), `order` (`asc|desc`), `skip`, `limit`. Порядок всегда детерминирован, поэтому пагинация стабильна.

## Конфигурация

Все параметры — переменные окружения / `.env` (см. `.env.example`). Приложение не стартует без `DATABASE_URL` и `JWT_SECRET_KEY`.
