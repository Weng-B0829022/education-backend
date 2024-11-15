from django.urls import path
from .views import (
    NewsStreamView
)

urlpatterns = [
    path('generator/execute-generate-storyboard', NewsStreamView.as_view(), name='execute_generate_storyboard'),
]