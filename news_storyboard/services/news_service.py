from .news_gen_voice_and_video import run_news_gen_voice_and_video
from .upload_to_bucket import upload_to_bucket
import os 
from django.conf import settings
from .create_scene import create_videos_from_images_and_audio
from .storyboard_manager import StoryboardManager
import shutil
from PIL import Image, ImageDraw, ImageFont
import os
import random
import string
from concurrent.futures import ThreadPoolExecutor
from .config import HALF_CONFIG, FULL_CONFIG
import re

def execute_news_gen_img(manager, storyboard_object, random_id, scene_coordinates):
    try:
        # 準備模擬的結果
        processed_result = []
        img_binary = []
        
        # 為每個段落創建一個假的結果
        safe_title = re.sub(r'[^\w\-_\. ]', '_', storyboard_object['title'])
        for i in range(len(storyboard_object['storyboard'])):
            image_name = f'{safe_title}_{i+1}.png'
            # 添加 URL
            processed_result.append({
                "url": image_name,
            })
            # 添加空的二進制數據（因為圖片已經保存了）
            img_binary.append(b"")
        
        return (img_binary, processed_result)
    except Exception as e:
        print(str(e))
        return (None, {"status": "error", "message": str(e)})

def execute_news_gen_voice_and_video(manager, storyboard_object, random_id, avatar_coordinates):
    try:
        print(storyboard_object)
        audios_path = run_news_gen_voice_and_video(manager, storyboard_object, random_id, avatar_coordinates)

        return audios_path
    except Exception as e:
        return [""]  # 返回一个包含空字符串的列表，表示出错

def combine_media(story_object, uploaded_images):
    def generate_random_id(length=10):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def setup_image(manager, random_id, image_name, config_item, copy_image=True):
        top_left = config_item['top_left']
        top_right = config_item['top_right']
        bottom_right = config_item['bottom_right']
        bottom_left = config_item['bottom_left']
        z_index = config_item['z_index']
        # Set the image configuration
        manager.set_image_config(image_name, top_left, top_right, bottom_right, bottom_left, z_index)
        # Add the configuration to all paragraphs
        manager.add_config_to_all_paragraphs()
        
        if copy_image:
            # Copy the background image to the output directory
            source_path = os.path.join(settings.BASE_DIR, image_name)
            destination_path = os.path.join(settings.BASE_DIR, 'generated', str(random_id), image_name)
            shutil.copy2(source_path, destination_path)

    story_object['storyboard'] = story_object['storyboard'][:]
    random_id = generate_random_id()
    remove_generated_folder()
    manager = execute_storyboard_manager(os.path.join(settings.MEDIA_ROOT, 'generated', random_id), random_id, story_object)
    
    config = HALF_CONFIG if manager.storyboard['avatarType'] == 'half' else FULL_CONFIG
    canvas_size = config['canvas_size']
    scene_place_coordinates = config['scene_place_coordinates']
    avatar_place_coordinates = config['avatar_place_coordinates']
    crop_coords = config['crop_coords']

    try:
        # 保存上傳的圖片並添加到 storyboard
        output_dir = os.path.join(settings.MEDIA_ROOT, 'generated', random_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # 處理圖片並生成 image_urls
        image_urls = []
        for i, image in enumerate(uploaded_images):
            # 使用與原本相同的命名規則
            safe_title = re.sub(r'[^\w\-_\. ]', '_', story_object['title'])
            image_name = f'{safe_title}_{i+1}.png'
            image_path = os.path.join(output_dir, image_name)
            
            # 保存圖片
            with open(image_path, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            
            # 添加圖片配置到對應的段落
            image_info = {
                "img_path": image_name,
                "top_left": scene_place_coordinates["top_left"],
                "top_right": scene_place_coordinates["top_right"],
                "bottom_right": scene_place_coordinates["bottom_right"],
                "bottom_left": scene_place_coordinates["bottom_left"],
                "z_index": 0
            }
            manager.storyboard["storyboard"][i]["images"] = [image_info]
            
            # 添加到 image_urls
            image_urls.append({"url": image_name})

        with ThreadPoolExecutor(max_workers=1) as executor:
            future_voice_and_video = executor.submit(
                execute_news_gen_voice_and_video, 
                manager, 
                manager.storyboard, 
                random_id, 
                avatar_place_coordinates
            )

        # 設定背景和其他靜態元素
        setup_image(manager, random_id, config['background']['file'], config['background'], copy_image=True)
        title_img_path = text_to_image(
            manager.storyboard['title'], 
            os.path.join(settings.BASE_DIR, 'font', "NotoSansTC-Bold.ttf"),
            os.path.join(settings.BASE_DIR, 'generated', str(random_id), "title.png"),
            padding=5
        )
        setup_image(manager, random_id, "title.png", config['title'], copy_image=False)
        international_img_path = text_to_image(
            "萬象新聞", 
            os.path.join(settings.BASE_DIR, 'font', "NotoSansTC-Bold.ttf"),
            os.path.join(settings.BASE_DIR, 'generated', str(random_id), "international.png"),
            padding=5
        )
        setup_image(manager, random_id, "international.png", config['international'], copy_image=False)

        # 等待語音生成完成
        audios_path = future_voice_and_video.result()
        video_paths = create_videos_from_images_and_audio(manager, canvas_size, crop_coords)
        
        return random_id, image_urls
    except Exception as e:
        print(f"Error in media generation: {str(e)}")
        return None, None

def execute_storyboard_manager(file_path, random_id, initial_storyboard=None):
    return StoryboardManager(file_path, random_id, initial_storyboard)

def text_to_image(text, font_path, output_path, font_size=32, padding=0, bg_color=(255, 255, 255, 0), text_color=(255, 255, 255, 255)):
    # 使用絕對路徑
    absolute_output_path = os.path.abspath(output_path)
    
    # 創建完整的目錄結構
    os.makedirs(os.path.dirname(absolute_output_path), exist_ok=True)
    
    # 檢查字體文件是否存在
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # 設置字體
    try:
        # Load a bold font if available
        font = ImageFont.truetype(font_path, font_size)
        print("Font loaded successfully")
    except Exception as e:
        print(f"Error loading font: {str(e)}")
        raise

    # 獲取文字大小
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    print(f"Text dimensions: {text_width}x{text_height}")

    # 創建一個比文字稍大的 PIL 圖像
    image_width = text_width + 2 * padding
    image_height = text_height + 2 * padding
    pil_image = Image.new('RGBA', (image_width, image_height), bg_color)
    print(f"Image created with dimensions: {image_width}x{image_height}")

    # 創建一個可以在 PIL 圖像上繪圖的對象
    draw = ImageDraw.Draw(pil_image)

    # 在圖像上繪製文字（位置考慮內邊距）
    # Adjust the text position to move it upwards
    text_y_position = padding - bbox[1]  # Adjust by the top of the bounding box
    draw.text((padding, text_y_position), text, font=font, fill=text_color)
    print("Text drawn on image")

    # 直接保存 PIL 图像
    try:
        pil_image.save(absolute_output_path, format='PNG')
        print(f"Image saved successfully to: {absolute_output_path}")
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        raise
    return absolute_output_path, image_width, image_height

def execute_upload_to_drive(random_id):
    file_id = upload_to_bucket(random_id)
    return {"status":"success", "file_id":file_id}

def remove_generated_folder():
    generated_path = os.path.join(settings.BASE_DIR, 'generated')
    
    if os.path.exists(generated_path):
        try:
            shutil.rmtree(generated_path)
            print(f"'generated' folder has been successfully removed from {settings.BASE_DIR}")
        except Exception as e:
            print(f"Error occurred while trying to remove 'generated' folder: {e}")
    else:
        print(f"'generated' folder does not exist in {settings.BASE_DIR}")
