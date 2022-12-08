#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/9/1 0:49
@Desc : 统计页面视图

'''

import collections

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count
from django.views.generic import View

from app_web import models


class statistics(View):
    """ 统计页面 """
    def get(self, request, project_id):
        return render(request, 'app_web/statistics.html')


class statistics_priority(View):
    """ 按照优先级生成饼图 """
    def get(self, request, project_id):
        """ 按照优先级生成饼图 """

        # 找到所有的问题，根据优先级分组，每个优先级的问题数量
        start = request.GET.get('start')
        end = request.GET.get('end')

        # 1.构造字典
        data_dict = collections.OrderedDict()
        for key, text in models.Issues.priority_choices:    # key：danger, warning, success, text: 高，中，低，y: '后面修改为依据priority字段的值进行分组的数量'
            data_dict[key] = {'name': text, 'y': 0}

        # 2.去数据查询所有分组得到的数据量
        # 根据priority进行分组，并count每一组的数量，并将数量赋值给变量ct，issue_data: <QuerySet [{'priority': danger, 'ct': 2}, {'priority': warning, 'ct': 2}, ..]>
        result = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=start, create_datetime__lt=end).values('priority').annotate(ct=Count('id'))

        # 3.把分组得到的数据更新到data_dict中
        for item in result:
            data_dict[item['priority']]['y'] = item['ct']   # item['priority'] = danger, warning, success

        return JsonResponse({'status': True, 'data': list(data_dict.values())})


class statistics_project_user(View):
    """ 项目成员每个人被分配的任务数量（问题类型的配比）"""
    def get(self, request, project_id):

        start = request.GET.get('start')
        end = request.GET.get('end')

        """ info的一级key是用户id
        info = {
            1:{
                name:"ysz",
                status:{
                    1:0,
                    2:1,
                    3:0,
                    4:0,
                    5:0,
                    6:0,
                    7:0,
                }
            },
            2:{
                name:"zqq",
                status:{
                    1:0,
                    2:0,
                    3:1,
                    4:0,
                    5:0,
                    6:0,
                    7:0,
                }
            }
        }
        """
        # 1. 所有项目成员 及 未指派
        all_user_dict = collections.OrderedDict()
        all_user_dict[request.redmine.project.creator.id] = {   # 初始化项目创建者 问题状态 字典
            'name': request.redmine.project.creator.username,
            'status': {item[0]: 0 for item in models.Issues.status_choices}
        }
        all_user_dict[None] = {     # bug未指派人员
            'name': '未指派',
            'status': {item[0]: 0 for item in models.Issues.status_choices}
        }
        user_list = models.ProjectUser.objects.filter(project_id=project_id)    # 获取项目所有成员
        for item in user_list:
            all_user_dict[item.user_id] = {
                'name': item.user.username,
                'status': {item[0]: 0 for item in models.Issues.status_choices}
            }

        # 2. 去数据库获取相关的所有问题
        issues = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=start, create_datetime__lt=end)
        for item in issues:
            if not item.assign: # 未指派
                all_user_dict[None]['status'][item.status] += 1
            else:   # 已指派
                all_user_dict[item.assign_id]['status'][item.status] += 1

        # 3.获取所有的成员
        categories = [data['name'] for data in all_user_dict.values()]  # 柱状图所需要的第一个参数 xAxis 展示

        # 4.构造字典
        """
        data_result_dict = {
            1:{name:新建,data:[1，2，3，4]},
            2:{name:处理中,data:[3，4，5]},
            3:{name:已解决,data:[]},
            4:{name:已忽略,data:[]},
            5:{name:待反馈,data:[]},
            6:{name:已关闭,data:[]},
            7:{name:重新打开,data:[]},
        }
        """
        data_result_dict = collections.OrderedDict()
        for item in models.Issues.status_choices:
            data_result_dict[item[0]] = {'name': item[1], "data": []}

        for key, text in models.Issues.status_choices:
            # key=1,text='新建'
            for row in all_user_dict.values():
                count = row['status'][key]
                data_result_dict[key]['data'].append(count)

        context = {
            'status': True,
            'data': {
                'categories': categories,
                'series': list(data_result_dict.values())
            }
        }

        return JsonResponse(context)