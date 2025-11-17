"""
URL configuration for eyehospital project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
from django.views.static import serve
import os

# Favicon视图函数
def favicon_view(request):
    # 尝试不同的静态文件路径
    static_dirs = [
        settings.STATIC_ROOT,
        os.path.join(settings.BASE_DIR, 'static'),
        os.path.join(settings.BASE_DIR, 'cases', 'static'),
    ]
    
    for static_dir in static_dirs:
        if static_dir and os.path.exists(static_dir):
            # 首先尝试favicon.svg
            favicon_path = os.path.join(static_dir, 'favicon.svg')
            if os.path.exists(favicon_path):
                return FileResponse(open(favicon_path, 'rb'), content_type='image/svg+xml')
            
            # 然后尝试logo.png作为备选
            logo_path = os.path.join(static_dir, 'logo.png')
            if os.path.exists(logo_path):
                return FileResponse(open(logo_path, 'rb'), content_type='image/png')
    
    # 如果都没找到，返回一个简单的响应
    from django.http import HttpResponse
    return HttpResponse("Favicon not found", status=404)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('favicon.ico', favicon_view, name='favicon'),
    path('', include('cases.urls')),
]

# 开发环境下处理媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
