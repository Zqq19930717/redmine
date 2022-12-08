#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''

@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/10 17:52
@Desc : account view 所用modelfom

'''

import random

from django import forms
from django.core.validators import RegexValidator,ValidationError
from django.conf import settings
from django_redis import get_redis_connection

from app_web.models import UserInfo
from app_web.forms.bootstrap import BootstrapForm
from utils.tencent.sms import send_sms_single
from utils.encrypt import md5


class RegisterModelForm(BootstrapForm, forms.ModelForm):
    mobile_phone = forms.CharField(label="手机号", validators=[RegexValidator(regex=r'^(1[3|4|5|6|7|8|9])\d{9}$', message="手机号格式错误")])
    password = forms.CharField(widget=forms.PasswordInput(), label="密码", min_length=8, validators=[RegexValidator(r'^[a-zA-Z0-9]+.*', '密码必须字母结合数字,不小于8位')])  # 调整为输入密码时显示*******
    # 为什么不在model.py里面写这个confirm_password呢？因为数据库不需要这个字段, 只是页面输入时需要这个字段, 所以只在modelform这里生成了
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control', 'placeholder':"请输入密码"}), label="确认密码")
    code = forms.CharField(label="验证码", widget=forms.TextInput())

    class Meta:
        model = UserInfo
        fields = ["username", "email", "password", "confirm_password", "mobile_phone", "code"]

    # 钩子方法clean_fileds, 对confirm_password字段进行设置
    def clean_password(self):
        # print(self.cleaned_data)    # {'username': 'test', 'password': '123', 'confirm_password': '456'}
        password_context = self.cleaned_data.get("password")
        # return 的数据会作为value直接写入到cleaned_data里的'confirm_password', 如果return "333", 那'confirm_password':'333',最后save进数据库的也是return的值
        return md5(password_context)    # 加密密码并返回

    # 钩子方法clean_fileds, 对confirm_password字段进行设置
    def clean_confirm_password(self):
        # print(self.cleaned_data)    # {'username': 'test', 'password': '123', 'confirm_password': '456'}
        password_context = self.cleaned_data.get("password")    # 在feilds里password字段在前面，上面return md5(password_context)后这里已经是密文了
        confirm_password_context = md5(self.cleaned_data.get("confirm_password"))
        if password_context != confirm_password_context:
            raise ValidationError("两次输入密码不一致")
        # return 的数据会作为value直接写入到cleaned_data里的'confirm_password', 如果return "333", 那'confirm_password':'333',最后save进数据库的也是return的值
        return confirm_password_context

    # 验证码钩子函数
    def clean_code(self):
        # 获取验证码
        code = self.cleaned_data['code']
        # 获取手机号
        mobile_phone = self.cleaned_data.get("mobile_phone")
        if not mobile_phone:    # 手机号不存在，验证码不用继续校验
            return code
        conn = get_redis_connection()
        ver_code = conn.get(mobile_phone)
        if not ver_code:   # 如果在redis取到手机对应的验证码为空(其实就是用户没有点击获取验证码, 随便输入了一个验证码)
            raise ValidationError("该验证码无效")
        if code.strip() != ver_code.decode("utf-8"):    # 如果用户在输入验证码后加了一个空格也让通过，比较省事, 免得去debug空格问题
            raise ValidationError("验证码错误")

    # 用户名钩子函数
    def clean_username(self):
        input_username = self.cleaned_data.get("username")
        exists = UserInfo.objects.filter(username=input_username).exists()
        if exists:
            raise ValidationError('用户名已存在')
        # 记住钩子函数一定要return回去给modelform中, 要不然就是默认的return none了, 用户名那一栏尽管用户输入了modelform里数据也为空, 前端页面会报错, 该值不允许为Null
        return input_username

    # 邮箱钩子函数
    def clean_email(self):
        input_email = self.cleaned_data["email"]
        exists = UserInfo.objects.filter(email=input_email).exists()
        if exists:
            raise ValidationError('邮箱已存在')
        # 记住钩子函数一定要return回去, 要不然就是默认的return none了, 邮箱那一栏尽管用户输入了数据也为空, 前端页面会报错, 该值不允许为Null
        return input_email

    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']
        exists = UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if exists:
            raise ValidationError('该手机号已注册')
        return mobile_phone

class SendSmsForm(forms.Form):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误'), ])

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_mobile_phone(self):
        """ 手机号校验的钩子 """
        mobile_phone = self.cleaned_data['mobile_phone']

        # 判断短信模板是否有问题
        tpl = self.request.GET.get('tpl')    # tpl就是url里 ?tpl=xxx 的 xxx
        template_id = settings.TENCENT_SMS_TEMPLATE.get(tpl)
        if not template_id:
            # self.add_error('mobile_phone','短信模板错误')
            raise ValidationError('腾讯云短信模板不存在！')

        exists = UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if tpl == 'login':
            if not exists:
                raise ValidationError('手机号不存在')
        else:
            # 校验数据库中是否已有手机号
            if exists:
                raise ValidationError('该手机号已注册')

        # 发短信 & 写入redis
        code = random.randrange(100000, 999999)

        # 发送短信
        sms = send_sms_single(mobile_phone, template_id, [code, ])
        if sms['result'] != 0:
            raise ValidationError("短信发送失败，{}".format(sms['errmsg']))

        # 验证码 写入redis（django-redis）
        conn = get_redis_connection()
        conn.set(mobile_phone, code, ex=60)

        return mobile_phone

class LoginSMSForm(BootstrapForm, forms.Form):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误'), ])
    code = forms.CharField(label="验证码", widget=forms.TextInput())

    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']
        # 这里改为first(), 而不是exsits(), 目的是将user_object直接return给self.cleaned_data，后续可以根据self.cleaned_data直接取user_object, 而不用再做一次查询
        user_object = UserInfo.objects.filter(mobile_phone=mobile_phone).first()    # 搜索出来可能存在多个，只取QuerySet里第一个符合条件的，这次搜索QuerySet里只有一个
        if not user_object:
            raise ValidationError('该手机号不存在')
        return user_object

    # 验证码钩子函数
    def clean_code(self):
        # 获取验证码
        code = self.cleaned_data['code']
        # 获取手机号
        user_object = self.cleaned_data.get("mobile_phone")     # 由于上一个mobile_phone的钩子函数返回的是user_object，cleaned_data放入的就是"mobile_phone"：user_object
        if not user_object:    # 手机号不存在，验证码不用继续校验
            return code
        conn = get_redis_connection()
        ver_code = conn.get(user_object.mobile_phone)
        if not ver_code:   # 如果在redis取到手机对应的验证码为空(其实就是用户没有点击获取验证码, 随便输入了一个验证码)
            raise ValidationError("该验证码无效")
        if code.strip() != ver_code.decode("utf-8"):    # 如果用户在输入验证码后加了一个空格也让通过，比较省事, 免得去debug空格问题
            raise ValidationError("验证码错误")


class LoginForm(BootstrapForm, forms.Form):
    username = forms.CharField(label='用户名或邮箱')
    password = forms.CharField(label='密码',
                               widget=forms.PasswordInput(render_value=True),   #加了render_value=True后, 验证码填错后点击了登录, 刚输的密码不会清空
                               min_length=8,
                               validators=[RegexValidator(r'^[a-zA-Z0-9]+.*', '密码必须字母结合数字,不小于8位')])
    code = forms.CharField(label='验证码')

    def __init__(self, request, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_code(self):
        """ 读取用户输入的图片验证码是否正确 """
        # 1. 读取用户输入的验证码
        code = self.cleaned_data.get("code")
        # 2. 获取session里的验证码
        session_code = self.request.session.get("image_code")
        if not session_code:
            raise ValidationError("验证码已失效, 请重新获取")
        if code.strip().upper() != session_code.strip().upper():    # 加入upper不区分大小写字母
            raise ValidationError("验证码输入错误")
        return code

    def clean_password(self):
        # print(self.cleaned_data)    # {'username': 'test', 'password': '123', 'confirm_password': '456'}
        password_context = self.cleaned_data.get("password")
        # return 的数据会作为value直接写入到cleaned_data里的'confirm_password', 如果return "333", 那'confirm_password':'333',最后save进数据库的也是return的值
        return md5(password_context)    # 加密密码并返回

class ModifyPasswordForm(BootstrapForm, forms.ModelForm):
    origin_password = forms.CharField(widget=forms.PasswordInput(), label="原密码", min_length=8, validators=[RegexValidator(r'^[a-zA-Z0-9]+.*', '密码必须字母结合数字,不小于8位')])
    password = forms.CharField(widget=forms.PasswordInput(), label="新密码", min_length=8, validators=[RegexValidator(r'^[a-zA-Z0-9]+.*', '密码必须字母结合数字,不小于8位')])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': "请输入密码"}), label="确认密码")
    class Meta:
        model = UserInfo
        fields = ["origin_password", "password", "confirm_password"]

    # 钩子方法clean_fileds, 对confirm_password字段进行设置
    def clean_password(self):
        # print(self.cleaned_data)    # {'username': 'test', 'password': '123', 'confirm_password': '456'}
        password_context = self.cleaned_data.get("password")
        # return 的数据会作为value直接写入到cleaned_data里的'confirm_password', 如果return "333", 那'confirm_password':'333',最后save进数据库的也是return的值
        return md5(password_context)    # 加密密码并返回

    # 钩子方法clean_fileds, 对confirm_password字段进行设置
    def clean_confirm_password(self):
        # print(self.cleaned_data)    # {'username': 'test', 'password': '123', 'confirm_password': '456'}
        password_context = self.cleaned_data.get("password")    # 在feilds里password字段在前面，上面return md5(password_context)后这里已经是密文了
        confirm_password_context = md5(self.cleaned_data.get("confirm_password"))
        if password_context != confirm_password_context:
            raise ValidationError("两次输入密码不一致")
        # return 的数据会作为value直接写入到cleaned_data里的'confirm_password', 如果return "333", 那'confirm_password':'333',最后save进数据库的也是return的值
        return confirm_password_context
