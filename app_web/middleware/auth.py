#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/13 23:34
@Desc : 中间件

'''
import datetime

from django.conf import settings
from django.urls import reverse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from app_web.models import UserInfo, Transaction, ProjectUser, Project

class redmine():
    ''' 封装两个变量到redmine对象中 '''
    def __init__(self):
        self.user = None
        self.price_policy = None
        self.project = None

class AuthMiddleWare(MiddlewareMixin):

    def process_request(self, request):
        """ 登录成功时会往session里写入user_id, request.session["user_id"] = user_object.id
        如果用户已登录, 则在request中赋值, 前端页面可以依据request.redmine.user中是否有值来判断用户是否登录 """
        request.redmine = redmine()
        user_id = request.session.get('user_id', 0) # session中没找到的话，默认赋值一个0, id=0在数据库中是不存在的
        user_object = UserInfo.objects.filter(id=user_id).first()
        request.redmine.user = user_object

        # 白名单：没有登录也可以访问的页面
        # 排除哪些不需要登录就能访问的页面(例如登录页面, 避免去登录页面检测到未登录, 然后重定向回登录页面 如此循环往复的请求)
        # 获取当前用户访问的url，并判断是否在白名单中, request.path_info 可以获取到当前用户请求的URL /login/
        if request.path_info in settings.WHITE_REGEX_URL_LIST:
            return None     # return 就能继续往下执行了, 继续往后走去访问下一个中间件或者我们定义的View
        # 判断用户是否已经登录, 没登录就跳转回登录页面
        if not request.redmine.user:
            return redirect(reverse('login'))

        # 登录成功后，访问后台管理，获取当前用户可以访问的额度
        # 方式一：免费额度在交易记录中存储
        # 获取当前用户ID值最大（最近交易记录）, status=2代表已支付
        _object = Transaction.objects.filter(user=user_object, status=2).order_by("-id").first()

        # 判断支付信息是否已经到了结束时间
        current_datetime = datetime.datetime.now()
        if _object.end_datetime and _object.end_datetime < current_datetime:     # 免费额度的结束时间为空，得判断是否_object.end_datetime为空来过滤掉免费
            # 过期或者超过结束时间，设置为免费版
            _object = Transaction.objects.filter(user=user_object, status=2, price_policy__category=1).first()  # price_policy是Transaction里的ForeignKey, 可以跨表查询category=1得免费版
        # 将支付信息存放 request.transaction
        # request.transaction = _object
        request.redmine.price_policy = _object.price_policy
        """
        # 方式二：免费的额度存储配置文件
        # 获取当前用户ID值最大（最近交易记录）
        _object = models.Transaction.objects.filter(user=user_object, status=2).order_by('-id').first()

        if not _object:
            # 没有购买, 直接指定价格策略为个人免费版
            request.price_policy = models.PricePolicy.objects.filter(category=1, title="个人免费版").first()
        else:
            # 付费版
            current_datetime = datetime.datetime.now()
            if _object.end_datetime and _object.end_datetime < current_datetime:
                # 过期，设置价格策略为免费版
                request.price_policy = models.PricePolicy.objects.filter(category=1, title="个人免费版").first()
            else:
                request.price_policy = _object.price_policy
        """

    def process_view(self, request, view, args, kwargs):
        # print(args) #输出 ()
        # print(kwargs) #看起来像是和url的参数有关，输出 {'project_id': '7'}
        # 判断URL是否是以manage开头, 如果是则继续判断project_id
        if not request.path_info.startswith('/manage/'):
            return
        # project_id必须是我创建的或我参与的才能访问
        project_id = kwargs.get('project_id')

        # 是否当前用户创建的项目
        # process_view函数在process_request之后执行，这里已经有了request.redmine.user
        project_object = Project.objects.filter(creator=request.redmine.user,id=project_id).first()
        if project_object:
            # 是当前用户创建的项目，让其可访问
            request.redmine.project = project_object
            return

        # 是否当前用户参与的项目
        project_user_object = ProjectUser.objects.filter(user=request.redmine.user,project_id = project_id).first()
        if project_user_object:
            # 是当前用户参与的项目，让其可访问
            request.redmine.project = project_user_object.project
            return

        # 不是manage开头，不是当前用户创建的项目，也不是当前用户参与的项目，返回到项目展示列表
        return redirect(reverse('project_list'))