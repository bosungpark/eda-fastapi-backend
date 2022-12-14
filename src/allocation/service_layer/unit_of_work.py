import abc

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from allocation import config
from allocation.adapters.repository import AbstractRepository, SqlAlchemyProductRepository


DEFAULT_SESSION_FACTORY = sessionmaker(bind=create_engine(
    config.get_postgres_uri(),
    isolation_level="REPEATABLE READ",
))


class AbstractUnitOfWork(abc.ABC):
    products: AbstractRepository

    def __exit__(self, *args):
        self.rollback()

    def __enter__(self):
        return self

    def commit(self):
        self._commit()

    def collect_new_events(self):
        for product in self.products.seen:
            while product.events:
                yield product.events.popleft()

    @abc.abstractmethod
    def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory=session_factory

    def __enter__(self):
        self.session : Session= self.session_factory()
        self.products = SqlAlchemyProductRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()