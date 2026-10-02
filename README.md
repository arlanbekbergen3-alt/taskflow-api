# 🚀 TaskFlow API

Асинхронный REST API для управления задачами и категориями, построенный на чистой трехслойной архитектуре (**Router → Service → Repository**).

---

## 🛠 Технологический стек

* **Framework:** FastAPI
* **Database:** PostgreSQL + asyncpg
* **ORM:** SQLAlchemy 2.0 (AsyncSession)
* **Migrations:** Alembic
* **Validation & Schemas:** Pydantic v2
* **Containerization:** Docker & Docker Compose

---

## 🏛 Архитектура проекта

Проект спроектирован с учетом разделения ответственности (Separation of Concerns):

* `routers/` — принимает HTTP-запросы, отвечает за валидацию входящих/исходящих данных и статус-коды.
* `services/` — инкапсулирует бизнес-логику, правила обработки и выброс HTTP-исключений.
* `repositories/` — изолирует слой работы с базой данных (CRUD операции) через SQLAlchemy 2.0.
* `models/` — декларативные ORM-модели базы данных.
* `schemas/` — Pydantic-схемы для валидации запросов и ответов.
* `alembic/` — управление миграциями структуры БД.

---

## 🚀 Быстрый запуск

### 1. Запуск через Docker Compose (Рекомендуется)

Для запуска всей инфраструктуры (FastAPI + PostgreSQL) одной командой:

```bash
docker compose up --build
