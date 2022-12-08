#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/19 12:39
@DESC : redmine网站项目视图

'''
import time

from django.shortcuts import render,redirect,HttpResponse
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import View
from app_web.forms.project import ProjectModelForm
from app_web.models import Project,ProjectUser,IssuesType,Module
from utils.tencent.cos import create_bucket

class project_list(View):
    """ 项目首页 """
    def get(self, request):
        # GET请求查看项目列表
        """
        1. 从数据库中获取两部分数据
            我创建的所有项目：已星标、未星标
            我参与的所有项目：已星标、未星标
        2. 提取已星标
            列表 = 循环 [我创建的所有项目] + [我参与的所有项目] 把已星标的数据提取

        得到三个列表：星标、创建、参与
        """
        project_dict = {'star': [], 'my': [], 'join': []}
        # 筛选出当前用户创建的所有项目
        my_project_list = Project.objects.filter(creator=request.redmine.user)
        for row in my_project_list:
            if row.star:
                project_dict['star'].append({"value": row, 'type': 'my'})
            else:
                project_dict['my'].append(row)
        # 筛选出当前用户参与的项目
        join_project_list = ProjectUser.objects.filter(user=request.redmine.user)
        for item in join_project_list:
            if item.star:   # 不是append item, 而是apeend ProjectUser里的外键project
                project_dict['star'].append({"value": item.project, 'type': 'join'})
            else:
                project_dict['join'].append(item.project)
        form = ProjectModelForm(request=request)
        return render(request, "app_web/project_list.html", {"form": form, "project_dict": project_dict})

    def post(self, request):
        """ 新建项目 ajax弹出添加对话框"""
        form = ProjectModelForm(data=request.POST, request=request)
        if form.is_valid():
            project_name = form.cleaned_data.get("name")
            # 为项目创建一个桶(每个项目创建一个桶就方便每个项目上传的图片单独管理)，桶名：手机号-时间-桶的后缀ID
            bucket = "{0}-{1}-{2}-1312799721".format(project_name, request.redmine.user.mobile_phone, str(int(time.time())))
            region = "ap-nanjing"
            create_bucket(bucket=bucket, region=region)
            # 将桶和区域写入数据库
            form.instance.region = region
            form.instance.bucket = bucket
            # 验证通过：用户提交了项目名 + 颜色 + 描述，由于Project表use_space，star，join_count有默认值可不加，但是creator需要有数据一并保存入数据库
            form.instance.creator = request.redmine.user  # 可以思考下设计表格时候哪些可以给默认值，哪些不能给默认值
            instance = form.save()

            # 为每个新创建的项目创建初始Issue 类型
            issue_type_object_list = []
            for issue_type in IssuesType.PROJECT_INIT_LIST:
                issue_type_object_list.append(IssuesType(title=issue_type, project=instance))
            IssuesType.objects.bulk_create(issue_type_object_list) # 一次性创建三个问题类型值

            # 为每个新创建的项目创建初始模块
            module_type_object_list = []
            for model_type in Module.MODULE_INIT_LIST:
                module_type_object_list.append(Module(title=model_type, project=instance))
            Module.objects.bulk_create(module_type_object_list)

            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False, "error": form.errors})

class project_star(View):
    """ 星标项目 """

    def get(self, request, project_type, project_id):
        if project_type == "my":
            # 如果是当前用户创建的项目，找到该项目，并将项目star字段更新为True, 加了creator=request.redmine.user当前登录用户只允许更改自己创建的项目为星标，避免有人恶意url里改id，影响到别人的项目
            Project.objects.filter(id=project_id, creator=request.redmine.user).update(star=True)
            return redirect(reverse('project_list'))
        if project_type == "join":
            # 如果是当前用户参与的项目，找到该项目，并将项目star字段更新为True, project在ProjectUser表里是外键, 数据库会自动创建project_id字段关联到Project表
            ProjectUser.objects.filter(project_id=project_id, user=request.redmine.user).update(star=True)
            return redirect(reverse('project_list'))
        return HttpResponse("不支持的项目类型")

class project_unstar(View):
    """ 取消星标项目 """

    def get(self, request, project_type, project_id):
        if project_type == "my":
            # 如果是当前用户创建的项目，找到该项目，并将项目star字段更新为False, 加了creator=request.redmine.user当前登录用户只允许更改自己创建的项目为星标，避免有人恶意url里改id，影响到别人的项目
            Project.objects.filter(id=project_id, creator=request.redmine.user).update(star=False)
            return redirect(reverse('project_list'))
        if project_type == "join":
            # 如果是当前用户参与的项目，找到该项目，并将项目star字段更新为False, project在ProjectUser表里是外键, 数据库会自动创建project_id字段关联到Project表
            ProjectUser.objects.filter(project_id=project_id, user=request.redmine.user).update(star=False)
            return redirect(reverse('project_list'))
        return HttpResponse("不支持的项目类型")