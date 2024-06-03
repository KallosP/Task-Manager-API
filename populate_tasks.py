import sqlalchemy
import os
import dotenv
from faker import Faker
import numpy as np
import random
import pytz
from enum import Enum
from datetime import time

def database_connection_url():
    dotenv.load_dotenv()
    DB_USER: str = os.environ.get("POSTGRES_USER")
    DB_PASSWD = os.environ.get("POSTGRES_PASSWORD")
    DB_SERVER: str = os.environ.get("POSTGRES_SERVER")
    DB_PORT: str = os.environ.get("POSTGRES_PORT")
    DB_NAME: str = os.environ.get("POSTGRES_DB")
    return f"postgresql://{DB_USER}:{DB_PASSWD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"

class StatusEnum(str, Enum):
    complete = "complete"
    in_progress = "in progress"
    not_started = "not started"

class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

# Create a new DB engine based on our connection string
engine = sqlalchemy.create_engine(database_connection_url(), use_insertmanyvalues=True)

with engine.begin() as conn:
    conn.execute(sqlalchemy.text("""
    DROP TABLE IF EXISTS subtasks;
    DROP TABLE IF EXISTS tags;
    DROP TABLE IF EXISTS tasks;
    DROP TABLE IF EXISTS users;

    create table
    public.users (
        user_id bigint generated by default as identity,
        user_name text null default ''::text,
        password text null default ''::text,
        free_time time without time zone [] null,
        constraint users_pkey primary key (user_id)
    ) tablespace pg_default;

    create table
    public.tasks (
        task_id integer generated by default as identity,
        name text null default ''::text,
        description text null default ''::text,
        priority text null default ''::text,
        status text null default ''::text,
        start_date timestamp with time zone null,
        due_date timestamp with time zone null,
        end_date timestamp with time zone null,
        user_id bigint null,
        estimated_time bigint null,
        constraint tasks_pkey primary key (task_id),
        constraint tasks_user_id_fkey foreign key (user_id) references users (user_id)
    ) tablespace pg_default;

    create table
    public.subtasks (
        subtask_id serial,
        task_id integer null,
        name text null,
        priority text null,
        due_date timestamp with time zone null,
        estimated_time integer null,
        weight integer null,
        user_id integer null,
        constraint subtasks_pkey primary key (subtask_id),
        constraint subtasks_task_id_fkey foreign key (task_id) references tasks (task_id),
        constraint subtasks_user_id_fkey foreign key (user_id) references users (user_id)
    ) tablespace pg_default;

    create table
    public.tags (
        tag_id bigint generated by default as identity,
        name text null default ''::text,
        user_id bigint null,
        task_id integer null,
        constraint tags_pkey primary key (tag_id),
        constraint tags_task_id_fkey foreign key (task_id) references tasks (task_id) on delete cascade,
        constraint tags_user_id_fkey foreign key (user_id) references users (user_id)
    ) tablespace pg_default;

    """))
    
# Creates ~1 mil rows in total
num_users = 10000
fake = Faker()
# Assuming every user would have anywhere from 10 to 30 tasks
tasks_sample_distribution = np.random.default_rng().integers(10, 30, num_users)
total_tasks = 0

# Create fake users with fake tasks
with engine.begin() as conn:
    print("creating fake users...")
    tasks = []
    tags = []
    subtasks = []
    for i in range(num_users):
        if (i % 10 == 0):
            print(i)
        
        name = fake.name()
        password = fake.password()
        # Generate random free times
        free_time = []
        # Generate 1 to 3 free time ranges
        for _ in range(random.randint(1, 4)):  
            start_time = time(hour=random.randint(0, 12), minute=random.randint(0, 59))
            end_time = time(hour=random.randint(start_time.hour+1, 23), minute=random.randint(0, 59))
            free_time.append([start_time, end_time])

        user_id = conn.execute(sqlalchemy.text("""
        INSERT INTO users (user_name, password, free_time)
        VALUES (:username, :password, :free_time) 
        RETURNING user_id;
        """), {"username": name, "password": password, "free_time": free_time}).scalar_one()

        num_tasks = tasks_sample_distribution[i]
        for j in range(num_tasks):
            total_tasks += 1

            task = {
                "name": fake.bs(),
                "description": fake.sentences(),
                "priority": random.choice(list(PriorityEnum)).value,
                "status": random.choice(list(StatusEnum)).value,
                "start_date": fake.date_time_between(start_date='-1y', end_date='now', tzinfo=pytz.timezone(fake.timezone())),
                "due_date": fake.date_time_between(start_date='-1y', end_date='now', tzinfo=pytz.timezone(fake.timezone())),
                "end_date": fake.date_time_between(start_date='-1y', end_date='now', tzinfo=pytz.timezone(fake.timezone())),
                "user_id": user_id,
                "estimated_time": random.randint(1, 30)
            }
            tasks.append(task)

            # Add a random number of tags (1-5) to the tags table
            for _ in range(random.randint(1, 6)):  
                tag = {
                    "name": fake.word(),
                    "user_id": user_id,
                    "task_id": total_tasks
                }
                tags.append(tag)

            # Insert random subtasks (1-5) related to the task
            for _ in range(random.randint(1, 6)):  
                subtask = {
                    "task_id": total_tasks,  
                    "name": task["name"] + " (SUBTASK)",
                    "priority": task["priority"],
                    "due_date": task["due_date"],
                    "estimated_time": task["estimated_time"],
                    "weight": random.randint(1, 10),
                    "user_id": user_id
                }
                subtasks.append(subtask)

    # Bulk insert tasks into tasks table
    conn.execute(sqlalchemy.text("""
    INSERT INTO tasks (name, description, priority, status, start_date, due_date, end_date, user_id, estimated_time) 
    VALUES (:name, :description, :priority, :status, :start_date, :due_date, :end_date, :user_id, :estimated_time);
    """), tasks)

    # Bulk insert tags into tags table
    conn.execute(sqlalchemy.text("""
    INSERT INTO tags (name, user_id, task_id)
    VALUES (:name, :user_id, :task_id);
    """), tags)

    # Bulk insert subtasks into subtasks table
    conn.execute(sqlalchemy.text("""
    INSERT INTO subtasks (task_id, name, priority, due_date, estimated_time, weight, user_id)
    VALUES (:task_id, :name, :priority, :due_date, :estimated_time, :weight, :user_id);
    """), subtasks)

    print("total tasks: ", total_tasks)