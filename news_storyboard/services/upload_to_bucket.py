import os
import os.path
import time
from google.cloud import storage
from google.api_core import retry
from tqdm import tqdm
from django.conf import settings
MAX_RETRIES = 3
RETRY_DELAY = 5

def get_storage_client():
    """初始化並返回 GCS client"""
    try:
        return storage.Client()
    except Exception as e:
        print(f"初始化 GCS client 時發生錯誤: {e}")
        raise

def create_folder_with_retry(bucket, folder_name, parent_path=None):
    """在 GCS 中創建一個空的 folder marker"""
    folder_path = f"{parent_path}/{folder_name}/" if parent_path else f"{folder_name}/"
    
    for attempt in range(MAX_RETRIES):
        try:
            blob = bucket.blob(folder_path)
            blob.upload_from_string('')
            return folder_path
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"創建資料夾失敗，重試中: {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise

def upload_file_with_retry(bucket, source_path, destination_path):
    """上傳單個文件到 GCS，具有重試機制"""
    for attempt in range(MAX_RETRIES):
        try:
            blob = bucket.blob(destination_path)
            blob.upload_from_filename(source_path)
            return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"上傳檔案失敗，重試中: {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise

def count_files(folder_path):
    """計算資料夾中的文件總數"""
    try:
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            total_files += len(files)
        return total_files
    except Exception as e:
        print(f"計算檔案數量時發生錯誤: {e}")
        raise

def upload_folder_contents(bucket, local_folder_path, gcs_folder_path, pbar):
    """遞迴上傳資料夾內容到 GCS"""
    try:
        for item in os.listdir(local_folder_path):
            item_path = os.path.join(local_folder_path, item)
            destination_path = f"{gcs_folder_path}/{item}" if gcs_folder_path else item
            
            try:
                if os.path.isfile(item_path):
                    upload_file_with_retry(bucket, item_path, destination_path)
                    pbar.update(1)
                elif os.path.isdir(item_path):
                    # 為資料夾創建一個marker
                    folder_path = create_folder_with_retry(bucket, item, gcs_folder_path)
                    upload_folder_contents(bucket, item_path, destination_path, pbar)
            except Exception as e:
                print(f"處理檔案 {item} 時發生錯誤: {e}")
                continue
    except Exception as e:
        print(f"讀取資料夾內容時發生錯誤: {e}")
        raise

def upload_to_bucket(id):
    """主要的上傳函數"""
    # 設置你的 Google Cloud 憑證
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "phoeney-4bac5820ef2b.json"
    
    # 設置參數
    bucket_name = "news-data-bucket"
    local_folder_path = os.path.join(settings.BASE_DIR, 'generated', f"{id}")
    gcs_base_path = "education_generated_video"  

    try:
        # 初始化 GCS client
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        
        # 確認 bucket 存在
        if not bucket.exists():
            print(f"Bucket '{bucket_name}' 不存在")
            return None, None
        
        # 計算總文件數
        total_files = count_files(local_folder_path)
        print(f"準備上傳 {total_files} 個檔案到 GCS bucket '{bucket_name}/generated'...")
        
        # 使用資料夾名稱作為 GCS 中的前綴
        base_folder_name = os.path.basename(local_folder_path)
        
        # 在 generated 文件夾下創建子文件夾
        folder_path = create_folder_with_retry(bucket, base_folder_name, gcs_base_path)
        
        # 使用進度條上傳所有文件
        with tqdm(total=total_files, unit='file') as pbar:
            upload_folder_contents(bucket, local_folder_path, f"{gcs_base_path}/{base_folder_name}", pbar)
        
        print("所有檔案和資料夾上傳完成。")
        
        # 生成公開訪問URL
        public_url = f"https://storage.googleapis.com/{bucket_name}/{folder_path}"
        
        # 返回元組 (folder_path, public_url)
        return folder_path, public_url
    
    except Exception as e:
        print(f"上傳過程中發生錯誤: {e}")
        return None, None

