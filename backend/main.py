from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from services.file_service import FileService
from services.task_service import TaskService
from services.ppt_reader import PptReader
from services.openai_service import OpenAIService
from services.ppt_writer import PptWriter

app = FastAPI(title="SlideBeautifier Backend")

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

file_service = FileService(UPLOAD_DIR)
task_service = TaskService()
ppt_reader = PptReader()
openai_service = OpenAIService()
ppt_writer = PptWriter()


@app.get("/")
def health_check():
    return {
        "status": "running",
        "message": "SlideBeautifier backend is running"
    }


@app.post("/generate")
async def generate_presentation(
        format_file: UploadFile = File(...),
        text_file: UploadFile = File(...)
):
    task_id = str(uuid4())

    if not format_file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="format_file must be .pptx")

    if not text_file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="text_file must be .pptx")

    format_path = file_service.save_upload_file(format_file, task_id, "format")
    text_path = file_service.save_upload_file(text_file, task_id, "text")

    extracted_text = ppt_reader.extract_all_text(text_path)

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No text found in text_file")

    slide_plan = openai_service.generate_slide_plan(extracted_text)

    result_path = RESULT_DIR / f"{task_id}_result.pptx"

    ppt_writer.write_slide_plan_to_template(
        template_path=format_path,
        slide_plan=slide_plan,
        result_path=result_path
    )

    task = task_service.create_task(
        task_id=task_id,
        format_path=str(format_path),
        text_path=str(text_path)
    )

    task["status"] = "completed"
    task["result_path"] = str(result_path)

    return {
        "task_id": task_id,
        "status": "completed",
        "download_url": f"/download/{task_id}"
    }


@app.get("/download/{task_id}")
def download_result(task_id: str):
    task = task_service.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    result_path = Path(task["result_path"])

    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=result_path,
        filename="result.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = task_service.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task