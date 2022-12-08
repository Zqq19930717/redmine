#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/15 18:51
@DESC : django离线脚本

'''

import base     # 学习离线脚本要去看看base.py里的初始条件准备

from app_web.models import UserInfo
# 往数据库添加数据，需要django加载配置文件，连接数据库，然后增删改查，最后关闭数据库
UserInfo.objects.create(username="zqq", mobile_phone="1346665201", email="zhouquanquan@zhou.com", password="123456zhou")
