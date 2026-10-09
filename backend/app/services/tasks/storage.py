"""In-memory storage + background dispatcher for Cloud Tasks."""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import threading
import time
import logging

from .models import Queue, Task, QueueState, TaskState

logger = logging.getLogger(__name__)


class TasksStorage:
    def __init__(self):
        self._lock = threading.Lock()
        self.queues: Dict[str, Dict[str, Queue]] = {}  # scope -> queue_id -> Queue
        self._dispatcher_started = False

    def _scope(self, project_id: str, location: str) -> str:
        return f"{project_id}/{location}"

    def create_queue(self, project_id: str, location: str, queue_id: str) -> Queue:
        with self._lock:
            scope = self._scope(project_id, location)
            queues = self.queues.setdefault(scope, {})
            if queue_id in queues:
                raise ValueError(f"Queue '{queue_id}' already exists")
            queue = Queue(queue_id=queue_id, project_id=project_id, location=location)
            queues[queue_id] = queue
            return queue

    def get_queue(self, project_id: str, location: str, queue_id: str) -> Optional[Queue]:
        return self.queues.get(self._scope(project_id, location), {}).get(queue_id)

    def list_queues(self, project_id: str, location: str) -> List[Queue]:
        return list(self.queues.get(self._scope(project_id, location), {}).values())

    def delete_queue(self, project_id: str, location: str, queue_id: str) -> bool:
        scope = self._scope(project_id, location)
        with self._lock:
            if queue_id in self.queues.get(scope, {}):
                del self.queues[scope][queue_id]
                return True
            return False

    def pause_queue(self, project_id: str, location: str, queue_id: str) -> Optional[Queue]:
        queue = self.get_queue(project_id, location, queue_id)
        if queue:
            queue.state = QueueState.PAUSED
        return queue

    def resume_queue(self, project_id: str, location: str, queue_id: str) -> Optional[Queue]:
        queue = self.get_queue(project_id, location, queue_id)
        if queue:
            queue.state = QueueState.RUNNING
        return queue

    def create_task(
        self, project_id: str, location: str, queue_id: str,
        http_request: Dict, schedule_time: Optional[datetime] = None,
    ) -> Task:
        queue = self.get_queue(project_id, location, queue_id)
        if not queue:
            raise ValueError(f"Queue '{queue_id}' not found")
        with self._lock:
            task = Task(
                queue_id=queue_id,
                project_id=project_id,
                location=location,
                task_id=queue.new_task_id(),
                http_request=http_request,
                schedule_time=schedule_time or datetime.now(timezone.utc),
            )
            queue.tasks[task.task_id] = task
            return task

    def get_task(self, project_id: str, location: str, queue_id: str, task_id: str) -> Optional[Task]:
        queue = self.get_queue(project_id, location, queue_id)
        if not queue:
            return None
        return queue.tasks.get(task_id)

    def list_tasks(self, project_id: str, location: str, queue_id: str) -> List[Task]:
        queue = self.get_queue(project_id, location, queue_id)
        if not queue:
            return []
        return list(queue.tasks.values())

    def delete_task(self, project_id: str, location: str, queue_id: str, task_id: str) -> bool:
        queue = self.get_queue(project_id, location, queue_id)
        if not queue or task_id not in queue.tasks:
            return False
        with self._lock:
            del queue.tasks[task_id]
            return True

    def run_task_now(self, project_id: str, location: str, queue_id: str, task_id: str) -> Optional[Task]:
        task = self.get_task(project_id, location, queue_id, task_id)
        if not task:
            return None
        self._dispatch(task)
        return task

    def _dispatch(self, task: Task):
        """Attempt the task's HTTP request. Never raises; records result on the task."""
        import requests

        task.dispatch_count += 1
        task.state = TaskState.DISPATCHED
        url = task.http_request.get("url")
        if not url:
            task.state = TaskState.FAILED
            task.last_attempt_result = "missing url"
            return
        method = task.http_request.get("httpMethod", "POST")
        headers = task.http_request.get("headers", {})
        body = task.http_request.get("body")
        try:
            resp = requests.request(method, url, headers=headers, data=body, timeout=10)
            task.response_count += 1
            task.state = TaskState.SUCCEEDED if resp.ok else TaskState.FAILED
            task.last_attempt_result = f"HTTP {resp.status_code}"
        except Exception as e:
            task.state = TaskState.FAILED
            task.last_attempt_result = str(e)

    def _dispatcher_loop(self):
        while True:
            now = datetime.now(timezone.utc)
            for queues in list(self.queues.values()):
                for queue in list(queues.values()):
                    if queue.state != QueueState.RUNNING:
                        continue
                    for task in list(queue.tasks.values()):
                        if task.state == TaskState.SCHEDULED and task.schedule_time <= now:
                            try:
                                self._dispatch(task)
                            except Exception:
                                logger.exception("task dispatch failed")
            time.sleep(1)

    def start_dispatcher(self):
        if self._dispatcher_started:
            return
        self._dispatcher_started = True
        thread = threading.Thread(target=self._dispatcher_loop, daemon=True)
        thread.start()

    def get_stats(self) -> Dict[str, int]:
        total_queues = sum(len(q) for q in self.queues.values())
        total_tasks = sum(len(q.tasks) for qs in self.queues.values() for q in qs.values())
        return {"queues": total_queues, "tasks": total_tasks}


storage = TasksStorage()
