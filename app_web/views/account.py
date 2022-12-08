import uuid
import datetime

from io import BytesIO
from django.shortcuts import render, HttpResponse, redirect
from django.http import JsonResponse
from django.views.generic import View
from django.urls import reverse
from django.db.models import Q

from app_web.forms.account import RegisterModelForm, SendSmsForm, LoginSMSForm, LoginForm
from utils.verification_code import check_code
from app_web.models import UserInfo, Transaction, PricePolicy
# Create your views here.

class send_sms(View):
    """ 发送短信
        url + ?tpl=login -> 1464268
        url + ?tpl=register -> 1464270
    """

    def get(self, request):
        form = SendSmsForm(request, data=request.GET)
        # 只是校验手机号不能为空，且符合手机号正则表达式
        if form.is_valid():
            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False, "error": form.errors})



class register(View):
    """ 注册页面 """
    def get(self, request):
        register_form = RegisterModelForm()
        return render(request, 'app_web/register.html', {"register_form": register_form})

    def post(self, request):
        register_form = RegisterModelForm(data=request.POST)
        if register_form.is_valid():
            # 用户注册后新保存一条记录, instance就可以代表保存的这条用户信息记录
            instance = register_form.save()
            # 获取price_policy里的个人免费版数据对象
            policy_object = PricePolicy.objects.filter(category=1, title="个人免费版").first()
            # 根据创建的用户记录instance来创建用户的交易记录
            Transaction.objects.create(
                status=2,
                order=uuid.uuid4(),
                user=instance,
                price_policy=policy_object,
                count=0,
                price=0,
                create_datetime=datetime.datetime.now()
            )
            return JsonResponse({"status": True, 'data': reverse('login_sms')})
        else:
            return JsonResponse({"status": False, "error": register_form.errors})


class login_sms(View):
    """ 短信登录页面 """
    def get(self, request):
        form = LoginSMSForm()
        return render(request, "app_web/login_sms.html", {"form": form})

    def post(self, request):
        login_sms_form = LoginSMSForm(data=request.POST)
        if login_sms_form.is_valid():
            # 用户输入正确，登录成功
            user_object = login_sms_form.cleaned_data.get("mobile_phone")
            # 将用户登录信息放入session
            request.session["user_id"] = user_object.id
            # print(reverse("index"))     # 输出/index/
            return JsonResponse({"status": True, 'data': reverse("index")})
        else:
            return JsonResponse({"status": False, "error": login_sms_form.errors})

class login(View):
    """ 用户名密码登录 """
    def get(self, request):
        form = LoginForm(request=request)
        return render(request, "app_web/login.html", {"form": form})

    def post(self, request):
        form = LoginForm(data=request.POST, request=request)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            # user_object = UserInfo.objects.filter(username=username, password=password).first()
            # 使用用户名或邮箱登录，手机号方式支持使用短信登录
            user_object = UserInfo.objects.filter(Q(username=username) | Q(email=username)).filter(password=password).first()
            # 手机或邮箱登录, 用Q查询, 下面一句取消注释，然后form里的username字段里的label = "手机号或邮箱" 即可
            # user_object = UserInfo.objects.filter(Q(mobile_phone=username)|Q(email=username)).filter(password=password).first()
            if user_object:
                # 登陆成功, 将用户登录信息放入session
                request.session["user_id"] = user_object.id
                # 设置用户信息保存在session里超时时间为2周
                request.session.set_expiry(60*60*24*14)
                return redirect(reverse('index'))
            else:
                form.add_error('username', "用户名或密码错误")
        return render(request, "app_web/login.html", {"form": form})

class image_code(View):
    """ 生成图片验证码 """
    def get(self, request):
        # 调用基于pillow写的函数生成验证码图片, code_str就是随机生成的验证码字符串
        img_obj, code_str = check_code()
        # 写入到session中（以便于后续获取该验证码并进行校验）
        request.session['image_code'] = code_str
        # 给该session设置一个60秒超时
        request.session.set_expiry(60)

        # 将img_obj写入到内存中
        stream = BytesIO()
        img_obj.save(stream, 'png')  # 文件保存在内存中
        # stream.getvalue()   # 再从内存中获取原始的img数据
        return HttpResponse(stream.getvalue())

class logout(View):
    """ 用户注销 """
    def get(self, request):
        request.session.flush() # 将session中的数据清空
        return redirect(reverse('index'))
