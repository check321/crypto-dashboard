from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.logging import logger

class SchedulerService:
    _instance = None
    _scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._scheduler = AsyncIOScheduler()
        return cls._instance

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler stopped")

    def add_job(self, func, trigger, **kwargs):
        return self._scheduler.add_job(func, trigger, **kwargs)

    def get_job(self, job_id):
        return self._scheduler.get_job(job_id)

    def remove_job(self, job_id):
        return self._scheduler.remove_job(job_id)

    def reschedule_job(self, job_id, trigger, **trigger_args):
        return self._scheduler.reschedule_job(job_id, trigger=trigger, **trigger_args)
    
    def get_jobs(self):
        return self._scheduler.get_jobs()
    