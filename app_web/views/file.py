#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/8/11 16:38
@DESC : 文件管理视图

'''

import json
import locale

import requests

from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from django.views.generic import View
from django.forms import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils.encoding import escape_uri_path

from app_web.forms.file import folderModelForm, FileModelForm
from app_web.models import FileRepository
from utils.tencent.cos import delete_file, delete_file_list, credential

class file(View):
    """ 文件列表 & 添加文件夹"""

    """ get 和 post方法中公共代码怎么优化 ？？？ """

    def get(self, request, project_id):
        parent_object = None
        folder_id = request.GET.get('folder', "")   # 如果文件夹根目录url就是/manage/project_id/file/, 如果文件夹有父目录url就是/manage/project_id/file?folder=9
        if folder_id.isdecimal():   # 前面get里默认值为"", 保证了folder_id一定是字符串，存在isdecimal方法，然后用isdecimal()判断该字符串是不是纯十进制数字, 是才去数据库查找，避免用户恶意输入folder=Q 筛选报错
            # 如果url里存在folder, 就取出父文件夹的对象
            parent_object = FileRepository.objects.filter(file_type=2, project=request.redmine.project, id=int(folder_id)).first()

        # 展示导航条
        breadcrumb_list = []
        parent_obj = parent_object
        while parent_obj: # 如果当前目录 有父文件夹 将父文件夹放列表最前面
            # breadcrumb_list.insert(0, {'id': parent_obj.id, 'name': parent_obj.name})
            breadcrumb_list.insert(0, model_to_dict(parent_obj, ["id", "name"])) # 另外一种写法, model_to_dict第一个参数为对象, 后面列表为{"id": 对象.id, "name":对象.name}
            parent_obj = parent_obj.parent   # 将当前文件夹更新为父文件夹，来给breadcrumb_list填充数据

        # 展示文件或文件夹目录：将当前目录下所有的文件&文件夹获取到
        queryset = FileRepository.objects.filter(project=request.redmine.project)
        if parent_object:   # 如果存在父目录，进入了某目录
            file_object_list = queryset.filter(parent=parent_object).order_by("-file_type") # 加-号代表从大到小排，2是文件夹排前面，1是文件排后面
        else:   # 进入了根目录
            file_object_list = queryset.filter(parent__isnull=True).order_by("-file_type")

        form = folderModelForm(request=request, parent_object=parent_object)
        context = {
            "form": form,
            "file_object_list": file_object_list,
            "breadcrumb_list": breadcrumb_list,
            "folder_object": parent_object
        }
        return render(request, 'app_web/file.html', context)

    def post(self, request, project_id):
        parent_object = None
        folder_id = request.GET.get('folder', "")   # 如果文件夹根目录url就是/manage/project_id/file/, 如果文件夹有父目录url就是/manage/project_id/file?folder=9
        if folder_id.isdecimal():   # 前面get里默认值为"", 保证了folder_id一定是字符串，存在isdecimal方法，然后用isdecimal()判断该字符串是不是纯十进制数字, 是才去数据库查找，避免用户恶意输入folder=Q 筛选报错
            # 如果url里存在folder, 就取出父文件夹的对象
            parent_object = FileRepository.objects.filter(file_type=2, project=request.redmine.project, id=int(folder_id)).first()
        # POST 文件夹的添加和修改
        fid = request.POST.get("fid","")
        edit_object = None
        if fid.isdecimal(): # fid 不为空就是添加，为空就是新建, 默认给了一个空字符串""，然后用isdecimal来判断字符串是空还是数字id的字符串，由前端{{item.id}}给fid赋值的
            # 编辑
            edit_object = FileRepository.objects.filter(project=request.redmine.project, id=int(fid), file_type=2).first()
        if edit_object: # 如果为空就是新建，不为空就是编辑
            # 加了instance=edit_object后，数据库就不是新建一条记录了，而是覆盖原始的记录
            form = folderModelForm(data=request.POST, request=request, parent_object=parent_object, instance=edit_object)
        else:
            form = folderModelForm(data=request.POST, request=request, parent_object=parent_object)

        if form.is_valid():
            form.instance.project = request.redmine.project
            form.instance.file_type = 2
            form.instance.update_user = request.redmine.user
            form.instance.parent = parent_object
            form.save()
            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False, "error":form.errors})

class file_delete(View):
    """ 删除文件夹 """

    def get(self, request, project_id):
        fid = request.GET.get("fid", "")
        if fid.isdecimal():
            # 删除数据库中的 文件夹 & 文件 (能删除文件夹下文件是因为数据库的级联删除)
            delete_object = FileRepository.objects.filter(id=fid, project=request.redmine.project).first()
            if delete_object.file_type == 1:    # 删除文件: 1. 删除数据库中的文件对象; 2. 删除cos中的文件; 3. 项目已使用空间返还
                # 2. 删除cos中的文件
                delete_file(bucket=request.redmine.project.bucket, region=request.redmine.project.region, key=delete_object.key)
                # 3. 项目已使用空间的返还
                request.redmine.project.use_space -= delete_object.file_size    # 已使用空间减去删除文件的大小
                request.redmine.project.save()
                # 1. 删除数据库中的文件
                delete_object.delete()
                return JsonResponse({"status": True})
            else:   # 删除文件夹: 对文件夹下所有文件做右边三个操作, 1. 删除数据库中的文件对象; 2. 删除cos中的文件; 3. 项目已使用空间返还
                # delete_object
                # 找他下面的 文件和文件夹
                # models.FileRepository.objects.filter(parent=delete_object) # 文件 删除；文件夹 继续向里查

                total_size = 0
                key_list = []

                folder_list = [delete_object, ]
                for folder in folder_list:
                    child_list = FileRepository.objects.filter(project=request.redmine.project,parent=folder).order_by('-file_type')
                    for child in child_list:
                        if child.file_type == 2:
                            folder_list.append(child)
                        else:
                            # 文件大小汇总
                            total_size += child.file_size
                            # 删除文件
                            key_list.append({"Key": child.key})

                # cos 批量删除文件
                if key_list:
                    delete_file_list(request.redmine.project.bucket, request.redmine.project.region, key_list)
                # 归还容量
                if total_size:
                    request.redmine.project.use_space -= total_size
                    request.redmine.project.save()
                # 删除数据库中的文件
                delete_object.delete()
                return JsonResponse({'status': True})
        else:
            return JsonResponse({"status": False, "error": "该文件夹不存在"})


class cos_credential(View):
    """ 获取cos上传临时凭证 """
    def get(self, request, project_id):
        pass

    def post(self, request, project_id):
        per_file_limit = request.redmine.price_policy.per_file_size * 1024 * 1024
        total_file_limit = request.redmine.price_policy.project_space * 1024 * 1024 * 1024
        total_size = 0
        # 一般ajax请求的data数据可以用request.POST获取, 但对于data里嵌套字典要用request.body获取，decode转为字符串，用json.load获取字典
        # 前端$.post 相当于 $.ajax里type：POST, $.post接受三个参数(url, data, callback), 嵌套字典data = JSON.stringify(checkFileList) 转为字节码
        file_list = json.loads(request.body.decode('utf-8'))
        for item in file_list:
            # 文件的字节大小 item['size'] = B
            # 单文件限制的大小 M
            # 超出限制
            if item['size'] > per_file_limit:
                msg = "单文件超出限制（最大{}M），文件：{}，请升级套餐。".format(request.redmine.price_policy.per_file_size, item['name'])
                return JsonResponse({'status': False, 'error': msg})
            total_size += item['size']

            # 做容量限制：单文件 & 总容量

        # 总容量进行限制
        # request.redmine.price_policy.project_space  # 项目的允许的空间
        # request.redmine.project.use_space # 项目已使用的空间
        if request.redmine.project.use_space + total_size > total_file_limit:
            return JsonResponse({'status': False, 'error': "容量超过限制，请升级套餐。"})
        data_dict = credential(request.redmine.project.bucket, request.redmine.project.region)
        return JsonResponse({'status': True, 'data': data_dict})

    @csrf_exempt
    def dispatch(self, *args, **kwargs):    # 基类视图免除csrf roken认证
        return super(cos_credential, self).dispatch(*args, **kwargs)


class file_post(View):
    """ 已上传成功的文件写入到数据 """
    def get(self, request, project_id):
       pass

    def post(self, request, project_id):
        """
              name: fileName,
              key: key,
              file_size: fileSize,
              parent: CURRENT_FOLDER_ID,
              # etag: data.ETag,
              file_path: data.Location
              """
        # 根据key再去cos获取文件Etag和"db7c0d83e50474f934fd4ddf059406e5"

        print(request.POST)
        # 把获取到的数据写入数据库即可
        form = FileModelForm(request, data=request.POST)
        if form.is_valid():
            # 通过ModelForm.save()存储到数据库中的数据返回的isntance对象，无法通过get_xx_display获取choice的中文
            # form.instance.file_type = 1
            # form.update_user = request.redmine.user
            # instance = form.save() # 添加成功之后，获取到新添加的那个对象（instance.id,instance.name,instance.file_type,instace.get_file_type_display()

            # 校验通过：数据写入到数据库
            data_dict = form.cleaned_data
            data_dict.pop('etag')   # 数据库不写etag
            data_dict.update({'project': request.redmine.project, 'file_type': 1, 'update_user': request.redmine.user}) # 加入其它必要字段
            instance = FileRepository.objects.create(**data_dict)   # 写入数据库

            # 项目的已使用空间：更新 (data_dict['file_size'])
            request.redmine.project.use_space += data_dict['file_size']
            request.redmine.project.save()

            locale.setlocale(locale.LC_CTYPE, 'Chinese')    # 这里设置了locale decode后，下面的datatime时间格式化就不会报错了

            result = {
                'id': instance.id,
                'name': instance.name,
                'file_size': instance.file_size,
                'username': instance.update_user.username,
                'datetime': instance.update_datetime.strftime("%Y年%m月%d日 %H:%M"),
                'download_url': reverse('file_download', kwargs={"project_id": project_id, 'file_id': instance.id})
                # 'file_type': instance.get_file_type_display()
            }
            return JsonResponse({'status': True, 'data': result})

        return JsonResponse({'status': False, 'data': "文件错误"})

    @csrf_exempt
    def dispatch(self, *args, **kwargs):    # 基类视图免除csrf roken认证
        return super(file_post, self).dispatch(*args, **kwargs)


class file_download(View):
    """ 下载文件 """

    def get(self, request, project_id, file_id):
        """ 下载文件 """

        file_object = FileRepository.objects.filter(id=file_id, project_id=project_id).first()
        res = requests.get(file_object.file_path)

        # 文件分块处理（适用于大文件）
        data = res.iter_content()

        # 设置content_type=application/octet-stream 用于提示下载框
        response = HttpResponse(data, content_type="application/octet-stream")

        # 设置响应头：中文件文件名转义
        response['Content-Disposition'] = "attachment; filename={};".format(escape_uri_path(file_object.name))
        return response