import os
import uuid
import shutil
import asyncio
from typing import Optional, List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI()

UPLOAD_DIR = "uploads"
RESULT_DIR = "results"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


class TaskStatus(BaseModel):
    taskId: str
    status: str
    progress: int
    previewImages: List[str]
    downloadUrl: Optional[str]
    message: Optional[str]


tasks: Dict[str, dict] = {}


app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")


@app.get("/api/health")
def health_check():
    return {
        "status": "ok"
    }


@app.post("/api/beautify")
async def beautify_slides(
    background_tasks: BackgroundTasks,
    original_file: UploadFile = File(...),
    style_file: UploadFile = File(...)
):
    if not original_file.filename.lower().endswith(".pptx"):
        raise HTTPException(
            status_code=400,
            detail="original_file must be .pptx"
        )

    if not style_file.filename.lower().endswith(".pptx"):
        raise HTTPException(
            status_code=400,
            detail="style_file must be .pptx"
        )

    task_id = str(uuid.uuid4())

    upload_task_dir = os.path.join(UPLOAD_DIR, task_id)
    result_task_dir = os.path.join(RESULT_DIR, task_id)

    os.makedirs(upload_task_dir, exist_ok=True)
    os.makedirs(result_task_dir, exist_ok=True)

    original_path = os.path.join(upload_task_dir, "original.pptx")
    style_path = os.path.join(upload_task_dir, "style.pptx")

    with open(original_path, "wb") as buffer:
        shutil.copyfileobj(original_file.file, buffer)

    with open(style_path, "wb") as buffer:
        shutil.copyfileobj(style_file.file, buffer)

    tasks[task_id] = {
        "taskId": task_id,
        "status": "processing",
        "progress": 0,
        "previewImages": [],
        "downloadFile": None,
        "message": None
    }

    background_tasks.add_task(
        process_task,
        task_id,
        original_path,
        style_path,
        result_task_dir
    )

    return {
        "taskId": task_id,
        "status": "processing"
    }


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str, request: Request):
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task = tasks[task_id]

    base_url = str(request.base_url).rstrip("/")

    download_url = None
    if task["downloadFile"] is not None:
        download_url = f"{base_url}/results/{task_id}/result.pptx"

    preview_images = [
        f"{base_url}/results/{task_id}/{image_name}"
        for image_name in task["previewImages"]
    ]

    return {
        "taskId": task["taskId"],
        "status": task["status"],
        "progress": task["progress"],
        "previewImages": preview_images,
        "downloadUrl": download_url,
        "message": task["message"]
    }


async def process_task(
    task_id: str,
    original_path: str,
    style_path: str,
    result_task_dir: str
):
    try:
        tasks[task_id]["progress"] = 20
        await asyncio.sleep(1)

        tasks[task_id]["progress"] = 50
        await asyncio.sleep(1)

        tasks[task_id]["progress"] = 80
        await asyncio.sleep(1)

        # 第一版先不真正美化 PPT
        # 先把 original.pptx 复制成 result.pptx
        result_path = os.path.join(result_task_dir, "result.pptx")
        shutil.copyfile(original_path, result_path)

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["downloadFile"] = "result.pptx"
        tasks[task_id]["previewImages"] = []

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["progress"] = 0
        tasks[task_id]["message"] = str(e)