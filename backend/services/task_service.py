from datetime import datetime


class TaskService:
    def __init__(self):
        self.tasks = {}

    def create_task(
        self,
        task_id: str,
        format_path: str,
        text_path: str
    ):
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": "uploaded",
            "format_path": format_path,
            "text_path": text_path,
            "result_path": None,
            "created_at": datetime.now().isoformat()
        }

        return self.tasks[task_id]

    def get_task(self, task_id: str):
        return self.tasks.get(task_id)