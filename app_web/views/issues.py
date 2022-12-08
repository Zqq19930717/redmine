#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/8/28 14:54
@Desc : 问题管理视图

'''

import json
import datetime
from django.views.generic import View
from django.shortcuts import render, reverse
from django.http.response import JsonResponse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from app_web.forms.issues import InviteModelForm, IssuesModelForm, IssuesReplyModelForm
from app_web.models import ProjectInvite,ProjectUser,Transaction, PricePolicy, Issues, IssuesType, IssuesReply
from utils.encrypt import uid
from utils.pagination import Pagination

class CheckFilter(object):
    def __init__(self, name, data_list, request):
        self.name = name
        self.data_list = data_list
        self.request = request

    def __iter__(self):
        """
        这里的data_list =   (
                    (1, '新建'),
                    (2, '处理中'),
                    (3, '已解决'),
                    (4, '已忽略'),
                    (5, '待反馈'),
                    (6, '已关闭'),
                    (7, '重新打开'),
                )
        那么进入到issue页面，很明显，当下所有的筛选条件都是没有打勾的，此时value_list为空, 那么我for循环遍历第一个 1，'新建' 时候，
        1不再空的value_list里面, 我把1加进去, value_list此时为[1,], 设置到query_dict里，query此时为{'status': [1,]}, 那么生成
        此时生成的url为 http://localhost:8000/manage/16/issue/?status=1, 并生成checkbox的a标签 + 新建文本，将url赋值给了该a标签，
        同理for 循环遍历第二个 2, '处理中'，同样将url为 http://localhost:8000/manage/16/issue/?status=2 赋值给了第二个a标签,
        也就是说为以上7个a标签都生成了url: http://localhost:8000/manage/16/issue/?status=1~7, 此时这7个都还是未选中状态，只要点击1就会跳转到
        http://localhost:8000/manage/16/issue/?status=1， 点击2就会跳转到http://localhost:8000/manage/16/issue/?status=2，


        但是注意每一次点击都会跳转都会由a标签发送请求http://localhost:8000/manage/16/issue/，触发issue 视图的get方法，再一次走入for循环中，遍历这7个标签。
        此时，比如1已经被点击了，地址栏url此时为 http://localhost:8000/manage/16/issue/?status=1, value_list=[1,], 那么for循环1时，会将1的checkbox打勾
        并将value_list里的1移除，此时为选中的1，'新建'a标签生成的url就是 http://localhost:8000/manage/16/issue/，但是for循环2时，这里的value_list = [1,]
        因为不管for循环几，在for循环里面的value_list 都会重新获取地址栏的url，那么2不在value_list里面，不在就放进去，此时value_list= [1,2,]，那么此时重新生成
        的a标签的url= http://localhost:8000/manage/16/issue/?status=1&status=2,
        为for循环以后的每一次x的 a 标签生成的url 都是 http://localhost:8000/manage/16/issue/?status=1&status=x


        此处的核心思路是： 所有未被选中的标签的url 都要带？status=x，使其点击时跳转？status=x做筛选，所有选中的标签的url都不带? status=x，使选中的标签再次
        点击时跳转的url不再做筛选， 以及每次勾选和取消勾选都会重新触发生成所有的筛选标签，每次url里都去请求地址栏最新url, 在此基础上url移除已选中的标签，并
        新增未被选中的标签status
        """
        for item in self.data_list:
            key = str(item[0])
            text = item[1]
            ck = ""
            # 如果当前用户请求的URL中status和当前循环key相等
            value_list = self.request.GET.getlist(self.name)
            if key in value_list:
                ck = 'checked'
                value_list.remove(key)
            else:
                value_list.append(key)

            # 为自己生成URL
            # 在当前URL的基础上去增加一项
            # status=1&age=19
            from django.http import QueryDict
            query_dict = self.request.GET.copy()
            query_dict._mutable = True      # 将_mutable设置为true才能做更改
            query_dict.setlist(self.name, value_list)
            if 'page' in query_dict:    # 这里其实点page也会触发走到这个函数，删除掉复制的url中的page属性，但是新生成的url只提供给了筛选a标签使用，依据a标签请求出来的url不需要包含page页面
                query_dict.pop('page')

            param_url = query_dict.urlencode()  # 如果query_dict是{"status":[1,2,3], 'xx': [1,]}, urlencode()就会拼接成 #status=1&status=2&status=3&xx=1
            if param_url:  # url有键值对加入?做拼接
                url = "{}?{}".format(self.request.path_info, param_url)  # self.request.path_info 是 http://localhost:8000/manage/16/issue/
            else:   # url里没有键值对直接等于当前的url，避免url多了一个?
                url = self.request.path_info

            tpl = '<a class="cell" href="{url}"><input type="checkbox" {ck} /><label>{text}</label></a>'
            html = tpl.format(url=url, ck=ck, text=text)
            yield mark_safe(html)


class SelectFilter(object):
    def __init__(self, name, data_list, request):
        self.name = name
        self.data_list = data_list
        self.request = request

    def __iter__(self):
        yield mark_safe("<select class='select2' multiple='multiple' style='width:100%;' >")
        for item in self.data_list:
            key = str(item[0])
            text = item[1]

            selected = ""
            value_list = self.request.GET.getlist(self.name)
            if key in value_list:
                selected = 'selected'
                value_list.remove(key)
            else:
                value_list.append(key)

            query_dict = self.request.GET.copy()
            query_dict._mutable = True
            query_dict.setlist(self.name, value_list)
            if 'page' in query_dict:
                query_dict.pop('page')

            param_url = query_dict.urlencode()
            if param_url:
                url = "{}?{}".format(self.request.path_info, param_url)  # status=1&status=2&status=3&xx=1
            else:
                url = self.request.path_info

            html = "<option value='{url}' {selected} >{text}</option>".format(url=url, selected=selected, text=text)
            yield mark_safe(html)
        yield mark_safe("</select>")

class issues(View):
    """ 问题页面展示 """

    def get(self, request, project_id):
        # 根据URL做筛选，筛选条件（根据用户通过GET传过来的参数实现）
        # ?status=1&status=2&issues_type=1
        allow_filter_name = ['issues_type', 'status', 'priority', 'assign', 'attention', 'mode']
        condition = {}
        for name in allow_filter_name:
            value_list = request.GET.getlist(name)  # [1,2]
            if not value_list:
                continue
            condition["{}__in".format(name)] = value_list
        """
        condition = {
            "status__in":[1,2],
            'issues_type__in':[1,]
        }
        """

        # 分页获取数据
        queryset = Issues.objects.filter(project_id=project_id).filter(**condition)
        page_object = Pagination(
            current_page=request.GET.get('page'),
            all_count=queryset.count(),
            base_url=request.path_info,
            query_params=request.GET,
            per_page=10
        )
        issues_object_list = queryset[page_object.start:page_object.end]

        form = IssuesModelForm(request)

        # 试了下 issues_type__in 和 issues_type_id__in 给到数据库都能filter出来，那么直接拼接出一个choices构造器，tuple(构造器)传递过去即可
        # issues_type_choices = ((issue_count, issue_value) for issue_count, issue_value in enumerate(IssuesType.PROJECT_INIT_LIST, start=1))
        # 传递过去 {'title': "问题类型", 'filter': CheckFilter('issues_type', tuple(issues_type_choices), request)}
        # 注释掉用 wupeiqi的方式, 直接传递过去了一个queryset： <QuerySet [(1, '任务'), (2, '功能'), (3, 'Bug')]>
        project_issues_type = IssuesType.objects.filter(project_id=project_id).values_list('id', 'title')

        project_total_user = [(request.redmine.project.creator_id, request.redmine.project.creator.username,)]  # 项目的创建者
        join_user = ProjectUser.objects.filter(project_id=project_id).values_list('user_id', 'user__username')  # 项目的参与者
        project_total_user.extend(join_user)

        invite_form = InviteModelForm()
        context = {
            'form': form,
            'invite_form': invite_form,
            'issues_object_list': issues_object_list,
            'page_html': page_object.page_html(),
            'filter_list': [
                {'title': "问题类型", 'filter': CheckFilter('issues_type', project_issues_type, request)},
                {'title': "状态", 'filter': CheckFilter('status', Issues.status_choices, request)},
                {'title': "优先级", 'filter': CheckFilter('priority', Issues.priority_choices, request)},
                {'title': "模式", 'filter': CheckFilter('mode', Issues.mode_choices, request)},
                {'title': "指派者", 'filter': SelectFilter('assign', project_total_user, request)},
                {'title': "关注者", 'filter': SelectFilter('attention', project_total_user, request)},
            ]
        }
        return render(request, 'app_web/issues.html', context)

    def post(self, request, project_id):
        form = IssuesModelForm(request, data=request.POST)
        if form.is_valid():
            form.instance.project = request.redmine.project
            form.instance.creator = request.redmine.user
            form.save()
            return JsonResponse({'status': True})

        return JsonResponse({'status': False, 'error': form.errors})


class invite_url(View):
    """ 邀请链接"""
    def post(self, request, project_id):
        """ 生成邀请码 """

        form = InviteModelForm(data=request.POST)
        if form.is_valid():
            """
            1. 创建随机的邀请码
            2. 验证码保存到数据库
            3. 限制：只有创建者才能邀请
            """
            if request.redmine.user != request.redmine.project.creator:
                form.add_error('period', "您无权创建邀请码")
                return JsonResponse({'status': False, 'error': form.errors})

            random_invite_code = uid(request.redmine.user.mobile_phone)
            form.instance.project = request.redmine.project
            form.instance.code = random_invite_code
            form.instance.creator = request.redmine.user
            form.save()

            # 将验邀请码返回给前端，前端页面上展示出来。
            url = "{scheme}://{host}{path}".format(
                scheme=request.scheme,  # 取到http 或 https
                host=request.get_host(),    # 拿到域名 + 端口
                path=reverse('invite_join', kwargs={'code': random_invite_code})
            )

            return JsonResponse({'status': True, 'data': url})

        return JsonResponse({'status': False, 'error': form.errors})

class invite_join(View):
    def get(self, request, code):
        """ 访问邀请码 """
        current_datetime = datetime.datetime.now()

        invite_object = ProjectInvite.objects.filter(code=code).first()
        if not invite_object:
            return render(request, 'app_web/invite_join.html', {'error': '邀请码不存在'})

        if invite_object.project.creator == request.redmine.user:
            return render(request, 'app_web/invite_join.html', {'error': '创建者无需再加入项目'})

        exists = ProjectUser.objects.filter(project=invite_object.project, user=request.redmine.user).exists()
        if exists:
            return render(request, 'app_web/invite_join.html', {'error': '您无法重复加入该项目'})

        # ####### 问题1： 最多允许的成员(要进入的项目的创建者的限制）#######
        # max_member = request.redmine.price_policy.project_member # 这里取的是当前登录用户的限制，应该取项目创建者的限制

        # 是否已过期，如果已过期则使用免费额度
        max_transaction = Transaction.objects.filter(user=invite_object.project.creator).order_by('-id').first()
        if max_transaction.price_policy.category == 1:  # 免费额度
            max_member = max_transaction.price_policy.project_member
        else:   # 不是免费额度
            if max_transaction.end_datetime < current_datetime:     # 支付是否已过期
                free_object = PricePolicy.objects.filter(category=1).first()
                max_member = free_object.project_member
            else:
                max_member = max_transaction.price_policy.project_member


        # 目前所有成员(创建者&参与者）
        current_member = ProjectUser.objects.filter(project=invite_object.project).count()
        current_member = current_member + 1
        if current_member >= max_member:
            return render(request, 'app_web/invite_join.html', {'error': '项目成员超出限制 {0} 人，请升级套餐'.format(max_member)})

        # 邀请码是否过期？

        limit_datetime = invite_object.create_datetime + datetime.timedelta(minutes=invite_object.period)
        if current_datetime > limit_datetime:
            return render(request, 'app_web/invite_join.html', {'error': '邀请码已过期'})

        # 邀请人数限制？
        if invite_object.count: # 如果有邀请人数限制
            if invite_object.use_count >= invite_object.count:  # 达到了邀请人数限制
                return render(request, 'app_web/invite_join.html', {'error': '邀请人数已达上限'})
            invite_object.use_count += 1
            invite_object.save()

        ProjectUser.objects.create(user=request.redmine.user, project=invite_object.project)

        # ####### 问题2： 更新项目参与成员 #######
        invite_object.project.join_count += 1
        invite_object.project.save()

        return render(request, 'app_web/invite_join.html', {'project': invite_object.project})

class issues_detail(View):
    """ 问题详细视图 """
    def get(self, request, project_id, issues_id):
        """ 编辑问题 """
        issues_object = Issues.objects.filter(id=issues_id, project_id=project_id).first()
        form = IssuesModelForm(request, instance=issues_object)
        return render(request, 'app_web/issues_detail.html', {'form': form, "issues_object": issues_object})


class issues_record(View):
    """ 初始化操作记录 """
    def get(self, request, project_id, issues_id):
        # 判断是否可以评论和是否可以操作这个问题

        reply_list = IssuesReply.objects.filter(issues_id=issues_id, issues__project=request.redmine.project)
        # 将queryset转换为json格式
        data_list = []
        for row in reply_list:
            data = {
                'id': row.id,
                'reply_type_text': row.get_reply_type_display(),
                'content': row.content,
                'creator': row.creator.username,
                'datetime': row.create_datetime.strftime("%Y-%m-%d %H:%M"),
                'parent_id': row.reply_id
            }
            data_list.append(data)

        return JsonResponse({'status': True, 'data': data_list})

    def post(self, request, project_id, issues_id):
        form = IssuesReplyModelForm(data=request.POST)
        if form.is_valid():
            form.instance.issues_id = issues_id
            form.instance.reply_type = 2
            form.instance.creator = request.redmine.user
            instance = form.save()
            info = {    # 再将数据返给前端做数据展示
                'id': instance.id,
                'reply_type_text': instance.get_reply_type_display(),
                'content': instance.content,
                'creator': instance.creator.username,
                'datetime': instance.create_datetime.strftime("%Y-%m-%d %H:%M"),
                'parent_id': instance.reply_id
            }

            return JsonResponse({'status': True, 'data': info})
        return JsonResponse({'status': False, 'error': form.errors})

    @csrf_exempt
    def dispatch(self, *args, **kwargs):    # 基类视图免除csrf roken认证
        return super(issues_record, self).dispatch(*args, **kwargs)


class issues_change(View):
    """ 问题更改记录 前端通过change方法监控任意字段更改了，都会触发ajax请求url反向解析到该视图, 并传递过来修改后的值组成的字典"""
    def post(self, request, project_id, issues_id):
        issues_object = Issues.objects.filter(id=issues_id, project_id=project_id).first()

        post_dict = json.loads(request.body.decode('utf-8'))
        """
        {'name': 'subject', 'value': '好饿呀sdfasdf'}
        {'name': 'subject', 'value': ''}
    
        {'name': 'desc', 'value': '好饿呀sdfasdf'}
        {'name': 'desc', 'value': ''}
    
        {'name': 'start_date', 'value': '好饿呀sdfasdf'}
        {'name': 'end_date', 'value': '好饿呀sdfasdf'}
    
        {'name': 'issues_type', 'value': '2'}
        {'name': 'assign', 'value': '4'}
        """
        name = post_dict.get('name')
        value = post_dict.get('value')
        if name is not None:    # 这里用户可能将关注着填为了空，需要判断是否是None
            field_object = Issues._meta.get_field(name) # 固定写法，获取到某个字段对象, 对象.null就能获取到对象是否允许为空

        def create_reply_record(content):
            new_object = IssuesReply.objects.create(    # 数据库添加完数据后， 返回这行数据的对象
                reply_type=1,
                issues=issues_object,
                content=change_record,
                creator=request.redmine.user,
            )
            new_reply_dict = {      # 将更新记录转化为字典传给前端，变成跟评论一样的字典，传递给前端创建记录的函数
                'id': new_object.id,
                'reply_type_text': new_object.get_reply_type_display(),
                'content': new_object.content,
                'creator': new_object.creator.username,
                'datetime': new_object.create_datetime.strftime("%Y-%m-%d %H:%M"),
                'parent_id': new_object.reply_id
            }
            return new_reply_dict

        # 1. 数据库字段更新
        # 1.1 文本
        if name in ["subject", 'desc', 'start_date', 'end_date']:
            if not value:
                if not field_object.null:   # value为空时, field_object.null是 False 时说明不允许为空
                    return JsonResponse({'status': False, 'error': "您选择的值不能为空"})
                setattr(issues_object, name, None)  # value为空时，如果允许为空，就设置为None
                issues_object.save()
                change_record = "{} 更新为 空".format(field_object.verbose_name)
            else:
                setattr(issues_object, name, value)
                issues_object.save()
                # 记录：xx更为了value
                change_record = "{} 更新为 {}".format(field_object.verbose_name, value)

            return JsonResponse({'status': True, 'data': create_reply_record(change_record)})

        # 1.2 FK字段（指派的话要判断是否创建者或参与者）
        if name in ['issues_type', 'module', 'parent', 'assign']:
            # 用户选择为空
            if not value:
                # 不允许为空
                if not field_object.null:
                    return JsonResponse({'status': False, 'error': "您选择的值不能为空"})
                # 允许为空
                setattr(issues_object, name, None)
                issues_object.save()
                change_record = "{} 更新为 空".format(field_object.verbose_name)
            else:  # 用户输入不为空
                if name == 'assign':
                    # 是否是项目创建者
                    if value == str(request.redmine.project.creator_id):
                        instance = request.redmine.project.creator
                    else:
                        # 是否是项目参与者
                        project_user_object = ProjectUser.objects.filter(project_id=project_id, user_id=value).first()
                        if project_user_object:
                            instance = project_user_object.user
                        else:
                            instance = None
                    if not instance:
                        return JsonResponse({'status': False, 'error': "您选择的值不存在"})

                    setattr(issues_object, name, instance)
                    issues_object.save()
                    change_record = "{} 更新为 {}".format(field_object.verbose_name, str(instance))  # value根据文本获取到内容
                else:
                    # 条件判断：用户输入的值，是自己的值。字段.rel.model相当于拿到了这个字段关联的表
                    instance = field_object.rel.model.objects.filter(id=value, project_id=project_id).first()
                    if not instance:    # 必须是当前项目存在的值
                        return JsonResponse({'status': False, 'error': "您选择的值不存在"})
                    # 这里的三个setattr和save和change_record都是相同的，可以提取到if else 外面, 但放里面逻辑看起来更清晰
                    setattr(issues_object, name, instance)
                    issues_object.save()
                    # 这里的str(object)， 相当于调用了object.__str__(), models对每张表重写了__str__, 不用在这里点name, .title拿到名称了
                    change_record = "{} 更新为 {}".format(field_object.verbose_name, str(instance))  # value根据文本获取到内容

            return JsonResponse({'status': True, 'data': create_reply_record(change_record)})

        # 1.3 choices字段
        if name in ['priority', 'status', 'mode']:
            selected_text = None
            for key, text in field_object.choices:  # 拿到choices的元组
                if str(key) == value:
                    selected_text = text
            if not selected_text:
                return JsonResponse({'status': False, 'error': "您选择的值不存在"})

            setattr(issues_object, name, value)
            issues_object.save()
            change_record = "{} 更新为 {}".format(field_object.verbose_name, selected_text)
            return JsonResponse({'status': True, 'data': create_reply_record(change_record)})

        # 1.4 M2M字段
        if name == "attention":
            # {"name":"attention","value":[1,2,3]}
            if not isinstance(value, list):
                return JsonResponse({'status': False, 'error': "数据格式错误"})

            if not value:   # 用户输入的关注者为空
                issues_object.attention.set(value)
                issues_object.save()
                change_record = "{} 更新为 空".format(field_object.verbose_name)
            else:
                # values=["1","2,3,4]  ->   id是否是项目成员（参与者、创建者）
                # 获取当前项目的所有成员
                user_dict = {str(request.redmine.project.creator_id): request.redmine.project.creator.username} # 项目创建者，以id为key
                project_user_list = ProjectUser.objects.filter(project_id=project_id)   # 获取项目所有参与者
                for item in project_user_list:
                    user_dict[str(item.user_id)] = item.user.username   # 将参与者添加到创建者中，获取项目所有成员
                username_list = []
                # 详细比对非法数据的逻辑处理，不一定是黑客，比如有些人在当前用户登录时，剔除了某个参与者，页面没做刷新选择了剔除的用户也会触发不合法数据
                for user_id in value:
                    username = user_dict.get(str(user_id))  # 看看项目所有成员是否能获取到用户传过来的关注者
                    if not username:    # 获取不到相关注者
                        return JsonResponse({'status': False, 'error': "用户不存在请重新设置"})
                    username_list.append(username)

                issues_object.attention.set(value)
                issues_object.save()
                change_record = "{} 更新为 {}".format(field_object.verbose_name, ",".join(username_list))

            return JsonResponse({'status': True, 'data': create_reply_record(change_record)})

        # 不是上述四种字段传过来了
        return JsonResponse({'status': False, 'error': "你传来了非法字段的数据哦！"})

    @csrf_exempt
    def dispatch(self, *args, **kwargs):    # 基类视图免除csrf roken认证
        return super(issues_change, self).dispatch(*args, **kwargs)