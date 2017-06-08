import sqlite3, logging, threading, time, functools, uuid

class Dict(dict):
    def __init__(self, names=(), values=(), **kwargs):
        super(Dict, self).__init__(**kwargs)
        for k, v in zip(names, values):
            self[k] = v

        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

        def __setattr__(self, key, value):
            self[key] = value

class DBError(Exception):
    pass

class MultiColumnsError(Exception):
    pass

def next_id(t=None):
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)

def _profiling(start, sql=''):
    t = time.time() - start
    if t > 0.1:
        logging.warning('[PROFILING] [DB] %s: %s' % (t, sql))
    else:
        logging.info('[PROFILING] [DB] %s: %s' % (t, sql))

engine = None

class _Engine(object):
    def __init__(self, connect):
        self.__connect = connect

    def connect(self):
        return self.__connect()

def create_engine(user='', password='', database='' , host='' , port='' , **kw):
    global engine
    if engine is not None:
        raise DBError('Engine is already initialized.')
    engine = _Engine(lambda : sqlite3.connect('example.db'))
    logging.info('Init sqlite engine <%s> ok.' % hex(id(engine)))

class _LasyConnection(object):
    def __init__(self):
        self.connection = None

    def cursor(self):
        global engine
        if self.connection is None:
            self.connection = engine.connect()
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            connection = self.connection
           # self.connection = None
            connection.close()


class _DbCtx(threading.local):
    def __init__(self):
        self.connection = None
        self.transactions = 0

    def is_init(self):
        return not self.connection is None

    def init(self):
        self.connection = _LasyConnection()
        self.transactions = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        self.connection.cursor()

_db_ctx = _DbCtx()

class _ConnectionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()

def connection():
    return _ConnectionCtx()


def with_connection(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        with _ConnectionCtx():
            return func(*args, **kwargs)
    return _wrapper

class _TransactionCtx(object):
    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions + 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions - 1
        try:
            if _db_ctx.transactions == 0:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):
        global _db_ctx
        try:
            _db_ctx.connection.commit()
        except:
            _db_ctx.connection.rollback()
            raise

    def rollback(self):
        global _db_ctx
        _db_ctx.connection.rollback()

def transaction():
    return _TransactionCtx()

def with_transaction(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        _start = time.time()
        with _TransactionCtx():
            return func(*args, **kwargs)
        _profiling(_start)
    return _wrapper

def _select(sql, first, *args):
    global  _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names, values)
        return [Dict(names, x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()

@with_connection
def select_one(sql, *args):
    return _select(sql, True, *args)


@with_connection
def select_int(sql, *args):
    d = _select(sql, True, *args)
    if len(d)!=1:
        raise MultiColumnsError('Except only one column.')
    return d.values()[0]

@with_connection
def select(sql, *args):
    return _select(sql, False, *args)

@with_connection
def _update(sql, *args):
    global _db_ctx
    cursor = None
    #sql = sql.replace('?', '%s')
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transactions==0:
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()

def insert(table, **kw):
    cols, args = zip(*kw.iteritems())
    sql = 'insert into %s (%s) values (%s)' % (
    table, ','.join(['%s' % col for col in cols]), ','.join(['?' for i in range(len(cols))]))
    return _update(sql, *args)

def update(sql, *args):
    return _update(sql, *args)



create_engine()
#update('drop table if exists user')
#update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
#kw = {'name': 'Test', 'admin': 0, 'created_at': 1496910289.864138, 'email': 'test@example.com', 'id': '0014969102898646452640faadb40f885c177fee7799211001', 'password': '1234567890', 'image': 'about:blank'}
#insert('users', **kw)


