import json
import os
import sys
from pathlib import Path


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "progressdesk",
    "user": "postgres",
    "password": os.environ.get("PROGRESSDESK_DB_PASSWORD", ""),
}

APP_USER = {
    "username": "Kartik",
    "email": "kartikhegde062@gmail.com",
    "password": os.environ.get("PROGRESSDESK_APP_PASSWORD", ""),
}

SCHEMA_NAME = "progressdesk"
JSON_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "ProgressDesk" / "tasks.json"


def require_dependency(module_name, package_name=None):
    try:
        return __import__(module_name)
    except ImportError as error:
        package = package_name or module_name
        raise SystemExit(
            f"Missing dependency '{module_name}'. Install it with: pip install {package}"
        ) from error


def load_source_data():
    if not JSON_PATH.exists():
        raise SystemExit(f"Could not find source data file: {JSON_PATH}")
    try:
        raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Could not read source data from {JSON_PATH}: {error}") from error

    if isinstance(raw, dict):
        tasks = raw.get("tasks", [])
        task_sets = raw.get("task_sets", [])
    elif isinstance(raw, list):
        tasks = raw
        task_sets = []
    else:
        raise SystemExit(f"Unexpected JSON structure in {JSON_PATH}")

    return tasks, task_sets


def hash_password(password, bcrypt_module):
    return bcrypt_module.hashpw(password.encode("utf-8"), bcrypt_module.gensalt()).decode("utf-8")


def ensure_schema(cur):
    cur.execute(f"create schema if not exists {SCHEMA_NAME}")

    cur.execute(
        f"""
        create table if not exists {SCHEMA_NAME}.app_user (
            id bigserial primary key,
            username varchar(50) not null unique,
            email varchar(255) not null unique,
            password_hash varchar(255) not null,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

    cur.execute(
        f"""
        create table if not exists {SCHEMA_NAME}.tasks (
            id text primary key,
            user_id bigint not null references {SCHEMA_NAME}.app_user(id) on delete cascade,
            title text not null,
            category varchar(50) not null,
            total_units integer not null check (total_units > 0),
            completed_units integer not null default 0 check (completed_units >= 0),
            unit_name varchar(50) not null,
            estimate_seconds integer not null default 0 check (estimate_seconds >= 0),
            spent_seconds integer not null default 0 check (spent_seconds >= 0),
            timer_started_at timestamptz null,
            notes text not null default '',
            completed_at timestamptz null,
            dropped_at timestamptz null,
            created_at timestamptz not null,
            updated_at timestamptz not null default now()
        )
        """
    )

    cur.execute(
        f"""
        create table if not exists {SCHEMA_NAME}.task_sets (
            id text primary key,
            user_id bigint not null references {SCHEMA_NAME}.app_user(id) on delete cascade,
            title text not null,
            notes text not null default '',
            start_at timestamptz null,
            end_at timestamptz null,
            created_at timestamptz not null,
            updated_at timestamptz not null default now()
        )
        """
    )

    cur.execute(
        f"""
        create table if not exists {SCHEMA_NAME}.task_set_tasks (
            id text primary key,
            task_set_id text not null references {SCHEMA_NAME}.task_sets(id) on delete cascade,
            title text not null,
            category varchar(50) not null,
            total_units integer not null check (total_units > 0),
            completed_units integer not null default 0 check (completed_units >= 0),
            unit_name varchar(50) not null,
            notes text not null default '',
            position integer not null default 0
        )
        """
    )

    cur.execute(
        f"""
        create table if not exists {SCHEMA_NAME}.user_settings (
            user_id bigint not null references {SCHEMA_NAME}.app_user(id) on delete cascade,
            setting_key varchar(100) not null,
            setting_value text not null,
            primary key (user_id, setting_key)
        )
        """
    )

    cur.execute(f"create index if not exists idx_{SCHEMA_NAME}_tasks_user_id on {SCHEMA_NAME}.tasks(user_id)")
    cur.execute(f"create index if not exists idx_{SCHEMA_NAME}_tasks_category on {SCHEMA_NAME}.tasks(category)")
    cur.execute(f"create index if not exists idx_{SCHEMA_NAME}_tasks_dropped_at on {SCHEMA_NAME}.tasks(dropped_at)")
    cur.execute(f"create index if not exists idx_{SCHEMA_NAME}_task_sets_user_id on {SCHEMA_NAME}.task_sets(user_id)")
    cur.execute(
        f"create index if not exists idx_{SCHEMA_NAME}_task_set_tasks_task_set_id on {SCHEMA_NAME}.task_set_tasks(task_set_id)"
    )


def get_app_user_columns(cur):
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = %s and table_name = 'app_user'
        """,
        (SCHEMA_NAME,),
    )
    return {row[0] for row in cur.fetchall()}


def get_or_create_user(cur, bcrypt_module):
    columns = get_app_user_columns(cur)
    cur.execute(
        f"select id from {SCHEMA_NAME}.app_user where lower(username) = lower(%s) or lower(email) = lower(%s)",
        (APP_USER["username"], APP_USER["email"]),
    )
    row = cur.fetchone()
    hashed_password = hash_password(APP_USER["password"], bcrypt_module)

    if row:
        user_id = row[0]
        if "password_hash" in columns:
            cur.execute(
                f"""
                update {SCHEMA_NAME}.app_user
                set username = %s,
                    email = %s,
                    password_hash = %s,
                    updated_at = now()
                where id = %s
                """,
                (APP_USER["username"], APP_USER["email"], hashed_password, user_id),
            )
        elif "password" in columns:
            cur.execute(
                f"""
                update {SCHEMA_NAME}.app_user
                set username = %s,
                    email = %s,
                    password = %s
                where id = %s
                """,
                (APP_USER["username"], APP_USER["email"], APP_USER["password"], user_id),
            )
        else:
            cur.execute(
                f"""
                update {SCHEMA_NAME}.app_user
                set username = %s,
                    email = %s
                where id = %s
                """,
                (APP_USER["username"], APP_USER["email"], user_id),
            )
        return user_id

    if "password_hash" in columns:
        cur.execute(
            f"""
            insert into {SCHEMA_NAME}.app_user (username, email, password_hash)
            values (%s, %s, %s)
            returning id
            """,
            (APP_USER["username"], APP_USER["email"], hashed_password),
        )
        return cur.fetchone()[0]

    if "password" in columns:
        cur.execute(
            f"""
            insert into {SCHEMA_NAME}.app_user (username, email, password)
            values (%s, %s, %s)
            returning id
            """,
            (APP_USER["username"], APP_USER["email"], APP_USER["password"]),
        )
        return cur.fetchone()[0]

    cur.execute(
        f"""
        insert into {SCHEMA_NAME}.app_user (username, email)
        values (%s, %s)
        returning id
        """,
        (APP_USER["username"], APP_USER["email"]),
    )
    return cur.fetchone()[0]


def migrate_tasks(cur, user_id, tasks):
    inserted = 0
    for task in tasks:
        cur.execute(
            f"""
            insert into {SCHEMA_NAME}.tasks (
                id,
                user_id,
                title,
                category,
                total_units,
                completed_units,
                unit_name,
                estimate_seconds,
                spent_seconds,
                timer_started_at,
                notes,
                completed_at,
                dropped_at,
                created_at,
                updated_at
            )
            values (
                %(id)s,
                %(user_id)s,
                %(title)s,
                %(category)s,
                %(total_units)s,
                %(completed_units)s,
                %(unit_name)s,
                %(estimate_seconds)s,
                %(spent_seconds)s,
                %(timer_started_at)s,
                %(notes)s,
                %(completed_at)s,
                %(dropped_at)s,
                %(created_at)s,
                now()
            )
            on conflict (id) do update
            set user_id = excluded.user_id,
                title = excluded.title,
                category = excluded.category,
                total_units = excluded.total_units,
                completed_units = excluded.completed_units,
                unit_name = excluded.unit_name,
                estimate_seconds = excluded.estimate_seconds,
                spent_seconds = excluded.spent_seconds,
                timer_started_at = excluded.timer_started_at,
                notes = excluded.notes,
                completed_at = excluded.completed_at,
                dropped_at = excluded.dropped_at,
                created_at = excluded.created_at,
                updated_at = now()
            """,
            {
                "id": task["id"],
                "user_id": user_id,
                "title": task.get("title", "Untitled"),
                "category": task.get("category", "Custom"),
                "total_units": max(1, int(task.get("total_units", 1))),
                "completed_units": max(0, int(task.get("completed_units", 0))),
                "unit_name": task.get("unit_name", "steps"),
                "estimate_seconds": max(0, int(task.get("estimate_seconds", 0))),
                "spent_seconds": max(0, int(task.get("spent_seconds", 0))),
                "timer_started_at": task.get("timer_started_at"),
                "notes": task.get("notes", ""),
                "completed_at": task.get("completed_at"),
                "dropped_at": task.get("dropped_at"),
                "created_at": task.get("created_at"),
            },
        )
        inserted += 1
    return inserted


def migrate_task_sets(cur, user_id, task_sets):
    inserted_sets = 0
    inserted_set_tasks = 0

    for task_set in task_sets:
        cur.execute(
            f"""
            insert into {SCHEMA_NAME}.task_sets (
                id,
                user_id,
                title,
                notes,
                start_at,
                end_at,
                created_at,
                updated_at
            )
            values (
                %(id)s,
                %(user_id)s,
                %(title)s,
                %(notes)s,
                %(start_at)s,
                %(end_at)s,
                %(created_at)s,
                now()
            )
            on conflict (id) do update
            set user_id = excluded.user_id,
                title = excluded.title,
                notes = excluded.notes,
                start_at = excluded.start_at,
                end_at = excluded.end_at,
                created_at = excluded.created_at,
                updated_at = now()
            """,
            {
                "id": task_set["id"],
                "user_id": user_id,
                "title": task_set.get("title", "Untitled task set"),
                "notes": task_set.get("notes", ""),
                "start_at": task_set.get("start_at"),
                "end_at": task_set.get("end_at"),
                "created_at": task_set.get("created_at"),
            },
        )
        inserted_sets += 1

        cur.execute(f"delete from {SCHEMA_NAME}.task_set_tasks where task_set_id = %s", (task_set["id"],))

        for position, item in enumerate(task_set.get("tasks", [])):
            cur.execute(
                f"""
                insert into {SCHEMA_NAME}.task_set_tasks (
                    id,
                    task_set_id,
                    title,
                    category,
                    total_units,
                    completed_units,
                    unit_name,
                    notes,
                    position
                )
                values (
                    %(id)s,
                    %(task_set_id)s,
                    %(title)s,
                    %(category)s,
                    %(total_units)s,
                    %(completed_units)s,
                    %(unit_name)s,
                    %(notes)s,
                    %(position)s
                )
                """,
                {
                    "id": item["id"],
                    "task_set_id": task_set["id"],
                    "title": item.get("title", "Untitled"),
                    "category": item.get("category", "Custom"),
                    "total_units": max(1, int(item.get("total_units", 1))),
                    "completed_units": max(0, int(item.get("completed_units", 0))),
                    "unit_name": item.get("unit_name", "steps"),
                    "notes": item.get("notes", ""),
                    "position": position,
                },
            )
            inserted_set_tasks += 1

    return inserted_sets, inserted_set_tasks


def main():
    psycopg = require_dependency("psycopg", "psycopg[binary]")
    bcrypt_module = require_dependency("bcrypt")

    tasks, task_sets = load_source_data()

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ensure_schema(cur)
                user_id = get_or_create_user(cur, bcrypt_module)
                task_count = migrate_tasks(cur, user_id, tasks)
                task_set_count, task_set_task_count = migrate_task_sets(cur, user_id, task_sets)
            conn.commit()
    except Exception as error:
        raise SystemExit(f"Migration failed: {error}") from error

    print(f"Source file: {JSON_PATH}")
    print(f"Schema: {SCHEMA_NAME}")
    print(f"App user: {APP_USER['username']} ({APP_USER['email']})")
    print(f"Migrated {task_count} standalone tasks")
    print(f"Migrated {task_set_count} task sets")
    print(f"Migrated {task_set_task_count} task-set tasks")


if __name__ == "__main__":
    main()
