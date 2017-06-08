#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import db

class Field(object):
    _count = 0
    def __init__(self, **kw):
        self.name = kw.get('name', None)
        self._default = kw.get('default', None)
        self.primary_key = kw.get('primary_key', False)
        self.nullable = kw.get('nullable', False)
        self.updatable = kw.get('updatable', True)
        self.insertable = kw.get('insertable', True)
        self.ddl = kw.get('ddl', '')
        self._order = Field._count
        Field._count = Field._count + 1

    #将类方法转换为只读属性
    #重新实现一个属性的setter和getter方法
    @property
    def default(self):
        d = self._default
        return d() if callable(d) else d

    def __str__(self):
        s = ['<%s:%s,%s,default(%s),' % (self.__class__.__name__, self.name, self.ddl, self._default)]
        self.nullable and s.append('N')
        self.updatable and s.append('U')
        self.insertable and s.append('I')
        s.append('>')
        return ''.join(s)

class StringField(Field):

    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'text'
        super(StringField, self).__init__(**kw)

class IntegerField(Field):

    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 0
        if not 'ddl' in kw:
            kw['ddl'] = 'integer'
        super(IntegerField, self).__init__(**kw)

class FloatField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 0.0
        if not 'ddl' in kw:
            kw['ddl'] = 'real'
        super(FloatField, self).__init__(**kw)

class BooleanField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 0
        if not 'ddl' in kw:
            kw['ddl'] = 'integer'
        super(BooleanField, self).__init__(**kw)

class TextField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'text'
        super(TextField, self).__init__(**kw)

class BlobField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'blob'
        super(BlobField, self).__init__(**kw)

def _gen_sql(table_name, mappings):
    pk = None
    sql = ['-- generating SQL for %s:' % table_name, 'create table `%s` (' % table_name]
    for f in sorted(mappings.values(), lambda x, y: cmp(x._order, y._order)):
        if not hasattr(f, 'ddl'):
            raise StandardError('no ddl in field "%s".' % n)
        ddl = f.ddl
        nullable = f.nullable
        if f.primary_key:
            pk = f.name
        sql.append(nullable and '  `%s` %s,' % (f.name, ddl) or '  `%s` %s not null,' % (f.name, ddl))
    sql.append('  primary key(`%s`)' % pk)
    sql.append(');')
    return '\n'.join(sql)


class ModelMetaclass(type):
    def __new__(cls, future_class_name, future_class_parents, future_class_attr):
        if future_class_name == 'Model':
            return type.__new__(cls, future_class_name, future_class_parents, future_class_attr)
        mappings = dict()
        primary_key = None
        for k,v in future_class_attr.iteritems():
            if isinstance(v, Field):
                if not v.name:
                    v.name = k
                if v.primary_key:
                    if primary_key:
                        raise TypeError('Cannot define more than 1 primary key in class: %s' % future_class_name)
                    if v.updatable:
                        logging.warning('NOTE: change primary key to non-updatable.')
                        v.updatable = False
                    if v.nullable:
                        logging.warning('NOTE: change primary key to non-nullable.')
                        v.nullable = False
                    primary_key = v
                mappings[k] = v
        if not primary_key:
            raise TypeError('Primary key not defined in class: %s' % future_class_name)
        for k in mappings.iterkeys():
            future_class_attr.pop(k)
        if not '__table__' in  future_class_attr:
            future_class_attr['__table__'] = future_class_name.lower()
        future_class_attr['__mappings__'] = mappings
        future_class_attr['__primary_key__'] = primary_key
        future_class_attr['__sql__'] = lambda self: _gen_sql(future_class_attr['__table__'], mappings)
        return type.__new__(cls, future_class_name, future_class_parents, future_class_attr)

class Model(dict):
    __metaclass__ = ModelMetaclass
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    #
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    @classmethod
    def get(cls, pk):
        d = db.select_one('select * from %s where %s = ? ' % (cls.__table__, cls.__primary_key__,), pk )
        #三元运算符解决方案== d?cls(**d):None
        return cls(**d) if d else None

    @classmethod
    def find_first(cls, where, *args):
        d = db.select_one('select * from %s ' % (cls.__table__, where, ), *args)
        return cls(**d) if d else None

    @classmethod
    def find_all(cls):
        L = db.select('select * from %s ' % (cls.__table__))
        return [cls(**d) for d in L]

    @classmethod
    def count_all(cls):
        return db.select_int('select count(*) from %s' % (cls.__table__))

    @classmethod
    def count_by(cls, where, *args):
        return db.select_int('select count(*) from %s ' % (cls.__table__, where, ), *args)

    @classmethod
    def create_table(cls):
        L = []
        for k,v in cls.__mappings__.iteritems():
            if v.primary_key:
                L.append('%s %s primary key' % (v.name, v.ddl))
            else:
                L.append('%s %s %s' % (v.name, v.ddl, 'null' if v.nullable else ' not null'))
        db.update('create table if not exists %s(%s)' % (cls.__table__, ','.join(L)))

    def update(self):
        L = []
        args = []
        for k,v in self.__mappings__.iteritems:
            if v.updatable:
                if hasattr(self, k):
                    arg = getattr(self, k)
                else:
                    arg = v.default
                    setattr(self, k, arg)
                L.append('%s=?' % k)
                args.append(arg)
        pk = self.__primary_key.name
        args.append(getattr(self, pk))
        db.update('update %s set %s where %s=?' % (self.__table__, ','.join(L), pk), *args)
        return self

    def delete(self):
        pk = self.__primary_key.name
        arg = getattr(self, pk)
        db.update('delete from %s where %s=?' % (self.__table__, pk), pk)
        return self

    def insert(self):
        params = {}
        for k,v in self.__mappings__.iteritems():
            if v.insertable:
                if not hasattr(self, k):
                    setattr(self, k, v.default)
                params[v.name] = getattr(self, k)
        db.insert('%s' % self.__table__, **params)
        return self




def insert(ta, **kw):

    db.insert(ta, **kw)



