import os
import json
import time
import requests
import random
from google import genai
from google.genai import types

# ======================================================
# [설정 1] 사용자 환경 설정 (여기만 고치세요!)
# ======================================================
GEMINI_API_KEY = "AIzaSyCx3y1TCsIuq6RCGIBrL4IAya1qJGajDBQ"

# ComfyUI가 그림을 저장하는 폴더 (본인 경로로 수정 필수!)
# 보통: ComfyUI_windows_portable\ComfyUI\output
COMFY_OUTPUT_DIR = r"D:\ComfyUI\output" 

# ComfyUI 서버 주소
COMFY_URL = "http://127.0.0.1:8188/prompt"

# 아까 찾은 노드 번호 (ID)
NODE_ID_PROMPT = "6"  # 긍정 프롬프트(초록상자) 번호
NODE_ID_SEED = "3"    # KSampler 번호

# ======================================================
# [설정 2] 시스템 초기화
# ======================================================
client = genai.Client(api_key=GEMINI_API_KEY)
base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, "final_result")

# 템플릿 파일 경로
template_cover_path = os.path.join(base_dir, "template.html")
template_content_path = os.path.join(base_dir, "template_content.html")

# ======================================================
# 1. Gemini: 대본과 그림 묘사를 동시에 생성
# ======================================================
def get_full_plan(keywords):
    print(f"🧠 Gemini가 '{keywords}' 내용을 기획하고 있습니다...")

    # 프롬프트: 대본(한글) + 그림지시문(영어)을 같이 달라고 요청
    prompt = f"""
    너는 카드뉴스 PD야. 아래 키워드를 바탕으로 5장짜리 카드뉴스를 기획해줘.
    
    [입력 키워드]
    {keywords}
    
    [필수 요청사항]
    1. 각 슬라이드의 '제목', '내용(한글)', '그림 프롬프트(영어)'를 작성해.
    2. 그림 프롬프트는 ComfyUI용이므로 'Pororo animation style, 3d render, cute, vivid colors' 같은 스타일 태그를 꼭 포함해서 구체적으로 묘사해줘.
    3. 반드시 아래 JSON 형식으로만 답해.
    
    {{
        "slides": [
            {{
                "title": "1장 표지 제목",
                "content": "부제목",
                "img_prompt": "English prompt for cover image, Pororo style, ..."
            }},
            {{
                "title": "2장 제목",
                "content": "본문 내용...",
                "img_prompt": "English prompt for slide 2, ..."
            }},
            {{
                "title": "3장 제목",
                "content": "본문 내용...",
                "img_prompt": "English prompt for slide 3, ..."
            }},
            {{
                "title": "4장 제목",
                "content": "본문 내용...",
                "img_prompt": "English prompt for slide 4, ..."
            }},
            {{
                "title": "5장 제목",
                "content": "마무리 멘트",
                "img_prompt": "English prompt for outro, ..."
            }}
        ]
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        return data.get("slides", [])
    except Exception as e:
        print(f"❌ 기획 중 에러 발생: {e}")
        return []

# ======================================================
# 2. ComfyUI: 이미지 생성 요청 및 대기
# ======================================================
def generate_images(slides):
    print("\n🎨 ComfyUI에게 그림 5장을 그리라고 시킵니다...")
    
    # 워크플로우 파일 읽기
    try:
        with open("workflow_api.json", "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        print("❌ 'workflow_api.json' 파일이 없습니다!")
        return []

    # 생성 전, 현재 폴더에 있는 파일 목록 기억 (새 파일 찾기 위해)
    existing_files = set(os.listdir(COMFY_OUTPUT_DIR))
    generated_image_paths = []

    for i, slide in enumerate(slides, 1):
        prompt_text = slide['img_prompt']
        print(f"   [{i}장] 그림 생성 중... (프롬프트: {prompt_text[:30]}...)")
        
        # (1) 프롬프트 입력
        workflow[NODE_ID_PROMPT]["inputs"]["text"] = prompt_text
        
        # (2) 시드 변경 (랜덤)
        if NODE_ID_SEED in workflow:
            workflow[NODE_ID_SEED]["inputs"]["seed"] = random.randint(1, 9999999999)
        
        # (3) 서버로 전송
        try:
            requests.post(COMFY_URL, json={"prompt": workflow})
        except:
            print("❌ ComfyUI 서버가 꺼져있는 것 같습니다. (http://127.0.0.1:8188)")
            return []
            
        # (4) 그림 다 그려질 때까지 대기 (파일이 생길 때까지 감시)
        # 단순하게 5~10초 대기 후 가장 최신 파일 가져오기
        time.sleep(6) # 컴퓨터 속도에 따라 늘리세요 (초 단위)
    
    # 생성 후 파일 확인 (최신순 정렬)
    # 팁: 방금 생성된 5장을 확실히 가져오기 위해 시간순 정렬
    all_files = [os.path.join(COMFY_OUTPUT_DIR, f) for f in os.listdir(COMFY_OUTPUT_DIR) 
                 if f.lower().endswith(('.png', '.jpg'))]
    all_files.sort(key=os.path.getmtime, reverse=True) # 최신이 위로
    
    # 최신 5장 가져오기 (순서가 거꾸로이므로 뒤집어야 함)
    # 생성순서: 1->2->3->4->5. 리스트: [5, 4, 3, 2, 1]. 뒤집으면 [1, 2, 3, 4, 5]
    new_images = all_files[:5]
    new_images.reverse()
    
    if len(new_images) < 5:
        print("⚠️ 경고: 이미지가 5장 미만으로 생성되었습니다. 시간을 더 늘려보세요.")
    
    return new_images

# ======================================================
# 3. HTML 합체: 텍스트 + 이미지
# ======================================================
def create_html_result(slides, image_paths, topic):
    print(f"\n📑 최종 카드뉴스 HTML을 조립합니다...")
    
    # 저장 폴더 만들기
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    save_folder = os.path.join(output_dir, f"{topic}_{timestamp}")
    os.makedirs(save_folder, exist_ok=True)
    
    # 템플릿 읽기
    with open(template_cover_path, "r", encoding="utf-8") as f: cover_tpl = f.read()
    with open(template_content_path, "r", encoding="utf-8") as f: content_tpl = f.read()
    
    for i, slide in enumerate(slides):
        title = slide['title']
        content = slide['content'].replace("\n", "<br>") # 줄바꿈 처리
        
        # 이미지 경로 (없으면 빈칸)
        img_path = image_paths[i] if i < len(image_paths) else ""
        
        # HTML 내용 치환
        if i == 0: # 표지
            html = cover_tpl.replace("{{ title }}", title).replace("{{ content }}", content)
        else: # 내용
            html = content_tpl.replace("{{ title }}", title).replace("{{ content }}", content)
            
            # [중요] 브라우저에서 로컬 이미지 보이게 하려면 'file://' 접두사 필요할 수 있음
            # 일단 절대 경로 그대로 넣습니다.
            html = html.replace("{{ image_path }}", img_path)
            
        # 파일 저장
        filename = f"{save_folder}/slide_{i+1:02d}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
            
    print(f"✨ 작업 완료! 결과물 폴더: {save_folder}")

# ======================================================
# 실행
# ======================================================
if __name__ == "__main__":
    # 사용자 입력 예시
    user_input = input("키워드를 입력하세요 (예: 부산 북극곰축제, 뽀로로 스타일, 12월 25일): ")
    
    # 1. 기획 (글+프롬프트)
    slides_data = get_full_plan(user_input)
    
    if slides_data:
        # 2. 그림 생성
        generated_images = generate_images(slides_data)
        
        # 3. 합체
        create_html_result(slides_data, generated_images, user_input.split()[0])