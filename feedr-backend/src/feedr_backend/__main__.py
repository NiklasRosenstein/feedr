
import click
import nr.proxy

from .app import app, init_app
from .config import Config
from .model import init_db

config: Config = nr.proxy.proxy[Config](lambda: click.get_current_context().obj['config'])  # type: ignore


@click.group()
@click.option('-c', '--config', 'config_file', default='config.yml')
@click.option('--create-tables', is_flag=True)
@click.pass_context
def cli(ctx: click.Context, config_file: str, create_tables: bool):
  ctx.ensure_object(dict)['config'] = Config.load(config_file)
  init_db(config.database.url, create_tables=create_tables)
  init_app(config)


@cli.command()
def start():
  app.run(port=8000, use_reloader=False)


if __name__ == '__main__':
  cli()  # pylint: disable-all
