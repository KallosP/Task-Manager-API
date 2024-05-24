from fastapi import APIRouter, Depends
from src.api import auth
from src import database as db
import sqlalchemy
from pydantic import BaseModel

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    dependencies=[Depends(auth.get_api_key)],
)

class Tag(BaseModel):
    name: str = None

@router.post("/add")
def add_tag(user_id: int, task_id: int, tag: Tag):
    
    with db.engine.begin() as connection:
        # Check if task_id exists
        exists = connection.execute(sqlalchemy.text(
            """
            SELECT task_id
            FROM tasks
            WHERE task_id = :task_id AND user_id = :user_id
            """
            ), [{"task_id": task_id, "user_id": user_id}]).fetchone()

        if exists is None:
            return "ERROR: task_id not found"
        
        # Check if we already have a tag of the same name for a given task
        tag_exists = connection.execute(sqlalchemy.text(
            """
            SELECT tag_id
            FROM tags
            WHERE task_id = :task_id AND user_id = :user_id AND name = :tag
            """
            ), [{"task_id": task_id, "user_id": user_id, "tag": tag.name}]).fetchone()
        
        if tag_exists:
            return "ERROR: tag already exists for task"

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO tags (user_id, task_id, name)
            VALUES
            (:user_id, :task_id, :name)
            """
            ), [{"task_id": task_id, "user_id": user_id, "name": tag.name}])
    
    return "OK"

@router.post("/get")
def get_tags(user_id: int, task_id: int):

    with db.engine.begin() as connection:

        # Check if task_id exists
        exists = connection.execute(sqlalchemy.text(
            """
            SELECT task_id
            FROM tasks
            WHERE task_id = :task_id AND user_id = :user_id
            """
            ), [{"task_id": task_id, "user_id": user_id}]).fetchone()

        if exists is None:
            return "ERROR: task_id not found"
        
        tags = connection.execute(sqlalchemy.text(
            """
            SELECT DISTINCT name
            FROM tags
            WHERE task_id = :task_id AND user_id = :user_id
            """
            ), [{"task_id": task_id, "user_id": user_id}])
        
        result = []
        for tag in tags:
            result.append(tag[0])
        return result
    
class Tags(BaseModel):
    names: list[str] = None


@router.post("/remove")
def remove_tag(user_id: int, task_id: int, tags: Tags):

    with db.engine.begin() as connection:

        # Check if task_id exists
        exists = connection.execute(sqlalchemy.text(
            """
            SELECT task_id
            FROM tasks
            WHERE task_id = :task_id AND user_id = :user_id
            """
            ), [{"task_id": task_id, "user_id": user_id}]).fetchone()

        if exists is None:
            return "ERROR: task_id not found"
        
        deleted = connection.execute(sqlalchemy.text(
            """
            DELETE FROM tags
            WHERE task_id = :task_id AND user_id = :user_id
            AND name IN :names
            """
            ), [{"task_id": task_id, "user_id": user_id, "names": tuple(tags.names)}])
        
        if deleted.rowcount <= 0:
            return "ERROR: Could not delete, tag not found."
        
    return "OK: Tag successfully removed"
