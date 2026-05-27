-- Включим расширение
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица проектов
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица задач
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    assignee TEXT,
    status TEXT CHECK (status IN ('pending','in_progress','done')) DEFAULT 'pending',
    percent_complete INTEGER DEFAULT 0 CHECK (percent_complete BETWEEN 0 AND 100),
    planned_cost NUMERIC(12,2) DEFAULT 0,
    actual_cost NUMERIC(12,2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица истории изменений статуса
CREATE TABLE task_status_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT,
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by TEXT DEFAULT SESSION_USER
);

-- Хранимая функция 1: метрики по проекту
CREATE OR REPLACE FUNCTION project_ev_metrics(p_project_id INTEGER)
RETURNS TABLE(
    total_tasks BIGINT,
    done_tasks BIGINT,
    bac NUMERIC,
    ev NUMERIC,
    cpi NUMERIC
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE status = 'done')::BIGINT,
        SUM(planned_cost) AS bac,
        SUM(planned_cost * percent_complete / 100.0) AS ev,
        CASE WHEN SUM(actual_cost) > 0 THEN SUM(planned_cost * percent_complete / 100.0) / SUM(actual_cost) ELSE 0 END AS cpi
    FROM tasks
    WHERE project_id = p_project_id;
END;
$$;

-- Хранимая функция 2: применить скидку к задаче
CREATE OR REPLACE FUNCTION apply_task_discount(task_id INTEGER, discount_percent NUMERIC)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    UPDATE tasks
    SET
        planned_cost = planned_cost * (1 - discount_percent / 100),
        actual_cost = actual_cost * (1 - discount_percent / 100)
    WHERE id = task_id;
END;
$$;

-- Триггерная функция логирования статуса
CREATE OR REPLACE FUNCTION log_task_status_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO task_status_history(task_id, old_status, new_status)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

-- Триггер
CREATE TRIGGER trg_log_task_status
AFTER UPDATE OF status ON tasks
FOR EACH ROW
EXECUTE FUNCTION log_task_status_change();

-- Индексы
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee);

-- Тестовые данные
INSERT INTO projects (name) VALUES ('AI Platform'), ('Mobile App'), ('Backend Migration');

DO $$
DECLARE
    proj_id INTEGER;
BEGIN
    FOR proj_id IN SELECT id FROM projects LOOP
        INSERT INTO tasks (project_id, name, assignee, status, percent_complete, planned_cost, actual_cost)
        VALUES
            (proj_id, 'Research', 'Alice', 'done', 100, 5000, 4800),
            (proj_id, 'Design', 'Bob', 'in_progress', 60, 8000, 5000),
            (proj_id, 'Implementation', 'Charlie', 'pending', 0, 20000, 0),
            (proj_id, 'Testing', 'Diana', 'pending', 0, 6000, 0);
    END LOOP;
END $$;
