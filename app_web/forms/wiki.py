#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/28 15:21
@DESC : wiki添加文档forms

'''

from django import forms
from app_web.models import Wiki
from app_web.forms.bootstrap import BootstrapForm

class WikiModelForm(BootstrapForm, forms.ModelForm):
    class Meta:
        model = Wiki
        exclude = ["project", 'depth']

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        init_choices_list = [("", "请选择"),]
        data_list = Wiki.objects.filter(project = request.redmine.project).values_list("id", "title")
        init_choices_list.extend(data_list)
        self.fields["parent"].choices = init_choices_list

