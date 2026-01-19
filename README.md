# Cloude-Storage

Cloude-Storage — это простое и понятное веб-приложение для хранения и обмена файлами.
По сути — мини-аналог Google Drive или Яндекс.Диска, но локально и под твоим контролем.
Построенное на Flask и SQLite.

## Возможности

- Управление файлами: Загрузка, скачивание и удаление файлов
- Аутентификация: Регистрация и вход пользователей
- Обмен файлами: Публичные ссылки для доступа к файлам
- Статистика: Информация об использовании хранилища

## Технологии

**Backend**
- *Python*
- *Flask*

**База данных**
- *SQLite3*

**Frontend**
- *HTML*
- *CSS*

**Безопасность**
- *Flask Sessions*
- *Хеширование паролей*

## Установка и запуск

1. Клонирование и настройка

```bash
# Создание виртуального окружения
python -m venv venv

venv\Scripts\activate

# Установка зависимостей
pip install Flask
```

2. Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: http://your-ip:port

## Структура проекта

```
cloud_storage/
├── app.py                 # Основное приложение Flask
├── database.py            # Работа с базой данных SQLite
├── templates/            # HTML шаблоны
│   ├── base.html         # Базовый шаблон
│   ├── login.html        # Страница входа
│   ├── register.html     # Страница регистрации
│   ├── dashboard.html    # Главная страница
│   ├── upload.html       # Загрузка файлов
│   └── files.html        # Список файлов
└── static/
    ├── css/
    │   └── style.css     # Стили приложения
    └── uploads/          # Папка для хранения файлов
```


<img width="1913" height="947" alt="image" src="https://github.com/user-attachments/assets/be10f5a6-2d79-4fea-8ba6-f24eed556941" />
