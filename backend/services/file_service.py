from pathlib import Path
import shutil
from fastapi import UploadFile


class FileService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

    def save_upload_file(
        self,
        upload_file: UploadFile,
        task_id: str,
        file_type: str
    ) -> Path:
        file_path = self.upload_dir / f"{task_id}_{file_type}.pptx"

        upload_file.file.seek(0)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        if not file_path.exists():
            raise FileNotFoundError(f"Upload file was not saved: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"Uploaded file is empty: {file_path}")

        print(f"Saved {file_type} file:", file_path)
        print(f"File size:", file_path.stat().st_size)

        return file_path