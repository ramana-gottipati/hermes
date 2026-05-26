import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hermes.scheduler")


def hello_world_job() -> None:
    log.info("hello from hermes scheduler — replace me with a real job")


def main() -> None:
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(hello_world_job, "interval", minutes=5, id="hello-world")
    log.info("hermes scheduler starting — jobs: %s", [j.id for j in scheduler.get_jobs()])
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("scheduler stopping")


if __name__ == "__main__":
    main()
