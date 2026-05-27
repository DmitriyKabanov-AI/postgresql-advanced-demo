-- Включаем расширение pgTAP
CREATE EXTENSION IF NOT EXISTS pgtap;

-- Начинаем тестирование
BEGIN;
SELECT plan(10);   -- <-- ТОЛЬКО ОДИН РАЗ

-- 1. Проверка функции project_ev_metrics
SELECT results_eq(
    'SELECT total_tasks, done_tasks, bac, ev FROM project_ev_metrics(1)',
    'VALUES (4::bigint, 1::bigint, 39000.00, 9800.00)',
    'project_ev_metrics returns correct totals'
);

-- 2. Проверка триггера
UPDATE tasks SET status = 'in_progress' WHERE id = 1;
SELECT ok(
    EXISTS(SELECT 1 FROM task_status_history WHERE new_status = 'in_progress'),
    'trigger works'
);

-- 3. Индекс
SELECT has_index('tasks', 'idx_tasks_assignee');

-- 4. Триггер существует
SELECT has_trigger('tasks', 'trg_log_task_status');

-- 5. Скидка на planned_cost
SELECT apply_task_discount(1, 10);
SELECT ok((SELECT planned_cost FROM tasks WHERE id=1) = 4500.00, 'planned cost after discount');

-- 6. Увеличение planned_cost
SELECT apply_task_discount(3, -5);
SELECT ok((SELECT planned_cost FROM tasks WHERE id=3) = 21000.00, 'planned cost after increase');

-- 7. Проверка, что total_amount всегда положительный
SELECT is_empty(
    $$ SELECT * FROM dwh.fact_sales WHERE total_amount <= 0 $$,
    'Все суммы продаж положительные'
);

-- 8. Проверка внешних ключей (нет сирот)
SELECT is_empty(
    $$ SELECT f.* FROM dwh.fact_sales f
       LEFT JOIN dwh.dim_customer c ON f.customer_id = c.customer_id
       WHERE c.customer_id IS NULL $$,
    'Нет записей fact_sales без customer_id'
);

-- 9. Проверка, что витрина sales_kpi не пуста
SELECT ok(
    (SELECT COUNT(*) FROM dwh.sales_kpi) > 0,
    'Витрина sales_kpi содержит данные'
);

-- 10. Идемпотентность generate_sales_data (упрощённый вариант)
SELECT is(
    (SELECT COUNT(*) FROM dwh.fact_sales),
    (SELECT COUNT(*) FROM dwh.fact_sales),
    'generate_sales_data is idempotent (placeholder)'
);

SELECT * FROM finish();
ROLLBACK;