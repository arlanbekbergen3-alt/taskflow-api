# 📝 Todo-API на FastAPI и SQLAlchemy 2.0

<p align="center">
  <img src="https://shields.io" alt="FastAPI"/>
  <img src="https://shields.io" alt="Postgres"/>
  <img src="https://shields.io" alt="Pydantic"/>
  <img src="https://shields.io" alt="Python"/>
</p>

Асинхронное RESTful API для управления задачами и категориями. Проект демонстрирует правильную архитектуру веб-приложений на Python с использованием современного стека технологий и асинхронного взаимодействия с базой данных.

---

## ✨ Ключевые фичи
- **Полный CRUD** для задач (`Tasks`) и категорий (`Categories`).
- **Связи один-ко-многим:** автоматическая привязка задач к категориям с каскадным поведением (`SET NULL`).
- **Асинхронность:** быстрая работа благодаря `asyncio`, `asyncpg` и асинхронным сессиям SQLAlchemy.
- **Безопасность:** валидация входных и выходных данных через схемы Pydantic v2.
- **Пагинация:** встроенные механизмы `skip` и `limit` для безопасного чтения больших списков.

---

## 🛠 Стек технологий
* **Фреймворк:** FastAPI
* **ORM:** SQLAlchemy 2.0 (Declarative Base, Mapped типы)
* **База данных:** PostgreSQL + драйвер `asyncpg`
* **Валидация и настройки:** Pydantic v2 & Pydantic Settings
* **Идентификаторы:** UUIDv4 в качестве первичных ключей

---

## 🚀 Быстрый запуск

### 1. Клонирование репозитория и подготовка
```bash
git clone https://github.com
cd ваш-репозиторий
```

### 2. Настройка окружения
Создайте файл `.env` в корневой папке и укажите вашу строку подключения к PostgreSQL:
```env
DATABASE_URL=postgresql+asyncpg://postgres:admin@localhost:15432/postgres
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Запуск приложения
```bash
uvicorn asf:app --reload
```
> *Примечание: Замените `asf`, если ваш главный файл называется иначе.*

После запуска интерактивная документация (Swagger UI) будет доступна по адресу:  
🔗 **http://127.0.0**

---

## 📋 Эндпоинты API

### Категории (`/categories`)
* `GET /categories` — Получить список категорий (с пагинацией)
* `POST /categories` — Создать новую категорию
* `PATCH /categories/{id}` — Частично обновить категорию
* `DELETE /categories/{id}` — Удалить категорию

### Задачи (`/tasks`)
* `GET /tasks` — Получить все задачи
* `POST /tasks` — Создать задачу (можно сразу передать `category_id`)
* `PATCH /tasks/{id}` — Обновить текст, статус (`completed`) или сменить категорию
* `DELETE /tasks/{id}` — Удалить задачу

