#!/usr/bin/env python3
"""
Резервное копирование PostgreSQL

Использование:
    python scripts/backup.py              # обычный SQL бэкап (по умолчанию)
    python scripts/backup.py --dump       # custom .dump формат (сжатый, быстрое восстановление)
    python scripts/backup.py --list       # показать все бэкапы
    python scripts/backup.py --clean      # удалить бэкапы старше 7 дней
"""

import os
import subprocess
import argparse
from datetime import datetime

# ========== КОНФИГУРАЦИЯ ==========
DB_NAME = "demo"
DB_USER = "postgres"
CONTAINER_NAME = "postgresql-advanced-demo-db"
BACKUP_DIR = "backups"
BACKUP_RETENTION_DAYS = 7


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def get_backup_filename(format_type):
    """format_type: 'sql' или 'dump'"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".dump" if format_type == 'dump' else ".sql"
    return os.path.join(BACKUP_DIR, f"backup_{timestamp}{ext}")


def create_backup(format_type='sql'):
    """
    Создаёт бэкап базы данных
    format_type: 'sql' или 'dump'
    """
    ensure_backup_dir()
    backup_file = get_backup_filename(format_type)

    print("=" * 60)
    print(f"📀 Резервное копирование PostgreSQL ({format_type.upper()})")
    print("=" * 60)
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🗄️  База: {DB_NAME}")
    print(f"📁 Файл: {backup_file}")

    try:
        if format_type == 'dump':
            # Custom .dump формат (бинарный, сжатый)
            cmd = f"docker exec {CONTAINER_NAME} pg_dump -U {DB_USER} -Fc -b -v {DB_NAME}"
            result = subprocess.run(cmd, shell=True, capture_output=True, check=True)
            with open(backup_file, 'wb') as f:
                f.write(result.stdout)
        else:
            # Обычный SQL формат (текстовый)
            cmd = f"docker exec {CONTAINER_NAME} pg_dump -U {DB_USER} -Fp {DB_NAME}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)

        size_mb = os.path.getsize(backup_file) / (1024 * 1024)
        print(f"\n✅ Бэкап создан!")
        print(f"   Размер: {size_mb:.2f} MB")
        print(f"   Путь: {backup_file}")
        print(f"\n💡 Восстановление: python scripts/restore.py --file {os.path.basename(backup_file)}")
        return backup_file

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка: {e.stderr if e.stderr else 'Неизвестная ошибка'}")
        return None
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return None


def list_backups():
    ensure_backup_dir()
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith(('.sql', '.dump'))]
    if not backups:
        print("📭 Нет бэкапов")
        return

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


def cleanup_old_backups():
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


def main():
    parser = argparse.ArgumentParser(description='Резервное копирование PostgreSQL')
    parser.add_argument('--dump', action='store_true', help='Custom .dump формат (сжатый, быстрое восстановление)')
    parser.add_argument('--list', action='store_true', help='Список бэкапов')
    parser.add_argument('--clean', action='store_true', help='Удалить старые бэкапы')
    args = parser.parse_args()

    if args.list:
        list_backups()
    elif args.clean:
        cleanup_old_backups()
    elif args.dump:
        create_backup(format_type='dump')
    else:
        create_backup(format_type='sql')


if __name__ == "__main__":
    main()