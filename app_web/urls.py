#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/7 22:49
@Desc : web app 子路由

'''

from django.urls import path,include, re_path
from app_web.views import account, home, project, wiki, file, setting, issues, dashboard, statistics

urlpatterns = [
    # 账户管理
    path('register/', account.register.as_view(), name="register"),
    path('login/sms/', account.login_sms.as_view(), name="login_sms"),
    path('login/', account.login.as_view(), name="login"),
    path('image/code/', account.image_code.as_view(), name="image_code"),
    path('send/sms/', account.send_sms.as_view(), name="send_sms"),
    path('logout/', account.logout.as_view(), name="logout"),

    # 主页管理
    path('index/', home.index.as_view(), name="index"),

    # 支付页面管理
    path('price/', home.price.as_view(), name='price'),
    re_path(r'^payment/(?P<policy_id>\d+)/$', home.payment.as_view(), name='payment'),
    path('pay/', home.pay.as_view(), name='pay'),
    path('pay/notify/', home.pay_notify.as_view(), name='pay_notify'),

    # 项目列表
    path('project/list/', project.project_list.as_view(), name="project_list"),
    re_path('project/star/(?P<project_type>\w+)/(?P<project_id>\d+)/', project.project_star.as_view(), name="project_star"),
    re_path('project/unstar/(?P<project_type>\w+)/(?P<project_id>\d+)/', project.project_unstar.as_view(), name="project_unstar"),

    # 项目管理
    # 一. 直白的写法
    # re_path('manage/(?P<project_id>\d+)/dashboard/', manage.dashboard.as_view(), name="dashboard"),
    # re_path('manage/(?P<project_id>\d+)/issue/', manage.issue.as_view(), name="issue"),
    # re_path('manage/(?P<project_id>\d+)/statistics/', manage.statistics.as_view(), name="statistics"),
    # re_path('manage/(?P<project_id>\d+)/file/', manage.file.as_view(), name="file"),
    # re_path('manage/(?P<project_id>\d+)/wiki/', wiki.wiki.as_view(), name="wiki"),
    # re_path('manage/(?P<project_id>\d+)/setting/', manage.setting.as_view(), name="setting"),
    # 二. url前面重复，可以用下面的写法
    re_path('manage/(?P<project_id>\d+)/', include([

        # wiki管理
        path('wiki/', wiki.wiki.as_view(), name="wiki"),
        path('wiki/add/', wiki.wiki_add.as_view(), name="wiki_add"),
        path('wiki/catalog/', wiki.wiki_catalog.as_view(), name="wiki_catalog"),
        re_path('wiki/delete/(?P<delete_id>\d+)', wiki.wiki_delete.as_view(), name="wiki_delete"),
        re_path('wiki/edit/(?P<edit_id>\d+)', wiki.wiki_edit.as_view(), name="wiki_edit"),
        path('wiki/upload/)', wiki.wiki_upload.as_view(), name="wiki_upload"),

        # 设置管理
        path('setting/', setting.setting.as_view(), name="setting"),
        path('setting/delete', setting.delete.as_view(), name="setting_delete"),
        path('setting/password', setting.modify_password.as_view(), name="modify_password"),

        # 文件管理
        path('file/', file.file.as_view(), name="file"),
        path('file/delete/', file.file_delete.as_view(), name="file_delete"),
        path('cos/credential/', file.cos_credential.as_view(), name='cos_credential'),
        path('file/post/', file.file_post.as_view(), name='file_post'),
        re_path('file/download/(?P<file_id>\d+)/$', file.file_download.as_view(), name='file_download'),

        # 问题管理
        path('issue/', issues.issues.as_view(), name="issues"),
        path('issues/invite/url/', issues.invite_url.as_view(), name='invite_url'),
        re_path('^issues/detail/(?P<issues_id>\d+)/$', issues.issues_detail.as_view(), name='issues_detail'),
        re_path('^issues/record/(?P<issues_id>\d+)/$', issues.issues_record.as_view(), name='issues_record'),
        re_path('^issues/change/(?P<issues_id>\d+)/$', issues.issues_change.as_view(), name='issues_change'),

        # 概览管理
        path('dashboard/', dashboard.dashboard.as_view(), name='dashboard'),
        path('dashboard/issues/chart/', dashboard.issues_chart.as_view(), name='issues_chart'),

        # 统计管理
        path('statistics/', statistics.statistics.as_view(), name='statistics'),
        path('statistics/priority/', statistics.statistics_priority.as_view(), name='statistics_priority'),
        path('statistics/project/user/', statistics.statistics_project_user.as_view(), name='statistics_project_user'),

    ], None)),
    re_path(r'^invite/join/(?P<code>\w+)/$', issues.invite_join.as_view(), name='invite_join'),

]