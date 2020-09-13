
import contextlib
from typing import Iterator

import nr.proxy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ._base import Entity


Session = sessionmaker()
session = nr.proxy.threadlocal[Session](
  name=__name__ + '.session',
  error_message='({name}) No SqlAlchemy session is available. Ensure that you are using the '
                'make_session() context manager before accessing the global session proxy.',
)


def begin_session() -> None:
  nr.proxy.push(session, Session())


def end_session() -> None:
  nr.proxy.pop(session)


@contextlib.contextmanager
def session_context() -> Iterator[None]:
  begin_session()
  try:
    yield
  except:  # noqa
    session.rollback()
    raise
  else:
    session.commit()
  finally:
    end_session()


def init_db(db_url: str, echo: bool = False, create_tables: bool = False) -> None:
  engine = create_engine(db_url, echo=echo)
  Session.configure(bind=engine)
  if create_tables:
    Entity.metadata.create_all(engine)
