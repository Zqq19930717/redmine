"""redmine URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    # # 加了namespace 后， app_redmine的urls里的name只能写成 app_redmine:register, 避免和app_web重复
    path("", include("app_web.urls"))                 # 这个项目只有两个app, "^/" 其他任意开头的取app_web.urls
]
