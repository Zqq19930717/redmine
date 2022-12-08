#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/22 18:41
@DESC : project后台View所用forms

'''

from django import forms
from django.core.validators import ValidationError

from app_web.forms.bootstrap import BootstrapForm
from app_web.models import Project
from app_web.forms.widgets import ColorRadioSelect

class ProjectModelForm(BootstrapForm, forms.ModelForm):
    bootstrap_class_exclude = ["color"]
    class Meta:
        model = Project
        fields = ['name', 'color', 'desc']
        # 将desc显示为文本输入框，方式一
        # desc = forms.CharField(widget=forms.Textarea)
        # 将desc显示为文本输入框，方式二
        widgets = {
            "desc" : forms.Textarea(),
            "color" : ColorRadioSelect(attrs={'class': "color-radio"})    #自定义的颜色选择样式
        }

    def __init__(self, request, *args, **kwargs):
        super(ProjectModelForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_name(self):
        # 验证当前用户创建的项目名不能和其已创建名字相同
        project_name = self.cleaned_data.get("name")
        exists = Project.objects.filter(name= project_name, creator=self.request.redmine.user).exists()
        if exists:
            raise ValidationError("项目名重复。")
        # 验证当前用户是否超过创建个数限制
        # 获取允许创建的最大项目个数
        max_projects = self.request.redmine.price_policy.project_num
        # 获取用户已创建的项目个数
        cur_projects = Project.objects.filter(creator=self.request.redmine.user).count()
        if cur_projects >= max_projects:
            raise ValidationError("已超过项目数量限制，请升级项目套餐!")
        return project_name