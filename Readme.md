# PostgreSQL Advanced Demo: DWH, мониторинг, дашборды

**Портфолио-проект для Data Engineer / Data Analyst**  
Демонстрация углублённой работы с PostgreSQL: хранимые функции, триггеры, тестирование pgTAP, построение DWH (схема «звезда»), мониторинг (Prometheus + Grafana) и бизнес-дашборды по продажам продуктов TrueConf.

## 🚀 Быстрый старт (Docker Compose)

```bash
git clone https://github.com/DmitriyKabanov-AI/postgresql-advanced-demo.git
cd postgresql-advanced-demo
docker-compose up -d
После запуска:

PostgreSQL – порт 5433 (хост), БД demo, пользователь postgres, пароль postgres_pass

Prometheus – http://localhost:9090

Grafana – http://localhost:3000 (логин admin / admin)

Данные DWH генерируются автоматически при первом запуске (около 1200 продаж).

📊 Создание дашборда в Grafana (один раз)
Откройте Grafana: http://localhost:3000 (логин admin / admin).

Перейдите в Dashboards → New → New Dashboard → Add visualization.

Выберите источник данных PostgreSQL DWH (он уже настроен автоматически).

Для каждой панели используйте SQL-запросы ниже.

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

Нажмите Apply

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

Нажмите Apply

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

Нажмите Apply

Сохраните дашборд: иконка дискеты → имя DWH Sales Dashboard.

🧪 Тестирование
bash
docker-compose run --rm test
📁 Структура проекта
text
postgresql-advanced-demo/
├── prometheus/            # конфиг Prometheus
├── provisioning/          # автоматическая настройка источника данных PostgreSQL
├── screenshots/           # скриншот дашборда
├── tests/                 # pgTAP тесты
├── 01_init.sql            # OLTP-схема (проекты, задачи, триггеры)
├── dwh_setup.sql          # DWH-схема, генерация данных
├── docker-compose.yml
├── Dockerfile.db
├── Dockerfile.pgtap
└── README.md
🛠 Используемые технологии
PostgreSQL 15 (PL/pgSQL, pgTAP, индексы, триггеры)

Docker / Docker Compose

Prometheus + postgres-exporter

Grafana (источник данных PostgreSQL)

👤 Автор
Dmitriy Kabanov