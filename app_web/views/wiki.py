#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/28 14:17
@DESC : wiki页面试图

'''
import os

from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from app_web.forms.wiki import WikiModelForm
from app_web.models import Wiki
from utils.tencent.cos import upload_file
from utils.encrypt import uid

class wiki(View):
    """ 项目wiki首页 """
    def get(self, request, project_id):
        wiki_id = request.GET.get("wiki_id")
        if not wiki_id or not wiki_id.isdecimal(): # wiki_id不存在 或者 不是只包含十进制数字
            return render(request, 'app_web/wiki.html')
        wiki_object = Wiki.objects.filter(id=wiki_id, project_id=project_id).first()    # 有可能没查到为空，返回给前端再做判断

        return render(request, 'app_web/wiki.html',{"wiki_object":wiki_object})

class wiki_add(View):
    """ 项目wiki新建文档 """
    def get(self, request, project_id):
        form = WikiModelForm(request)
        return render(request, 'app_web/wiki_form.html', {"form": form})

    def post(self, request, project_id):
        form = WikiModelForm(data=request.POST, request=request)
        if form.is_valid():
            form.instance.project = request.redmine.project
            # 也就是 form.cleaned_data 和 form.instance几乎等价
            # print(form.cleaned_data)    # {'title': '123456', 'content': '123456', 'parent': <Wiki: 123>}
            # print(form.instance)        # {'title': '222', 'content': '222', 'parent': <Wiki: 1234>}
            # print(form.cleaned_data.get("parent").depth)
            if form.cleaned_data.get("parent"): # 如果不为空
                form.instance.depth = form.cleaned_data["parent"].depth + 1
            else:
                form.instance.depth = 1
            form.save()
            return redirect(reverse('wiki', kwargs={'project_id':project_id}))
        else:
            return render(request, 'app_web/wiki_form.html', {"form": form})

class wiki_catalog(View):
    """ wiki目录展示 """
    def get(self, request, project_id):
        # 去数据库查询目录信息，values_list产出的是元祖，values产出的是字典, 字典有key更好辨认数据
        # 按照depth排序避免新创建的id小的子目录修改到后创建的根目录下时，子目录先展示会找不到父目录
        data = Wiki.objects.filter(project=request.redmine.project).values('id', 'title', 'parent_id').order_by('depth','id')
        # data = Wiki.objects.filter(project=request.redmine.project).values_list('id', 'title', 'parent_id').order_by('depth', 'id')

        # data是QuerySet报错TypeError: Object of type QuerySet is not JSON serializable，直接list(data)强制转换可以
        return JsonResponse({"status": True, "data": list(data)})


class wiki_delete(View):
    """ wiki 文章删除 """
    def get(self, request, project_id, delete_id):
        Wiki.objects.filter(project_id=project_id, id=delete_id).delete()
        return render(request, 'app_web/wiki.html')

class wiki_edit(View):
    """ wiki 文章编辑"""
    def get(self, request, project_id, edit_id):
        wiki_object = Wiki.objects.filter(project_id=project_id, id=edit_id).first()
        if not wiki_object:
            return redirect(reverse('wiki', kwargs={'project_id': project_id}))
        form = WikiModelForm(instance=wiki_object, request=request)
        return render(request, 'app_web/wiki_form.html', {"form": form})

    def post(self, request, project_id, edit_id):
        wiki_object = Wiki.objects.filter(project_id=project_id, id=edit_id).first()
        form = WikiModelForm(data=request.POST, request=request, instance=wiki_object)
        if form.is_valid():
            form.instance.project = request.redmine.project
            if form.cleaned_data.get("parent"):  # 如果不为空
                form.instance.depth = form.cleaned_data["parent"].depth + 1
            else:
                form.instance.depth = 1
            form.save()
            url = '{0}?wiki_id={1}'.format(reverse('wiki'.format(project_id), kwargs={'project_id': project_id}), edit_id)
            return redirect(url)
        else:
            return render(request, 'app_web/wiki_form.html', {"form": form})


class wiki_upload(View):
    """ markdown插件上传图片 """
    def get(self, request, project_id):
        return JsonResponse({"status": True})

    def post(self, request, project_id):
        # markdown接受的数据格式，需要success, message, url信息
        result = {
            'success': 0,
            'message': None,
            'url': None
        }
        # print(request.FILES)    # <MultiValueDict: {'editormd-image-file': [<InMemoryUploadedFile: report.png (image/png)>]}>
        image_object = request.FILES.get("editormd-image-file")
        if not image_object:
            result['message'] = "文件不存在"
            return JsonResponse(result)
        # 将文件对象上传到当前项目的桶中
        font, ext = os.path.splitext(image_object.name)
        key = "{0}{1}".format(uid(request.redmine.user.mobile_phone), ext)
        image_url = upload_file(
            bucket=request.redmine.project.bucket,
            region=request.redmine.project.region,
            file_object=image_object,
            key=key
        )
        result['success'] = 1       #代表上传成功了
        result['url'] = image_url
        return JsonResponse(result)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):    # 基类视图免除csrf roken认证
        return super(wiki_upload, self).dispatch(*args, **kwargs)

