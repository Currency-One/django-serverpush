# -*- coding: utf-8 -*-
import logging

from django.db import connection, DatabaseError

logger = logging.getLogger('serverpush')


def catch_exceptions(func):
    def wrapper(*arg, **kwarg):
        try:
            return func(*arg, **kwarg)
        except DatabaseError, e:
            logger.warning('Database connection failed, trying to recover: %s ' % e)
            connection.connection.close()
            connection.connection = None
            raise
        except Exception, e:
            logger.exception(e)
            raise e
    return wrapper
