
import datetime
import hashlib
import uuid
from typing import List, Optional

import feedparser
import requests
from databind.core import datamodel
from nr.parsing.date import Duration
from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Table
from sqlalchemy.orm import backref, relationship

from ._base import Entity, instance_getter
from ._session import session
from .task import BaseTask, queue_task
from .user import User


class Feed(Entity):
  """
  Represents a single RSS feed URL. Multiple users may subscribe to the same feed, which is
  modeled using this entity. However, every user may have their own preferences for the feed
  (e.g. it's name) which is stored in the #Subscription model.
  """

  __tablename__ = __name__ = '.Feed'
  id = Column(String, primary_key=True)
  url = Column(String, unique=True, nullable=False)

  get = instance_getter['Feed']()

  def __init__(self, **kwargs):
    super().__init__(id=str(uuid.uuid4()), **kwargs)


class Atom(Entity):
  __tablename__ = __name__ + '.Atom'
  id = Column(String, ForeignKey(Feed.id), primary_key=True)
  feed = relationship(Feed, backref=backref('atom', uselist=False), uselist=False)
  hash = Column(String, nullable=False)
  last_updated = Column(DateTime, nullable=False)
  title = Column(String, nullable=False)
  subtitle = Column(String, nullable=True)
  self_link = Column(String, nullable=True)
  link = Column(String, nullable=True)
  image_url = Column(String, nullable=True)
  updated_formatted = Column(String, nullable=True)
  updated = Column(DateTime, nullable=True)
  rights = Column(String, nullable=False)
  language = Column(String, nullable=True)
  author_name = Column(String, nullable=True)
  author_email = Column(String, nullable=True)

  get = instance_getter['Atom']()


class Article(Entity):
  __tablename__ = __name__ + '.Article'
  id = Column(Integer, primary_key=True)
  atom_id = Column(Integer, ForeignKey(Atom.id), nullable=False)
  title = Column(String, nullable=False)
  summary = Column(String, nullable=False)
  link = Column(String, nullable=False)
  guid = Column(String, nullable=False)
  updated_formatted = Column(String, nullable=True)
  updated = Column(DateTime, nullable=True)
  published_formatted = Column(String, nullable=True)
  published = Column(DateTime, nullable=True)
  publisher = Column(String, nullable=True)

  atom = relationship(Atom, backref='articles', uselist=False)

  get = instance_getter['Article']()


class Tag(Entity):
  __tablename__ = __name__ + '.Tag'
  term = Column(String, primary_key=True)

  get = instance_getter['Tag']()


class Author(Entity):
  __tablename__ = __name__ + '.Author'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True)

  get = instance_getter['Author']()


_tag_to_article = Table(__name__ + '._TagToArticle', Entity.metadata,
  Column('tag_term', String, ForeignKey(Tag.term), primary_key=True),
  Column('article_id', Integer, ForeignKey(Article.id), primary_key=True),
)

_author_to_article = Table(__name__ + '._AuthorToArticle', Entity.metadata,
  Column('author_id', Integer, ForeignKey(Author.id)),
  Column('article_id', Integer, ForeignKey(Article.id)),
)

Article.tags = relationship(Tag, back_populates='articles', secondary=_tag_to_article)
Tag.articles = relationship(Article, back_populates='tags', secondary=_tag_to_article)

Article.authors = relationship(Author, back_populates='articles', secondary=_author_to_article)
Author.articles = relationship(Article, back_populates='authors', secondary=_author_to_article)


def load_feed(feed_url: str) -> None:
  response = requests.get(feed_url)
  response.raise_for_status()
  feed_hash = hashlib.md5(response.content).hexdigest()

  feed = Feed.get(url=feed_url).or_create()
  if feed.atom and feed.atom.hash == feed_hash:
    feed.atom.last_updated = datetime.datetime.utcnow()
    return

  data = feedparser.parse(response.text)

  # TODO: Take timezone from *_parsed into consideration.
  def to_dt(parsed: Optional[List[int]]) -> Optional[datetime.datetime]:
    if parsed is not None:
      return datetime.datetime(*parsed[:6])  # type: ignore
    return None

  atom = Atom.get(id=feed.id).create_or_update(
    last_updated=datetime.datetime.utcnow(),
    hash=feed_hash,
    title=data['feed']['title'],
    subtitle=data['feed'].get('subtitle'),
    self_link=next((l for l in data['feed'].get('links', []) if l['rel'] == 'self'), {}).get('href'),  # type: ignore
    link=data['feed']['link'],
    image_url=data['feed'].get('image', {}).get('href'),
    updated_formatted=data['feed']['updated'],
    updated=to_dt(data['feed']['updated_parsed']),
    rights=data['feed']['rights'],
    language=data['feed'].get('language'),
    author_name=data['feed'].get('author_detail', {}).get('name'),
    author_email=data['feed'].get('author_detail', {}).get('email'),
  )

  for entry in data['entries']:
    article = Article.get(guid=entry['id']).create_or_update(
      atom_id=atom.id,
      title=entry['title'],
      summary=entry['summary'],
      link=entry['link'],
      updated_formatted=entry.get('updated'),
      updated=to_dt(entry.get('updated_parsed')),
      published_formatted=entry.get('published'),
      published=to_dt(entry.get('published_parsed')),
      publisher=entry.get('publisher'),
    )

    for author in entry.get('authors', []):
      Author.get(name=author['name']).or_create()

    for tag in entry.get('tags', []):
      Tag.get(term=tag['term']).or_create()


@datamodel
class UpdateRssFeedsTask(BaseTask):
  update_interval: Duration

  def execute(self):
    ok = True
    max_update_time = datetime.datetime.utcnow() - self.update_interval.as_timedelta()
    for atom in session.query(Atom).filter(Atom.last_updated < max_update_time):
      try:
        load_feed(atom.feed.url)
      except:
        logger.exception('Error updating feed %s', atom.feed)
        ok = False
    if not ok:
      raise RuntimeError('not all feeds have been updated correctly')
