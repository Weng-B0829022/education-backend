import logging
from rest_framework.views import APIView
from django.views import View
from django.http import FileResponse, HttpResponseNotFound, HttpResponseBadRequest, StreamingHttpResponse, JsonResponse
from django.conf import settings
from news_storyboard.services.news_service import execute_news_gen_img, combine_media, execute_upload_to_drive
import traceback
import os
import json
import logging
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# Create your views here.


class NewsGenImgView(APIView):
    def post(self, request):
        # 從請求中獲取 index 參數，如果沒有提供則默認為 0
        index = request.query_params.get('index', 0)
        try:
            # 將 index 轉換為整數
            index = int(index)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid index. Must be an integer.'
            }, status=400)
    
        # 調用執行函數，傳入 index 參數
        result = execute_news_gen_img(index)
        
        if result['status'] == 'success':
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse(result, json_dumps_params={'ensure_ascii': False}, status=500)


class NewsGenVideoView(APIView):
    def post(self, request):
        story_object = request.data.get('story_object')
        if not story_object:
            return JsonResponse({'error': 'Missing story_object parameter'}, status=400)
        
        # 直接執行 start_data_collection 並獲取 image_urls
        try:
            random_id, image_urls = combine_media(story_object)
        except Exception as e:
            print(f"Error in combine_media: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': 'Internal server error'}, status=500)
        # 立即返回 image_urls 給前端
        return JsonResponse({'message': 'Image generation completed', 'image_urls': image_urls, 'random_id': random_id}, status=200)

class GetGeneratedVideoView(View):
    def get(self, request):
        id = request.GET.get('id')
        
        if not id:
            logger.warning("Missing id parameter in request")
            return HttpResponseBadRequest("Missing id parameter")

        video_dir = os.path.join(settings.MEDIA_ROOT, 'generated', id)

        # 確保目錄存在
        if not os.path.exists(video_dir):
            logger.warning(f"Directory not found: {video_dir}")
            return HttpResponseNotFound("Video directory not found")

        # 搜尋包含 'final_video' 的檔案
        final_video_file = None
        for filename in os.listdir(video_dir):
            if 'final_video' in filename:
                final_video_file = filename
                break

        if final_video_file:
            video_path = os.path.join(video_dir, final_video_file)
            logger.info(f"Serving video file: {video_path}")
            return FileResponse(open(video_path, 'rb'), content_type='video/mp4')
        else:
            logger.warning(f"Final video file not found in directory: {video_dir}")
            return HttpResponseNotFound("Final video not found")

class NewsUploadView(APIView):
    def post(self, request):
        try:
            random_id = request.data.get('random_id')
            execute_upload_to_drive(random_id)
            
            # 確保返回 Response
            return Response({
                "message": "Upload successful",
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

