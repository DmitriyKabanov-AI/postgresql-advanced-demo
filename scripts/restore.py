#!/usr/bin/env python3
"""
Восстановление PostgreSQL из бэкапа
Перед восстановлением БД полностью удаляется через SQL с принудительным завершением подключений

Использование:
    python scripts/restore.py --list
    python scripts/restore.py --latest
    python scripts/restore.py --file backup_20250101_120000.sql
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
DB_NAME = "demo"
DB_USER = "postgres"
CONTAINER_NAME = "postgresql-advanced-demo-db"
BACKUP_DIR = "backups"
BACKUP_RETENTION_DAYS = 7


def list_backups():
    """Показывает список доступных бэкапов"""
    if not os.path.exists(BACKUP_DIR):
        print("📭 Папка backups/ не найдена")
        return []

    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith(('.sql', '.dump'))]
    if not backups:
        print("📭 Нет бэкапов")
        return []

    backups.sort(reverse=True)
    print("\n📋 Доступные бэкапы:")
    print("-" * 70)
    for i, f in enumerate(backups, 1):
        path = os.path.join(BACKUP_DIR, f)
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            print(f"   {i}. {f} ({size:.2f} MB) - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)
    return backups


def kill_all_connections():
    """Завершает все активные подключения к БД через SQL"""
    print("🔌 Завершение всех подключений к БД...")
    sql = f"""
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '{DB_NAME}'
      AND pid <> pg_backend_pid();
    """
    cmd = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d postgres -c "{sql}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Небольшая пауза, чтобы подключения точно завершились
    time.sleep(2)
    
    # Проверяем, остались ли подключения
    check_sql = f"SELECT COUNT(*) FROM pg_stat_activity WHERE datname = '{DB_NAME}';"
    check_cmd = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d postgres -t -c "{check_sql}"'
    check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    try:
        remaining = int(check_result.stdout.strip())
        if remaining == 0:
            print("✅ Все подключения завершены")
        else:
            print(f"⚠️ Осталось {remaining} подключений, пробуем ещё раз...")
            time.sleep(1)
            # Повторяем попытку
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
            time.sleep(1)
    except:
        pass
    
    return True


def drop_and_create_database():
    """
    Удаляет и создаёт БД заново через SQL
    Использует DROP DATABASE WITH (FORCE) если доступно, иначе обычный DROP
    """
    print(f"🗑️ Удаление и создание базы данных {DB_NAME}...")
    
    # Сначала завершаем все подключения
    kill_all_connections()
    
    # Пробуем удалить с FORCE (PostgreSQL 13+)
    cmd_drop_force = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d postgres -c "DROP DATABASE IF EXISTS {DB_NAME} WITH (FORCE);"'
    result_drop = subprocess.run(cmd_drop_force, shell=True, capture_output=True, text=True)
    
    # Если FORCE не сработал, пробуем обычный DROP
    if result_drop.returncode != 0:
        print("   (WITH FORCE не поддерживается, пробуем обычный DROP...)")
        cmd_drop = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d postgres -c "DROP DATABASE IF EXISTS {DB_NAME};"'
        result_drop = subprocess.run(cmd_drop, shell=True, capture_output=True, text=True)
    
    if result_drop.returncode != 0:
        print(f"⚠️ Ошибка удаления: {result_drop.stderr}")
        return False
    
    # Создаём БД заново
    cmd_create = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d postgres -c "CREATE DATABASE {DB_NAME} OWNER {DB_USER};"'
    result_create = subprocess.run(cmd_create, shell=True, capture_output=True, text=True)
    
    if result_create.returncode == 0:
        print(f"✅ База данных {DB_NAME} пересоздана")
        return True
    else:
        print(f"❌ Ошибка создания: {result_create.stderr}")
        return False


def drop_dwh_schema():
    """Удаляет схему dwh (если осталась) перед восстановлением"""
    print("🗑️ Удаление схемы dwh (если существует)...")
    cmd = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} -c "DROP SCHEMA IF EXISTS dwh CASCADE;"'
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("✅ Схема dwh удалена")


def restore_from_backup(backup_filename):
    """Восстанавливает БД из указанного бэкапа"""
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    if not os.path.exists(backup_path):
        print(f"❌ Файл не найден: {backup_path}")
        return False

    size_mb = os.path.getsize(backup_path) / (1024 * 1024)

    print("=" * 50)
    print("⚠️  ВОССТАНОВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("=" * 50)
    print(f"📁 Файл: {backup_filename}")
    print(f"📦 Размер: {size_mb:.2f} MB")

    confirm = input("\n❓ Будет выполнено: удаление БД → создание новой → восстановление. Продолжить? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Отменено")
        return False

    print("\n🔄 Начинаем восстановление...")

    try:
        # 1. Удаляем и создаём БД заново
        if not drop_and_create_database():
            print("❌ Не удалось пересоздать БД")
            return False
        
        # 2. Дополнительно удаляем схему dwh (на случай, если осталась)
        drop_dwh_schema()
        
        # 3. Восстанавливаем данные
        print(f"📀 Восстановление данных из {backup_filename}...")
        
        if backup_filename.endswith('.dump'):
            # Custom .dump формат
            with open(backup_path, 'rb') as f:
                result = subprocess.run(
                    f"docker exec -i {CONTAINER_NAME} pg_restore -U {DB_USER} -d {DB_NAME} -v --clean --if-exists",
                    stdin=f, shell=True, capture_output=True)
                if result.returncode != 0:
                    print(f"⚠️ Предупреждения при восстановлении: {result.stderr.decode() if result.stderr else ''}")
        else:
            # Обычный SQL формат (с опцией игнорирования ошибок)
            with open(backup_path, 'r', encoding='utf-8', errors='ignore') as f:
                result = subprocess.run(
                    f"docker exec -i {CONTAINER_NAME} psql -U {DB_USER} {DB_NAME} -v ON_ERROR_STOP=0",
                    stdin=f, shell=True, capture_output=True)
                if result.returncode != 0:
                    print(f"⚠️ Предупреждения при восстановлении: {result.stderr.decode() if result.stderr else ''}")
        
        # 4. Обновляем материализованную витрину
        print("🔄 Обновление материализованной витрины...")
        subprocess.run(
            f"docker exec {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} -c 'REFRESH MATERIALIZED VIEW dwh.sales_kpi;'",
            shell=True, capture_output=True)
        
        # 5. Перезапускаем зависимые сервисы
        print("🔄 Перезапуск сервисов (postgres-exporter, grafana)...")
        subprocess.run("docker-compose restart postgres-exporter grafana", shell=True, capture_output=True)
        
        # 6. Проверяем количество строк
        check_cmd = f'docker exec {CONTAINER_NAME} psql -U {DB_USER} -d {DB_NAME} -t -c "SELECT COUNT(*) FROM dwh.fact_sales;"'
        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        try:
            count = int(check_result.stdout.strip())
            print(f"📊 Восстановлено строк в fact_sales: {count}")
        except:
            pass
        
        print("\n✅ Восстановление завершено успешно!")
        print("💡 Проверьте: http://localhost:3000 (Grafana), тесты: docker-compose run --rm test")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка восстановления: {e.stderr if e.stderr else 'Неизвестная ошибка'}")
        return False
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        return False


def cleanup_old_backups():
    """Удаляет бэкапы старше BACKUP_RETENTION_DAYS дней"""
    ensure_backup_dir()
    now = datetime.now()
    deleted = 0
    for f in os.listdir(BACKUP_DIR):
        if not f.endswith(('.sql', '.dump')):
            continue
        path = os.path.join(BACKUP_DIR, f)
        if not os.path.exists(path):
            continue
        age = (now - datetime.fromtimestamp(os.path.getmtime(path))).days
        if age > BACKUP_RETENTION_DAYS:
            os.remove(path)
            deleted += 1
            print(f"   🗑️ Удалён: {f} (возраст {age} дней)")
    print(f"\n✅ Удалено {deleted} бэкапов (старше {BACKUP_RETENTION_DAYS} дней)")


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Восстановление PostgreSQL')
    parser.add_argument('--file', help='Имя файла бэкапа')
    parser.add_argument('--list', action='store_true', help='Список бэкапов')
    parser.add_argument('--latest', action='store_true', help='Восстановить из последнего')
    args = parser.parse_args()

    if args.list:
        list_backups()
    elif args.latest:
        backups = list_backups()
        if backups:
            restore_from_backup(backups[0])
        else:
            print("❌ Нет бэкапов для восстановления")
    elif args.file:
        restore_from_backup(args.file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()