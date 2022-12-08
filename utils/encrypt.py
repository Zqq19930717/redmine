#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   employee
@Author  ：  quanquanzhou    
@DateTime :  2022/6/26 17:42
@Desc : 密码加密

'''

import uuid
import hashlib
from django.conf import settings


def md5(password):
    # 一般会加盐 salt = "xxx", hashlib.md5(salt.encode('utf-8'), 也可以直接用django 的 SECRET_KEY
    hash_obj = hashlib.md5(settings.SECRET_KEY.encode('utf-8'))
    hash_obj.update(password.encode('utf-8'))
    return hash_obj.hexdigest()

def uid(string):
    data = "{}-{}".format(str(uuid.uuid4()), string)
    return md5(data)

