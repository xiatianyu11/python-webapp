#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

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
        for k,v in future_class_attr.iteritems:
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
        if not primary_key
            raise TypeError('Primary key not defined in class: %s' % future_class_name)
        for k in mappings.iterkeys():
            future_class_attr.pop(k)
        if not '__table__' in  future_class_attr:
            future_class_attr['__table__'] = future_class_name.lower()
        future_class_attr['__mappings__'] = mappings
        future_class_attr['__primary_key__'] = primary_key
        future_class_attr['__sql__'] = lambda self: _gen_sql(future_class_attr['__table__'], mappings)
        return type.__new__(cls, future_class_name, future_class_parents, future_class_attr)






