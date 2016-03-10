# coding=utf-8

from contextlib import ContextDecorator
from bs4 import BeautifulSoup


class BS4Parser(BeautifulSoup, ContextDecorator):
    def insert_before(self, successor):
        pass

    def insert_after(self, successor):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _ = exc_type, exc_val, exc_tb
        self.decompose()
