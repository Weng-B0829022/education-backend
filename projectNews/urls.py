from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('news_generator.urls')),  # 這會包含 news_generator 應用的所有 URL
    path('', include('news_storyboard.urls')),  # 這會包含 news_storyboard 應用的所有 URL
] 