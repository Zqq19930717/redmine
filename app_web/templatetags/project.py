#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/27 22:44
@Desc : inclusion tag展示

'''
from django.urls import reverse
from django.template import Library
from app_web.models import ProjectUser, Project

register = Library()

@register.inclusion_tag('inclusion/all_project_list.html')
def all_project_list(request):
    # 获取用户创建的所有项目
    my_project_list = Project.objects.filter(creator=request.redmine.user)
    # 获取用户参与的所有项目
    join_project_list = ProjectUser.objects.filter(user=request.redmine.user)
    return {"my":my_project_list, "join":join_project_list, "request": request}

@register.inclusion_tag('inclusion/manage_menu_list.html')
def manage_menu_list(request):
    data_list = [
        {"title": '概览', 'url': reverse('dashboard', kwargs={'project_id': request.redmine.project.id})},
        {"title": '问题', 'url': reverse('issues', kwargs={'project_id': request.redmine.project.id})},
        {"title": '统计', 'url': reverse('statistics', kwargs={'project_id': request.redmine.project.id})},
        {"title": 'wiki', 'url': reverse('wiki', kwargs={'project_id': request.redmine.project.id})},
        {"title": '文件', 'url': reverse('file', kwargs={'project_id': request.redmine.project.id})},
        {"title": '设置', 'url': reverse('setting', kwargs={'project_id': request.redmine.project.id})},
    ]
    for item in data_list:
        if request.path_info.startswith(item.get('url')):
            item["class"] = "active"
    return {'data_list': data_list}