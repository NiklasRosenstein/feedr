
import contextlib
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as _Session
from sqlalchemy.orm import sessionmaker, scoped_session

from ._base import Entity


Session = sessionmaker()
session: _Session = scoped_session(Session)


@contextlib.contextmanager
def session_context() -> Iterator[None]:
  try:
    yield
  except:  # noqa
    session.rollback()
    raise
  else:
    session.commit()
  finally:
    session.remove()


def init_db(db_url: str, echo: bool = False, create_tables: bool = False) -> None:
  engine = create_engine(db_url, echo=echo)
  Session.configure(bind=engine)
  if create_tables:
    Entity.metadata.create_all(engine)
