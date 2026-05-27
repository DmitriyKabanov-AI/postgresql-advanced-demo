# PostgreSQL Advanced Demo: DWH, мониторинг, бэкапы, тесты

**Портфолио-проект для Data Engineer / Data Analyst**  
Демонстрация углублённой работы с PostgreSQL: хранимые функции, триггеры, тестирование pgTAP, построение DWH (схема «звезда»), мониторинг (Prometheus + Grafana), автоматические бэкапы и восстановление.

---

## 🚀 Быстрый старт (Docker Compose)

```bash
git clone https://github.com/DmitriyKabanov-AI/postgresql-advanced-demo.git
cd postgresql-advanced-demo
docker-compose up -d
После запуска:

PostgreSQL – порт 5433 (хост), БД demo, пользователь postgres, пароль postgres_pass

Prometheus – http://localhost:9090

Grafana – http://localhost:3000 (логин admin, пароль admin)

Данные DWH генерируются автоматически при первом запуске (около 1300 продаж).

💾 Резервное копирование
Создание бэкапа
bash
# SQL бэкап (текстовый, человекочитаемый)
python scripts/backup.py

# Custom .dump бэкап (сжатый, быстрое восстановление)
python scripts/backup.py --dump

# Список всех бэкапов
python scripts/backup.py --list

# Удалить бэкапы старше 7 дней
python scripts/backup.py --clean
Просмотр бэкапов
bash
ls -la backups/
🔄 Восстановление из бэкапа
Автоматическое восстановление (рекомендуется)
bash
# Восстановить из последнего бэкапа
python scripts/restore.py --latest

# Восстановить из конкретного файла
python scripts/restore.py --file backup_20260528_010236.sql
python scripts/restore.py --file backup_20260528_010243.dump

# Показать список доступных бэкапов
python scripts/restore.py --list
Скрипт автоматически:

Завершает все подключения к БД

Удаляет текущую БД через DROP DATABASE WITH (FORCE)

Создаёт БД заново

Удаляет старую схему dwh

Восстанавливает данные из бэкапа

Обновляет материализованную витрину

Перезапускает сервисы (Grafana, экспортер)

Ручное восстановление (если скрипт не работает)
bash
# Остановить всё
docker-compose down

# Запустить только БД
docker-compose up -d db

# Восстановить из SQL
Get-Content backups\backup_20260528_010236.sql | docker exec -i postgresql-advanced-demo-db psql -U postgres -d demo

# Восстановить из DUMP
Get-Content backups\backup_20260528_010243.dump | docker exec -i postgresql-advanced-demo-db pg_restore -U postgres -d demo

# Запустить все сервисы
docker-compose up -d
🧪 Тестирование
Запуск тестов pgTAP
bash
docker-compose run --rm test
Ожидаемый вывод:

text
All tests successful.
Files=1, Tests=10
Что проверяют тесты
№	Проверка
1	Функция project_ev_metrics
2	Триггер trg_log_task_status
3	Индекс idx_tasks_assignee
4	Существование триггера
5	Скидка 10% через apply_task_discount
6	Увеличение на -5%
7	Нет отрицательных total_amount в fact_sales
8	Нет сирот во внешних ключах
9	Витрина sales_kpi не пуста
10	Идемпотентность generate_sales_data
📊 Создание дашборда в Grafana (один раз)
Откройте Grafana: http://localhost:3000 (логин admin, пароль admin)

Dashboards → New → New Dashboard → Add visualization

Выберите источник данных PostgreSQL DWH (настроен автоматически)

Для каждой панели используйте SQL-запросы ниже:

Панель 1: Выручка по месяцам (линейный график)
sql
SELECT 
    TO_DATE(year || '-' || month || '-01', 'YYYY-MM-DD') AS time,
    SUM(total_revenue) AS revenue
FROM dwh.sales_kpi
GROUP BY year, month
ORDER BY time
Format: Time series

Title: Выручка по месяцам

Панель 2: Выручка по отраслям (круговая диаграмма)
sql
SELECT 
    industry AS metric,
    SUM(total_revenue) AS value
FROM dwh.sales_kpi
GROUP BY industry
ORDER BY value DESC
Format: Table

Visualization: Pie chart

Title: Выручка по отраслям

Панель 3: Топ продуктов по выручке (столбчатая диаграмма)
sql
SELECT 
    product_name AS metric,
    SUM(total_revenue) AS value
FROM dwh.sales_kpi
GROUP BY product_name
ORDER BY value DESC
Format: Table

Visualization: Bar chart

Title: Топ продуктов по выручке

Нажмите Apply для каждой панели

Сохраните дашборд: иконка дискеты → имя DWH Sales Dashboard

📈 Оптимизация запросов (пример)
Запрос без индекса:

sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM dwh.fact_sales WHERE customer_id = 3;
Результат: Seq Scan (полное сканирование таблицы)

Создание индекса:

sql
CREATE INDEX idx_fact_sales_customer ON dwh.fact_sales(customer_id);
Запрос с индексом:

sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM dwh.fact_sales WHERE customer_id = 3;
Результат: Index Scan (ускорение в 10-100 раз)

🐘 Полезные команды
Подключение к БД
bash
docker exec -it postgresql-advanced-demo-db psql -U postgres -d demo
Проверка количества строк
bash
docker exec postgresql-advanced-demo-db psql -U postgres -d demo -c "SELECT COUNT(*) FROM dwh.fact_sales;"
Остановка всех сервисов
bash
docker-compose down
Полный сброс (удаление всех данных)
bash
docker-compose down -v
docker-compose up -d
python scripts/restore.py --latest
📁 Структура проекта
text
postgresql-advanced-demo/
├── backups/                # папка с бэкапами (игнорируется в Git, кроме примеров)
├── prometheus/             # конфиг Prometheus
├── provisioning/           # автоматическая настройка источника данных PostgreSQL
├── screenshots/            # скриншот дашборда
├── scripts/                # скрипты бэкапа и восстановления
│   ├── backup.py
│   └── restore.py
├── tests/                  # pgTAP тесты
│   └── test_functions.sql
├── 01_init.sql             # OLTP-схема (проекты, задачи, триггеры)
├── dwh_setup.sql           # DWH-схема, генерация данных
├── docker-compose.yml
├── Dockerfile.db
├── Dockerfile.pgtap
└── README.md
🛠 Используемые технологии
PostgreSQL 15 – PL/pgSQL, pgTAP, индексы, триггеры

Docker / Docker Compose – контейнеризация

Prometheus + postgres-exporter – мониторинг

Grafana – визуализация дашбордов

Python – скрипты бэкапа и восстановления

👤 Автор
Dmitriy Kabanov