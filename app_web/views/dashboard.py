#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/8/31 19:54
@DESC : 概览页面视图

'''

import time
import datetime
import collections

from django.views.generic import View
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count

from app_web import models

class dashboard(View):
    """ 概览面板 """
    def get(self, request, project_id):
        # 问题数据处理
        status_dict = collections.OrderedDict()
        for key, text in models.Issues.status_choices:
            status_dict[key] = {'text': text, 'count': 0}
        # 根据status进行分组，并count每一组的数量，并将数量赋值给变量ct，issue_data: <QuerySet [{'status': 1, 'ct': 2}, {'status': 2, 'ct': 2}, ..]>
        issues_data = models.Issues.objects.filter(project_id=project_id).values('status').annotate(ct=Count('id'))
        for item in issues_data:
            status_dict[item['status']]['count'] = item['ct']   # item['status'] 就是上面的key, item['ct']就是每个status类的数量

        # 项目成员
        user_list = models.ProjectUser.objects.filter(project_id=project_id).values('user_id', 'user__username')

        # 最近的10个问题
        top_ten = models.Issues.objects.filter(project_id=project_id, assign__isnull=False).order_by('-id')[0:10]

        context = {
            'status_dict': status_dict,
            'user_list': user_list,
            'top_ten_object': top_ten
        }
        return render(request, 'app_web/dashboard.html', context)


class issues_chart(View):
    """ 概览页面生成highcharts所需的数据 """
    def get(self, request, project_id):
        today = datetime.datetime.now().date()
        date_dict = collections.OrderedDict()
        for i in range(0, 30):
            date = today - datetime.timedelta(days=i)
            date_dict[date.strftime("%Y-%m-%d")] = [time.mktime(date.timetuple()) * 1000, 0]    # time.mktime(date.timetuple())*1000 转化为时间戳

        """ 注释：构造成以数据库取到的创建时间为key, 取到 时间戳，并用ct来修改分组的个数（搞懂django中数据库某个字段的分组并统计数量）
        data_dict = {
            2022-09-01: [158678845891, 0 ],
            2022-09-02: [158673987451, 0 ],
            ...
        }
        """

        # extra 进行高级筛选
        # select xxxx, 1 as ctime from table; 注释： 1 as ctime 新增一个字段  ctime 并且值全为 1
        # select id,name,email from table;
        # select id,name, strftime("%Y-%m-%d",create_datetime) as ctime from table; # extra中的select写法如下
        # "DATE_FORMAT(web_transaction.create_datetime,'%%Y-%%m-%%d')"
        # 数据库中的表名: app名_models里类名小写：例如：app_web_issues, 然后 .create_datetime 取到字段做日期格式化, 赋值给新增的字段ctime
        # 数据库一： sqlite的写法
        # result = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=today - datetime.timedelta(days=30)).extra(
        #     select={'ctime': "strftime('%%Y-%%m-%%d',app_web_issues.create_datetime)"}).values('ctime').annotate(
        #     ct=Count('id')
        # )
        # 数据库二：mysql的写法
        result = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=today - datetime.timedelta(days=30)).extra(
            select={'ctime': "DATE_FORMAT(app_web_issues.create_datetime,'%%Y-%%m-%%d')"}).values('ctime').annotate(
            ct=Count('id')
        )

        for item in result: # 根据数据库创建时间为key取到list, list中 index 0 是时间戳，index 1 是时间戳的个数，这里修改了每天的问题数量
            date_dict[item['ctime']][1] = item['ct']

        return JsonResponse({'status': True, 'data': list(date_dict.values())})


