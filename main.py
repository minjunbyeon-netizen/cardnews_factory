import os
import json
from google import genai
from google.genai import types

# ======================================================
# 1. 설정 및 초기화
# ======================================================

# 본인의 API 키를 여기에 입력하세요 (따옴표 안에)
GEMINI_API_KEY = "AIzaSyCx3y1TCsIuq6RCGIBrL4IAya1qJGajDBQ"

# 새로운 SDK 클라이언트 생성
client = genai.Client(api_key=GEMINI_API_KEY)

# 경로 설정 (사용자님 기존 코드 유지)
base_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = r"D:\comfyui\output"  # ComfyUI 출력 폴더
output_dir = os.path.join(base_dir, "output")
template_cover_path = os.path.join(base_dir, "template.html")
template_content_path = os.path.join(base_dir, "template_content.html")
# json_path = os.path.join(base_dir, GOOGLE_JSON_FILE) # 필요 시 주석 해제

# ======================================================
# 2. AI 스크립트 생성 함수 (5장 슬라이드용)
# ======================================================

def get_ai_script_5slides(topic):
    """5장 분량의 카드뉴스 콘텐츠 생성"""
    print(f"[AI] Gemini가 '{topic}' 5장 슬라이드 제작 중...")

    prompt = f"""
    너는 SNS 카드뉴스 전문 카피라이터야.
    주제: '{topic}'
    
    5장짜리 카드뉴스를 만들어줘. 각 장의 역할:
    - 1장(cover): 사람들의 시선을 끄는 표지 (제목 10자, 부제목 15자 이내)
    - 2장(point1): 첫 번째 핵심 포인트 (제목 10자, 설명 40자 이내)
    - 3장(point2): 두 번째 핵심 포인트 (제목 10자, 설명 40자 이내)
    - 4장(point3): 세 번째 핵심 포인트 (제목 10자, 설명 40자 이내)
    - 5장(outro): 마무리 및 행동 유도 (제목 10자, 부제목 15자 이내)
    
    반드시 아래 JSON 형식으로만 답변해. (마크다운, 잡담 금지)
    
    {{
        "slides": [
            {{"title": "표지 제목", "content": "짧은 부제목"}},
            {{"title": "포인트1", "content": "핵심 내용을 2문장으로 설명해줘"}},
            {{"title": "포인트2", "content": "핵심 내용을 2문장으로 설명해줘"}},
            {{"title": "포인트3", "content": "핵심 내용을 2문장으로 설명해줘"}},
            {{"title": "마무리", "content": "행동 유도 문구"}}
        ]
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        if response.text:
            data = json.loads(response.text)
            slides = data.get("slides", [])
            
            print(f"[OK] {len(slides)}장 슬라이드 생성 완료!")
            for i, slide in enumerate(slides, 1):
                print(f"  [{i}] {slide.get('title')} | {slide.get('content')}")
            
            return slides
        else:
            print("[WARN] API 응답이 비어있습니다.")
            return []

    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")
        return []

# ======================================================
# 3. HTML 카드뉴스 생성 함수 (5장 버전)
# ======================================================

def generate_card_news(topic):
    """
    주제를 받아 5장 슬라이드 카드뉴스 생성
    
    Args:
        topic: 카드뉴스 주제
    
    Returns:
        생성된 HTML 파일 경로 리스트
    """
    from datetime import datetime
    
    # 1. AI로 5장 슬라이드 콘텐츠 생성
    slides = get_ai_script_5slides(topic)
    
    if not slides:
        print("[ERROR] 슬라이드 생성 실패!")
        return []
    
    # 2. 템플릿 읽기 (표지용 + 콘텐츠용)
    with open(template_cover_path, "r", encoding="utf-8") as f:
        template_cover = f.read()
    with open(template_content_path, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    # 3. images 폴더에서 이미지 가져오기
    image_files = [f for f in os.listdir(images_dir) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))]
    image_files.sort()  # 정렬
    print(f"[IMG] 발견된 이미지: {len(image_files)}개")
    
    # 4. output 폴더 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 5. 타임스탬프 폴더 생성 (한 세트로 묶기)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    set_folder = os.path.join(output_dir, f"cardnews_{timestamp}")
    os.makedirs(set_folder, exist_ok=True)
    
    # 6. 각 슬라이드별 HTML 파일 생성
    saved_paths = []
    slide_names = ["01_cover", "02_point1", "03_point2", "04_point3", "05_outro"]
    
    for i, slide in enumerate(slides):
        title = slide.get("title", "")
        content = slide.get("content", "")
        
        if i == 0:
            # 1장: 표지 템플릿 (이미지 없음)
            html_content = template_cover.replace("{{ title }}", title)
            html_content = html_content.replace("{{ content }}", content)
        else:
            # 2~5장: 콘텐츠 템플릿 (이미지 포함)
            html_content = template_content.replace("{{ title }}", title)
            html_content = html_content.replace("{{ content }}", content)
            
            # 이미지 배정 (2장=첫번째 이미지, 3장=두번째...)
            img_index = i - 1  # 0, 1, 2, 3
            if img_index < len(image_files):
                image_path = os.path.join(images_dir, image_files[img_index])
                html_content = html_content.replace("{{ image_path }}", image_path)
            else:
                html_content = html_content.replace("{{ image_path }}", "")
        
        # 파일 저장
        filename = f"{slide_names[i]}.html"
        output_path = os.path.join(set_folder, filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        saved_paths.append(output_path)
    
    print(f"\n[DONE] 카드뉴스 5장 생성 완료!")
    print(f"[PATH] 저장 폴더: {set_folder}")
    
    return saved_paths


# ======================================================
# 4. 실행 (이 파일만 단독 실행 시 작동)
# ======================================================
if __name__ == "__main__":
    # 테스트 주제
    test_topic = "직장인 재테크 꿀팁"
    
    # 5장 카드뉴스 생성
    saved_paths = generate_card_news(test_topic)
    
    print("\n--- 최종 결과 ---")
    for path in saved_paths:
        print(f"[SAVED] {os.path.basename(path)}")