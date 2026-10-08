import os
import psycopg
import json
import uuid

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "progressdesk",
    "user": "postgres",
    "password": os.environ.get("PROGRESSDESK_DB_PASSWORD", ""),
}
SCHEMA_NAME = "progressdesk"

def load_from_db(Task, TaskSet, TaskSetTask):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Get the single app user
                cur.execute(f"SELECT id FROM {SCHEMA_NAME}.app_user LIMIT 1")
                row = cur.fetchone()
                if not row:
                    return None, None
                user_id = row[0]

                # Load tasks
                cur.execute(f"SELECT * FROM {SCHEMA_NAME}.tasks WHERE user_id = %s", (user_id,))
                cols = [desc[0] for desc in cur.description]
                tasks_data = [dict(zip(cols, row)) for row in cur.fetchall()]
                
                # Convert datetime objects to string for the dataclass
                for td in tasks_data:
                    for k, v in td.items():
                        if hasattr(v, "isoformat"):
                            td[k] = v.isoformat()
                            
                tasks = [Task.from_dict(td) for td in tasks_data]

                # Load task sets
                cur.execute(f"SELECT * FROM {SCHEMA_NAME}.task_sets WHERE user_id = %s", (user_id,))
                set_cols = [desc[0] for desc in cur.description]
                sets_data = [dict(zip(set_cols, row)) for row in cur.fetchall()]

                # Load task set tasks
                cur.execute(f"SELECT tst.* FROM {SCHEMA_NAME}.task_set_tasks tst JOIN {SCHEMA_NAME}.task_sets ts ON tst.task_set_id = ts.id WHERE ts.user_id = %s ORDER BY tst.position", (user_id,))
                tst_cols = [desc[0] for desc in cur.description]
                tst_data = [dict(zip(tst_cols, row)) for row in cur.fetchall()]
                
                for sd in sets_data:
                    for k, v in sd.items():
                        if hasattr(v, "isoformat"):
                            sd[k] = v.isoformat()
                    sd["tasks"] = []
                    for tstd in tst_data:
                        if str(tstd["task_set_id"]) == str(sd["id"]):
                            # Convert any needed format
                            sd["tasks"].append(tstd)
                
                task_sets = [TaskSet.from_dict(sd) for sd in sets_data]
                
                return tasks, task_sets
    except Exception as e:
        print(f"DB Load Error: {e}")
        return None, None

def save_to_db(tasks, task_sets):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id FROM {SCHEMA_NAME}.app_user LIMIT 1")
                row = cur.fetchone()
                if not row:
                    return False
                user_id = row[0]
                
                # Delete existing and insert new (simplest sync strategy for the whole state)
                cur.execute(f"DELETE FROM {SCHEMA_NAME}.tasks WHERE user_id = %s", (user_id,))
                cur.execute(f"DELETE FROM {SCHEMA_NAME}.task_sets WHERE user_id = %s", (user_id,))
                
                for t in tasks:
                    d = t.to_dict()
                    cur.execute(
                        f"""INSERT INTO {SCHEMA_NAME}.tasks (id, user_id, title, category, total_units, completed_units, unit_name, estimate_seconds, spent_seconds, timer_started_at, notes, completed_at, dropped_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (d["id"], user_id, d.get("title", ""), d.get("category", "Custom"), d.get("total_units", 1), d.get("completed_units", 0), d.get("unit_name", "units"), d.get("estimate_seconds", 0), d.get("spent_seconds", 0), d.get("timer_started_at"), d.get("notes", ""), d.get("completed_at"), d.get("dropped_at"), d.get("created_at"))
                    )
                
                for ts in task_sets:
                    d = ts.to_dict()
                    cur.execute(
                        f"""INSERT INTO {SCHEMA_NAME}.task_sets (id, user_id, title, notes, start_at, end_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (d["id"], user_id, d.get("title", ""), d.get("notes", ""), d.get("start_at"), d.get("end_at"), d.get("created_at"))
                    )
                    position = 0
                    for tst in d.get("tasks", []):
                        cur.execute(
                            f"""INSERT INTO {SCHEMA_NAME}.task_set_tasks (id, task_set_id, title, category, total_units, completed_units, unit_name, notes, position)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (tst["id"], d["id"], tst.get("title", ""), tst.get("category", "Custom"), tst.get("total_units", 1), tst.get("completed_units", 0), tst.get("unit_name", "units"), tst.get("notes", ""), position)
                        )
                        position += 1
                conn.commit()
                return True
    except Exception as e:
        print(f"DB Save Error: {e}")
        return False
