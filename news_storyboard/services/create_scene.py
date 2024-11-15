import cv2
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, ImageClip
from moviepy.editor import concatenate_videoclips
import os
from django.conf import settings
from PIL import Image

def combine_videos(title, output_dir, num_paragraphs):
    """
    Combines multiple video clips into a single video file.
    
    :param output_dir: Directory containing the input video files and where the output will be saved
    :param num_paragraphs: Number of video clips to combine
    """
    from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeAudioClip
    import gc
    import os

    video_clips = []
    
    for i in range(1, num_paragraphs + 1):
        video_path = os.path.join(output_dir, f"final_output_paragraph_{i}.mp4")
        
        # 檢查視頻文件是否存在
        if not os.path.exists(video_path):
            print(f"Warning: Video file {video_path} does not exist.")
            continue
        
        try:
            video = VideoFileClip(video_path)
            
            # 檢查視頻是否有音頻
            if video.audio is None:
                print(f"Warning: Video {i} does not have audio.")
            
            video_clips.append(video)
        
        except Exception as e:
            print(f"Error loading video {video_path}: {str(e)}")
            continue
        
        # 釋放不必要的資源
        gc.collect()
    
    # 確保有視頻片段可供合併
    if not video_clips:
        print("No valid video clips found to combine.")
        return None
    
    # 合併所有視頻片段
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 確保最終視頻有音頻，必要時創建靜音音軌
    if final_video.audio is None:
        print("Warning: The combined video does not have audio. Creating a silent audio track.")
        final_video = final_video.set_audio(CompositeAudioClip([]))
    
    final_output_path = os.path.join(output_dir, f"{title}_final_video.mp4")
    
    # 寫入最終視頻文件
    try:
        final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac", threads=4)
    except Exception as e:
        print(f"Error writing final video: {str(e)}")
    
    # 關閉所有視頻片段以釋放資源
    for clip in video_clips:
        clip.close()
    
    print(f"All videos combined into: {final_output_path}")

def compose_background_with_scenes(output_dir, images, canvas_size):
    """
    Composes multiple images based on their z-index and coordinates.
    Memory-efficient and numerically stable implementation.
    """
    import gc
    
    # 強制初始清理
    gc.collect()
    
    try:
        # 使用 float32 提供足夠的精度但不過度消耗記憶體
        canvas = np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.float32)
        
        # Sort images by z-index
        sorted_images = sorted(images, key=lambda x: x.get('z_index', 0))
        
        for img_info in sorted_images:
            try:
                img_path = os.path.join(output_dir, img_info["img_path"])
                
                # 使用 PIL 讀取並立即轉換格式
                with Image.open(img_path) as pil_img:
                    # 轉換為 RGBA
                    if pil_img.mode != 'RGBA':
                        pil_img = pil_img.convert('RGBA')
                    # 轉換為 numpy array 並正規化
                    img = np.array(pil_img, dtype=np.float32) / 255.0
                
                # 立即清理 PIL 圖片
                del pil_img
                
                # 獲取座標
                tl = np.array(img_info["top_left"], dtype=np.float32)
                tr = np.array(img_info["top_right"], dtype=np.float32)
                br = np.array(img_info["bottom_right"], dtype=np.float32)
                bl = np.array(img_info["bottom_left"], dtype=np.float32)
                
                # 創建透視變換矩陣
                src_pts = np.array([[0, 0], 
                                  [img.shape[1]-1, 0], 
                                  [img.shape[1]-1, img.shape[0]-1], 
                                  [0, img.shape[0]-1]], dtype=np.float32)
                dst_pts = np.array([tl, tr, br, bl], dtype=np.float32)
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                
                # 執行透視變換
                warped_img = cv2.warpPerspective(
                    img,
                    M,
                    (canvas_size[0], canvas_size[1]),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0,0,0,0)
                )
                
                # 清理不需要的變量
                del img, M, src_pts, dst_pts
                gc.collect()
                
                # 提取 alpha 通道
                alpha = warped_img[:, :, 3]
                alpha = np.clip(alpha, 0, 1)  # 確保 alpha 在有效範圍內
                
                # 使用 numpy 的廣播功能進行混合
                for c in range(3):  # 分別處理 RGB 通道
                    canvas[:, :, c] = (warped_img[:, :, c] * alpha + 
                                     canvas[:, :, c] * (1 - alpha))
                
                # 更新 alpha 通道
                canvas[:, :, 3] = np.maximum(canvas[:, :, 3], warped_img[:, :, 3])
                
                # 清理本次迭代的變量
                del warped_img, alpha
                gc.collect()
                
            except Exception as e:
                print(f"Error processing image {img_path}: {str(e)}")
                continue
        
        # 確保值在有效範圍內並轉換回 uint8
        result = (np.clip(canvas[:, :, :3], 0, 1) * 255).astype(np.uint8)
        
        return result
        
    except Exception as e:
        print(f"Error in compose_background_with_scenes: {str(e)}")
        return None
        
    finally:
        # 確保清理所有變量
        try:
            del canvas
        except:
            pass
        gc.collect()

def avatar_2_background(input_video, output_video, threshold, composed_background, crop_coords, placement_coords):
    """
    Replaces the background of a video with a composed background image.
    
    :param input_video: Path to the input video file
    :param output_video: Path to save the output video file
    :param threshold: Threshold for background removal
    :param composed_background: Composed background image
    :param crop_coords: Coordinates for cropping the input video
    :param placement_coords: Coordinates for placing the video on the background
    """
    cap = cv2.VideoCapture(input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    x, y, w, h = crop_coords
    bg_height, bg_width = composed_background.shape[:2]
    tl, tr, br, bl = placement_coords
    
    placed_width = int(max(tr[0], br[0]) - min(tl[0], bl[0]))
    placed_height = int(max(bl[1], br[1]) - min(tl[1], tr[1]))
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_output = os.path.join(os.path.dirname(output_video), f'temp_{os.path.basename(output_video)}')
    out = cv2.VideoWriter(temp_output, fourcc, fps, (bg_width, bg_height), isColor=True)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process each frame
        frame = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (placed_width, placed_height))
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        mask = np.where(gray < threshold, 0, 255).astype('uint8')
        blurred_mask = cv2.GaussianBlur(mask, (21, 21), 0).astype(float) / 255.0
        
        foreground = frame * blurred_mask[:,:,np.newaxis]
        bg_copy = composed_background.copy()
        
        # Create a perspective transform matrix
        src_pts = np.array([[0, 0], [placed_width-1, 0], [0, placed_height-1], [placed_width-1, placed_height-1]], dtype="float32")
        dst_pts = np.array([tl, tr, bl, br], dtype="float32")
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # Warp the foreground and mask
        warped_foreground = cv2.warpPerspective(foreground, M, (bg_width, bg_height))
        warped_mask = cv2.warpPerspective(blurred_mask, M, (bg_width, bg_height))
        
        # Blend foreground with background
        alpha = 1 - warped_mask[:,:,np.newaxis]
        blended = bg_copy * alpha + warped_foreground
        
        out.write(cv2.cvtColor(blended.astype(np.uint8), cv2.COLOR_RGB2BGR))
    
    cap.release()
    out.release()
    
    # Add original audio to the processed video
    video = VideoFileClip(temp_output)
    audio = AudioFileClip(input_video)
    final_video = video.set_audio(audio)
    final_video.write_videofile(output_video, codec="libx264", audio_codec="aac")
    
    video.close()
    audio.close()
    os.remove(temp_output)



def create_videos_from_images_and_audio(manager, canvas_size, crop_coords):
    """
    Creates videos by combining background images, scene images, and audio (with or without avatar videos).
    
    :param manager: Manager object containing the storyboard and other necessary information
    :param canvas_size: Size of the canvas (width, height)
    :param crop_coords: Coordinates for cropping the input video (x, y, w, h)
    """
    storyboard = manager.get_storyboard()
    title = storyboard.get('title')
    output_dir = os.path.join(settings.BASE_DIR, 'generated', storyboard['random_id'])
    
    for idx, paragraph in enumerate(storyboard["storyboard"]):
        print(f"Processing paragraph {idx + 1}...")
        
        # Compose background with all images
        composed_background = compose_background_with_scenes(output_dir, paragraph["images"], canvas_size)
        if composed_background is None:
            print(f"Error: Failed to compose background for paragraph {idx + 1}")
            continue
        
        # Check if avatar is needed
        if paragraph.get("needAvatar", False):
            # Process video with avatar
            input_video = os.path.join(output_dir, paragraph["video"]["avatar_path"])
            output_video = os.path.join(output_dir, f"final_output_paragraph_{idx + 1}.mp4")
            placement_coords = (paragraph["video"]["top_left"], paragraph["video"]["top_right"], paragraph["video"]["bottom_right"], paragraph["video"]["bottom_left"])
            
            avatar_2_background(input_video, output_video, 10, composed_background, crop_coords, placement_coords)
        else:
            # Create video from background image and audio
            output_video = os.path.join(output_dir, f"final_output_paragraph_{idx + 1}.mp4")
            audio_path = os.path.join(output_dir, paragraph["audio_path"])
            create_video_from_image_and_audio(composed_background, audio_path, output_video)
        
        print(f"Video processing complete for paragraph {idx + 1}")
    
    print("All videos processed successfully!")

    # Combine all videos into one final video
    num_paragraphs = len(storyboard["storyboard"])
    combine_videos(title, output_dir, num_paragraphs)
    
    print("Final combined video created successfully!")


# New function to create video from image and audio
def create_video_from_image_and_audio(image, audio_path, output_path, fps=24):
    """
    Creates a video from a static image and an audio file.
    
    :param image: The background image (numpy array)
    :param audio_path: Path to the audio file
    :param output_path: Path to save the output video
    :param fps: Frames per second for the output video (default is 24)
    """
    audio = AudioFileClip(audio_path)
    video = ImageClip(image).set_duration(audio.duration)
    video = video.set_audio(audio)
    video.fps = fps  # Set the fps for the video clip
    video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    audio.close()

if __name__ == "__main__":
    create_videos_from_images_and_audio()


