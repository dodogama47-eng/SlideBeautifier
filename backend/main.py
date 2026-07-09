from pathlib import Path
from uuid import uuid4
import traceback

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from services.file_service import FileService
from services.task_service import TaskService
from services.ppt_reader import PptReader
from services.ai_design_planner import AIDesignPlanner
from services.ppt_preview import PptPreviewService
from services.native_template_fill_service import NativeTemplateFillService


app = FastAPI(title="SlideBeautifier Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

file_service = FileService(UPLOAD_DIR)
task_service = TaskService()
ppt_reader = PptReader()
ai_design_planner = AIDesignPlanner()
ppt_preview_service = PptPreviewService()
template_fill_service = NativeTemplateFillService()


def get_task_result_dir(task_id: str) -> Path:
    result_dir = RESULT_DIR / task_id
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def get_analysis_dir(task_id: str) -> Path:
    analysis_dir = get_task_result_dir(task_id) / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir


def get_preview_dir(task_id: str, kind: str) -> Path:
    preview_dir = get_task_result_dir(task_id) / "preview" / kind
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir


def build_preview_urls(
    request: Request,
    task_id: str,
    kind: str
) -> list[str]:
    preview_dir = get_preview_dir(task_id, kind)

    files = sorted(
        preview_dir.glob("page_*.png"),
        key=lambda p: int(p.stem.replace("page_", ""))
    )

    return [
        str(
            request.url_for(
                "get_preview_image",
                task_id=task_id,
                kind=kind,
                image_name=file.name
            )
        )
        for file in files
    ]


def build_generate_response(
    request: Request,
    task_id: str
) -> dict:
    return {
        "task_id": task_id,
        "status": "completed",
        "download_url": str(
            request.url_for(
                "download_result",
                task_id=task_id
            )
        ),
        "original_preview_images": build_preview_urls(
            request=request,
            task_id=task_id,
            kind="original"
        ),
        "reference_preview_images": build_preview_urls(
            request=request,
            task_id=task_id,
            kind="reference"
        ),
        "beautified_preview_images": build_preview_urls(
            request=request,
            task_id=task_id,
            kind="beautified"
        )
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "connected",
        "engine": "native_template_fill_rewrite_v1"
    }


@app.post("/generate")
async def generate_presentation(
    request: Request,
    format_file: UploadFile = File(...),
    text_file: UploadFile = File(...)
):
    task_id = str(uuid4())

    if not format_file.filename or not format_file.filename.lower().endswith(".pptx"):
        raise HTTPException(
            status_code=400,
            detail="format_file must be .pptx"
        )

    if not text_file.filename or not text_file.filename.lower().endswith(".pptx"):
        raise HTTPException(
            status_code=400,
            detail="text_file must be .pptx"
        )

    try:
        reference_path = file_service.save_upload_file(
            format_file,
            task_id,
            "reference"
        )

        content_path = file_service.save_upload_file(
            text_file,
            task_id,
            "content"
        )

        reference_path = Path(reference_path)
        content_path = Path(content_path)

        if not reference_path.exists() or reference_path.stat().st_size == 0:
            raise HTTPException(
                status_code=400,
                detail="reference PPTX is empty"
            )

        if not content_path.exists() or content_path.stat().st_size == 0:
            raise HTTPException(
                status_code=400,
                detail="content PPTX is empty"
            )

        result_dir = get_task_result_dir(task_id)
        analysis_dir = get_analysis_dir(task_id)
        result_path = result_dir / "result.pptx"

        slide_library_path = analysis_dir / "slide_library.json"
        fill_plan_path = analysis_dir / "fill_plan.json"
        check_report_path = analysis_dir / "check_report.json"

        task = task_service.create_task(
            task_id=task_id,
            format_path=str(reference_path),
            text_path=str(content_path)
        )

        task["status"] = "processing"
        task["result_path"] = str(result_path)
        task["analysis_dir"] = str(analysis_dir)

        print("Step 1: extracting content slides...")
        content_slides = ppt_reader.extract_content_slides(content_path)

        if not content_slides:
            raise HTTPException(
                status_code=400,
                detail="No slides found in content PPTX"
            )

        print("Step 2: analyzing reference PPTX as native slide library...")
        slide_library = template_fill_service.analyze_reference(
            reference_path=reference_path,
            output_json_path=slide_library_path
        )

        print("Step 3: generating native fill_plan with AI...")

        try:
            fill_plan = ai_design_planner.generate_fill_plan(
                content_slides=content_slides,
                slide_library=slide_library
            )
        except Exception:
            print("AI fill planner failed:")
            traceback.print_exc()

            print("Using fallback fill plan...")
            fill_plan = ai_design_planner.build_fallback_fill_plan(
                content_slides=content_slides,
                slide_library=slide_library
            )

        template_fill_service.save_fill_plan(
            fill_plan=fill_plan,
            output_json_path=fill_plan_path
        )

        print("Step 3.5: checking fill_plan...")
        check_report = template_fill_service.check_fill_plan(
            slide_library=slide_library,
            fill_plan=fill_plan,
            output_json_path=check_report_path
        )

        task["fill_plan_path"] = str(fill_plan_path)
        task["slide_library_path"] = str(slide_library_path)
        task["check_report_path"] = str(check_report_path)
        task["check_summary"] = check_report.get("summary", {})

        print("Step 4: applying fill_plan to native PPTX template...")
        template_fill_service.apply_fill_plan(
            reference_path=reference_path,
            fill_plan=fill_plan,
            result_path=result_path,
            slide_library=slide_library
        )

        if not result_path.exists() or result_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500,
                detail="Generated result PPTX is empty"
            )

        print("Step 5: generating preview images...")

        try:
            ppt_preview_service.render_pptx_to_images(
                pptx_path=content_path,
                output_dir=get_preview_dir(task_id, "original")
            )

            ppt_preview_service.render_pptx_to_images(
                pptx_path=reference_path,
                output_dir=get_preview_dir(task_id, "reference")
            )

            ppt_preview_service.render_pptx_to_images(
                pptx_path=result_path,
                output_dir=get_preview_dir(task_id, "beautified")
            )

        except Exception:
            print("Preview generation failed:")
            traceback.print_exc()
            task["preview_error"] = "Preview generation failed."

        task["status"] = "completed"

        print("Done.")

        return build_generate_response(
            request=request,
            task_id=task_id
        )

    except HTTPException:
        raise

    except Exception as e:
        print("Generation failed with exception:")
        traceback.print_exc()

        existing_task = task_service.get_task(task_id)

        if existing_task is not None:
            existing_task["status"] = "failed"
            existing_task["error"] = str(e)

        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )


@app.get("/preview/{task_id}/{kind}/{image_name}", name="get_preview_image")
def get_preview_image(
    task_id: str,
    kind: str,
    image_name: str
):
    if kind not in ["original", "reference", "beautified"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid preview type"
        )

    image_path = get_preview_dir(task_id, kind) / image_name

    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Preview image not found"
        )

    return FileResponse(
        path=image_path,
        media_type="image/png"
    )


@app.get("/download/{task_id}", name="download_result")
def download_result(task_id: str):
    task = task_service.get_task(task_id)

    if task is not None:
        result_path = Path(task.get("result_path", ""))
    else:
        result_path = RESULT_DIR / task_id / "result.pptx"

    if not result_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Result file not found"
        )

    if result_path.stat().st_size == 0:
        raise HTTPException(
            status_code=500,
            detail="Result file is empty"
        )

    return FileResponse(
        path=result_path,
        filename=f"SlideBeautifier_{task_id}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = task_service.get_task(task_id)

    if task is None:
        result_path = RESULT_DIR / task_id / "result.pptx"

        if result_path.exists():
            return {
                "task_id": task_id,
                "status": "completed",
                "result_path": str(result_path),
                "download_url": f"/download/{task_id}"
            }

        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return task