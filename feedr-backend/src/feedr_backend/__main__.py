
import logging

import click
import nr.proxy

from .app import create_app
from .config import Config
from .model import init_db
from .model.file import LocalStorageManager, init_storage
from .task_worker import TaskWorker

logger = logging.getLogger(__name__)
config: Config = nr.proxy.proxy[Config](lambda: click.get_current_context().obj['config'])  # type: ignore


@click.group()
@click.option('-c', '--config', 'config_file', default='config.yml')
@click.option('--create-tables', is_flag=True)
@click.pass_context
def cli(ctx: click.Context, config_file: str, create_tables: bool):
  logging.basicConfig(level=logging.INFO)
  ctx.ensure_object(dict)['config'] = Config.load(config_file)
  init_db(config.database.url, create_tables=create_tables)
  init_storage(LocalStorageManager(config.media_directory))


@cli.command()
def start():
  task_worker = TaskWorker('main_task_worker')
  task_worker.start()
  try:
    app = create_app(config)
    app.run(port=8000, debug=config.debug)
  finally:
    logger.info('Stopping main task worker')
    task_worker.stop()
    task_worker.join()


@cli.command()
def tasks():
  from .model import session, session_context
  from .model.task import Task
  with session_context():
    #queue_task('some task', MyTask('Nik'))
    for task in Task.pending():
      print(task)
      #task.load().execute(logging)
      #task.status

if __name__ == '__main__':
  cli()  # pylint: disable-all
