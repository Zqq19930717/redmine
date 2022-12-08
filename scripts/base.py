#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/19 12:15
@DESC : 用户封装django离线脚本的公共初始化部分，再次创建其它脚本时，只需要先import base即可

'''

import os
import sys
import django

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 找到当前py文件的绝对路径, 然后上一级目录，再上一级目录到了redmine根目录
sys.path.append(base_dir)   # 将根目录放到sys.path种，就不会找不到redmine模块了

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "redmine.settings")
django.setup()  # 读取键os.environ["DJANDO_SETTINGS_MODULE"] 获取到对应的值 "redmine.settings"