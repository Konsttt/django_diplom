"""
URL configuration for django_diplom project.

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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from backend.views import redirect_login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('backend.urls', namespace='backend')),
    # Удобная api-документация
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('', include('social_django.urls')),
    # По умолчанию запросы social_django завершаются на "родных" джанговских темплейтах, импортируем их
    path('accounts/', include('django.contrib.auth.urls')),
    # Редирект с джанговского темплейта на свой темплейт с логином
    path('accounts/profile/', redirect_login_view),
    # Удобный анализатор запросов
    path('silk/', include('silk.urls', namespace='silk'))
]
