#!/usr/bin/env python
# -*- coding: utf-8 -*-

from models import User
User.create_table()
u = User(name='Test', email='test@example.com', password='1234567890', image='about:blank')

u.insert()