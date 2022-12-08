#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/8/25 17:14
@DESC : 个人设置中心视图

'''

from django.views.generic import View
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse
from utils.tencent.cos import delete_bucket

from app_web import models
from app_web.forms.account import ModifyPasswordForm
from utils.encrypt import md5

class setting(View):
    """ 项目管理设置 """
    def get(self, request, project_id):
        return render(request, 'app_web/setting.html')


class delete(View):
    """ 删除项目已经对应的cos对象 """
    def get(self, request, project_id):
        """删除项目"""
        return render(request, 'app_web/setting_delete.html')

    def post(self, request, project_id):
        project_name = request.POST.get('project_name')
        if not project_name or project_name != request.redmine.project.name:
            return render(request, 'app_web/setting_delete.html', {'error': "项目名错误"})

        # 项目名写对了则删除（只有创建者可以删除）
        if request.redmine.user != request.redmine.project.creator:
            return render(request, 'app_web/setting_delete.html', {'error': "必须项目创建者删除项目"})

        # 1. 删除桶
        #       - 删除桶中的所有文件（找到桶中的所有文件 + 删除文件 )
        #       - 删除桶中的所有碎片（找到桶中的所有碎片 + 删除碎片 )
        #       - 删除桶
        # 2. 删除项目
        #       - 项目删除

        delete_bucket(request.redmine.project.bucket, request.redmine.project.region)
        models.Project.objects.filter(id=request.redmine.project.id).delete()

        return redirect(reverse("project_list"))

class modify_password(View):
    """ 修改密码视图 """
    def get(self, request, project_id):
        form = ModifyPasswordForm()
        return render(request, 'app_web/setting_password.html', {"form": form})

    def post(self, request, project_id):
        form = ModifyPasswordForm(data=request.POST)
        if form.is_valid():
            # 获取用户输入的原密码
            input_origin_password = md5(form.cleaned_data.get("origin_password"))
            # 获取数据库中的原密码
            origin_password_data = models.UserInfo.objects.filter(username=request.redmine.user.username, password=input_origin_password).exists()
            if origin_password_data:    # 数据库能搜到当前用户输入的密码
                # 给用户修改为新密码，并保存
                models.UserInfo.objects.filter(username=request.redmine.user.username).update(password=md5(form.cleaned_data.get("password")))
                request.session.flush()  # 将session中的数据清空即可注销登录
                return JsonResponse({"status": True, 'data': reverse('login')}) # 前端用res.data来定向到login页面
            else:
                form.add_error('origin_password', "原密码错误")
                return JsonResponse({"status": False, "error": form.errors})
        else:
            return JsonResponse({"status": False, "error": form.errors})
