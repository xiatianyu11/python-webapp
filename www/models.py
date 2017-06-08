#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time, uuid

from transwarp.db import next_id
from transwarp.orm import Model, StringField, BooleanField, FloatField, TextField, insert


class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, updatable=False, default=next_id)
    email = StringField(updatable=False)
    password = StringField()
    admin = BooleanField()
    name = StringField()
    image = StringField()
    created_at = FloatField(updatable=False, default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, updatable=False, default=next_id)
    user_id = StringField(updatable=False)
    user_name = StringField()
    user_image = StringField()
    name = StringField()
    summary = StringField()
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, updatable=False, default=next_id)
    blog_id = StringField(updatable=False)
    user_id = StringField(updatable=False)
    user_name = StringField()
    user_image = StringField()
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)



