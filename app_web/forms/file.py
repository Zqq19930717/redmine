#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/8/11 17:22
@DESC : 文件管理的modelform

'''

from django import forms
from django.core.exceptions import ValidationError

from app_web.forms.bootstrap import BootstrapForm
from app_web.models import FileRepository
from utils.tencent.cos import check_file

class folderModelForm(BootstrapForm, forms.ModelForm):
    class Meta:
        model = FileRepository
        fields = ["name"]

    def __init__(self, request, parent_object, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.parent_object = parent_object

    def clean_name(self):
        name = self.cleaned_data.get("name")
        # 数据库判断，当前目录下 此文件夹是否已经存在
        queryset = FileRepository.objects.filter(file_type=2, project=self.request.redmine.project, name=name)  # 将公共的查询条件创建一个对象，利用该对象再去做不同的查询
        if self.parent_object:  # 如果存在父文件夹
            exsits = queryset.filter(parent=self.parent_object).exists()
        else:
            exsits = queryset.filter(parent__isnull=True).exists()

        if exsits:
            raise ValidationError("文件夹已存在")
        return name

class FileModelForm(forms.ModelForm):
    etag = forms.CharField(label='ETag')

    class Meta:
        model = FileRepository
        exclude = ['project', 'file_type', 'update_user', 'update_datetime']

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_file_path(self):
        return "https://{}".format(self.cleaned_data['file_path'])

    """
    # 校验前端$.POST传过来的数据是否合法，避免有人恶意通过传不合法数据(直接发送POST请求, 将$.POST的data伪造数据传送过来), 直接将不合法数据写入数据库, 多了一层网络请求, 速度会慢一点点
    def clean(self):
        key = self.cleaned_data['key']
        etag = self.cleaned_data['etag']
        size = self.cleaned_data['file_size']

        if not key or not etag:
            return self.cleaned_data

        # 向COS校验文件是否合法
        # SDK的功能
        from qcloud_cos.cos_exception import CosServiceError
        try:
            result = check_file(self.request.redmine.project.bucket, self.request.redmine.project.region, key)
        except CosServiceError as e:
            self.add_error("key", '文件不存在')
            return self.cleaned_data

        cos_etag = result.get('ETag')
        if etag != cos_etag:
            self.add_error('etag', 'ETag错误')

        cos_length = result.get('Content-Length')
        if int(cos_length) != size:
            self.add_error('size', '文件大小错误')

        return self.cleaned_data
    """