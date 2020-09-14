
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ._base import Entity
from .user import User


class RssFeed(Entity):
  """
  Represents a single RSS feed URL. Multiple users may subscribe to the same feed, which is
  modeled using this entity. However, every user may have their own preferences for the feed
  (e.g. it's name) which is stored in the #Subscription model.
  """

  __tablename__ = __name__ = '.RssFeed'

  id = Column(Integer, primary_key=True)
  url = Column(String, unique=True, nullable=False)


class Subscription(Entity):
  """
  Represents a user subscribing to an RSS feed.
  """

  rss_feed_id = Column(Integer, ForeignKey(RssFeed.id), primary_key=True)
  user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
  alias = Column(String, nullable=False)

  rss_feed = relationship(RssFeed, backref="subscriptions", uselist=False)
  user = relationship(User, backref="subscriptions", uselist=False)
