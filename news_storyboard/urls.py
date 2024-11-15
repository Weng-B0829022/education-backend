from django.urls import path
from .views import (
    NewsGenVideoView,
    NewsGenImgView,
    GetGeneratedVideoView,
    NewsUploadView,
)

urlpatterns = [
    path('storyboard/execute-generate-video', NewsGenVideoView.as_view(), name='execute_news_gen_video'),
    path('storyboard/get-generated-video', GetGeneratedVideoView.as_view(), name='get_generated_videos'),  # Add this line
    path('storyboard/execute-news-upload', NewsUploadView.as_view(), name='execute_news_upload'),
]