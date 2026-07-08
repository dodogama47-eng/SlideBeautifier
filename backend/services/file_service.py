from pathlib import Path
import shutil
from fastapi import UploadFile


class FileService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload_file(
        self,
        upload_file: UploadFile,
        task_id: str,
        label: str
    ) -> Path:
        suffix = Path(upload_file.filename or "").suffix
        if not suffix:
            suffix = ".pptx"

        file_path = self.upload_dir / f"{task_id}_{label}{suffix}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        return file_path