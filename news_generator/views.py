import json
from rest_framework.views import APIView
from django.http import JsonResponse
import requests
from news_generator.news_gen import run_news_gen
import re  # 在文件頂部添加
from PyPDF2 import PdfReader
import io
from rest_framework.parsers import MultiPartParser, FormParser
from news_generator.summerize import summerize_pdf_content
class NewsStreamView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        try:
            # 1. 檢查輸入數據
            content = request.data.get('text', '')
            files = request.FILES.getlist('files')
            
            print("Initial content:", content)  # 檢查初始文字內容
            print("Number of files:", len(files))  # 檢查檔案數量
            
            articles = []
            
            
            # 3. 處理 PDF 檔案
            for i, file in enumerate(files):
                print(f"Processing PDF file {i+1}")
                pdf_reader = PdfReader(io.BytesIO(file.read()))
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
                
                content = summerize_pdf_content(content + pdf_text)
                articles.append({
                    "content": content,
                    "storyboard": None
                })

            # 5. 創建最終數據結構
            processed_data = {
                "articles": articles
            }
            
            generated_content = run_news_gen(processed_data)
            print("Final processed_data:", processed_data)  # 檢查最終數據
            
            return JsonResponse({
                'status': 'success',
                'createded_content': generated_content,
            })
            
        except Exception as e:
            print("Error occurred:", str(e))  # 打印錯誤信息
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)