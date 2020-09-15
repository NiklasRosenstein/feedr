
import logging
from typing import cast

import click
import nr.proxy

from .app import create_app
from .config import Config
from .model import init_db
from .model.file import LocalStorageManager, init_storage
from .model.rss import load_feed, UpdateRssFeedsTask
from .model.task import queue_task
from .task_worker import BackgroundDispatcher, TaskWorker

logger = logging.getLogger(__name__)
config: Config = nr.proxy.proxy[Config]()  # type: ignore


@click.group()
@click.option('-c', '--config', 'config_file', default='config.yml')
@click.option('--create-tables', is_flag=True)
@click.pass_context
def cli(ctx: click.Context, config_file: str, create_tables: bool):
  logging.basicConfig(level=logging.INFO)
  nr.proxy.set_value(cast(nr.proxy.proxy, config), Config.load(config_file))
  init_db(config.database.url, create_tables=create_tables)
  init_storage(LocalStorageManager(config.media_directory))


@cli.command()
def start():
  task_worker = TaskWorker('main_task_worker')
  dispatcher = BackgroundDispatcher()

  try:
    task_worker.start()
    dispatcher.start()

    dispatcher.push_recurring(
      config.rss.update_interval.total_seconds(),
      lambda: queue_task('Update RSS Feeds', UpdateRssFeedsTask(config.rss.update_interval)))

    app = create_app(config)
    app.run(port=8000, debug=config.debug)
  finally:
    logger.info('Stopping main task worker')
    task_worker.stop()
    dispatcher.stop()
    task_worker.join()
    dispatcher.join()



@cli.command()
@click.argument('url')
def ingest(url):
  from .model import session
  from .model.rss import Feed, Atom, Article

  load_feed(url)
  session.commit()


if __name__ == '__main__':
  cli()  # pylint: disable-all
