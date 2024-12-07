import os
import json
import uvicorn
from contextlib import asynccontextmanager

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, Body

from errors import ValidationError, FileError, NotFoundError


load_dotenv()

Users_File = os.getenv("Users_File", "users.json")
Tasks_File = os.getenv("Tasks_File", "tasks.json")


async def init_files():
    for file in [Users_File, Tasks_File]:
        if not os.path.exists(file):
            async with aiofiles.open(file, mode="w") as fs:
                await fs.write("[]")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App is starting up...")
    await init_files()
    yield
    print("App is shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "FastAPI is running..."}

async def read_file(file_path):
    try:
        async with aiofiles.open(file_path, mode="r") as fs:
            return json.loads(await fs.read())
    except FileError as e:
        raise e

async def write_file(file_path, data):
    try:
        async with aiofiles.open(file_path, mode="w") as fs:
            await fs.write(json.dumps(data, indent=4))
    except FileError as e:
        raise e


@app.get("/users")
async def get_users():
    return await read_file(Users_File)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    users = await read_file(Users_File)

    user = next((user for user in users if user["id"] == user_id), None)
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    return user

@app.post("/users")
async def create_user(name: str = Body(..., min_length=1), email: str = Body(..., regex=r"[^@]+@[^@]+\.[^@]+"), password: str = Body(..., min_length=6)):
    users = await read_file(Users_File)

    if any(user["email"] == email for user in users):
        raise ValidationError("Email already registered")

    user_id = max([user["id"] for user in users], default=0) + 1
    new_user = {"id": user_id, "name": name, "email": email, "password": password}
    users.append(new_user)

    await write_file(Users_File, users)
    return {"id": user_id, "name": name, "email": email}

@app.put("/users/{user_id}")
async def update_user(user_id: int, name: str = Body(None), email: str = Body(None), password: str = Body(None),):
    users = await read_file(Users_File)

    for user in users:
        if user["id"] == user_id:
            if name:
                user["name"] = name
            if email:
                if "@" not in email or "." not in email:
                    raise ValidationError("Invalid email format")
                user["email"] = email
            if password:
                if len(password) < 6:
                    raise ValidationError("Password must have at least 6 characters")
                user["password"] = password

            await write_file(Users_File, users)
            return user
    raise NotFoundError(f"User with ID {user_id} not found")

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    users = await read_file(Users_File)

    updated_users = [user for user in users if user["id"] != user_id]
    if len(updated_users) == len(users):
        raise NotFoundError(f"User with ID {user_id} not found")
    await write_file(Users_File, updated_users)
    return {"message": f"User with ID {user_id} deleted"}


async def validate_user(user_id):
    users = await read_file(Users_File)

    if not any(user["id"] == user_id for user in users):
        raise ValidationError(f"No user exists with ID {user_id}")

@app.get("/tasks")
async def get_tasks():
    return await read_file(Tasks_File)

@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    tasks = await read_file(Tasks_File)

    task = next((task for task in tasks if task["id"] == task_id), None)
    if not task:
        raise NotFoundError(f"Task with ID {task_id} not found")
    return task

@app.post("/tasks")
async def create_task(
    title: str = Body(..., min_length=1),
    description: str = Body(None),
    user_id: int = Body(None),):

    if user_id:
        await validate_user(user_id)

    tasks = await read_file(Tasks_File)
    task_id = max([task["id"] for task in tasks], default=0) + 1
    new_task = {"id": task_id, "title": title, "description": description, "user_id": user_id}
    tasks.append(new_task)

    await write_file(Tasks_File, tasks)
    return new_task

@app.put("/tasks/{task_id}")
async def update_task(task_id: int, title: str = Body(None), description: str = Body(None), user_id: int = Body(None),):
    tasks = await read_file(Tasks_File)

    for task in tasks:
        if task["id"] == task_id:
            if title:
                task["title"] = title
            if description is not None:
                task["description"] = description
            if user_id is not None:
                await validate_user(user_id)
                task["user_id"] = user_id

            await write_file(Tasks_File, tasks)
            return task
    raise NotFoundError(f"Task with ID {task_id} not found")

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    tasks = await  read_file(Tasks_File)

    updated_tasks = [task for task in tasks if task["id"] != task_id]
    if len(updated_tasks) == len(tasks):
        raise NotFoundError(f"Task with ID {task_id} not found")
    await write_file(Tasks_File, updated_tasks)
    return {"message": f"Task with ID {task_id} deleted"}


@app.post("/register")
async def register_user(name: str = Body(...), email: str = Body(..., regex=r"[^@]+@[^@]+\.[^@]+"), password: str = Body(..., min_length=6)):
    users = await read_file(Users_File)

    if any(user["email"] == email for user in users):
        raise ValidationError("Email already registered")

    user_id = max([user["id"] for user in users], default=0) + 1
    new_user = {"id": user_id, "name": name, "email": email, "password": password}
    users.append(new_user)

    await write_file(Users_File, users)
    return {"id": user_id, "name": name, "email": email}

@app.post("/login")
async def login(email: str = Body(..., regex=r"[^@]+@[^@]+\.[^@]+"), password: str = Body(...)):
    users = await read_file(Users_File)

    user = next((user for user in users if user["email"] == email and user["password"] == password), None)
    if not user:
        raise ValidationError("Invalid email or password")
    return {"message": "Login successful", "user_id": user["id"]}

if __name__ == "__main__":
    uvicorn.run("main:app",port=8000,reload = True)