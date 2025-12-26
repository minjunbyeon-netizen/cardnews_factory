import os
import json
import time
import requests
import random
import shutil
from google import genai
from google.genai import types

# ======================================================
# [설정 1] 사용자 환경 설정
# ======================================================
# ⚠️ 여기에 아까 받은 [새 API 키]를 꼭 넣으세요!
GEMINI_API_KEY = "AIzaSyCx3y1TCsIuq6RCGIBrL4IAya1qJGajDBQ"

# ComfyUI 출력 폴더 (본인 경로가 맞는지 확인!)
COMFY_OUTPUT_DIR = r"D:\ComfyUI\output" 

# ComfyUI 서버 주소
COMFY_URL = "http://127.0.0.1:8188/prompt"

# 노드 번호 (ID) - 아까 확인한 번호 (보통 프롬프트=6, 샘플러=3)
NODE_ID_PROMPT = "6"
NODE_ID_SEED = "3"

# 폴더 경로 설정 (자동)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TXT_DIR = os.path.join(BASE_DIR, "input_text")
DONE_TXT_DIR = os.path.join(BASE_DIR, "done_text")
OUTPUT_HTML_DIR = os.path.join(BASE_DIR, "final_result")

# ======================================================
# 시스템 초기화 (폴더가 없으면 자동으로 만듦)
# ======================================================
client = genai.Client(api_key=GEMINI_API_KEY)
os.makedirs(INPUT_TXT_DIR, exist_ok=True)
os.makedirs(DONE_TXT_DIR, exist_ok=True)
os.makedirs(OUTPUT_HTML_DIR, exist_ok=True)

# 템플릿 경로
template_cover_path = os.path.join(BASE_DIR, "template.html")
template_content_path = os.path.join(BASE_DIR, "template_content.html")

# ======================================================
# 1. Gemini: 텍스트 기획안 생성
# ======================================================
def get_full_plan_from_text(raw_text):
    print(f"🧠 Gemini가 내용을 분석하고 있습니다...")

    prompt = f"""
    너는 SNS 카드뉴스 전문 PD야. 
    사용자가 입력한 아래 내용을 바탕으로 5장짜리 카드뉴스를 기획해줘.
    
    [원본 텍스트]
    {raw_text}
    
    [필수 요청사항]
    1. 각 슬라이드의 '제목', '내용(한글)', '그림 프롬프트(영어)'를 작성해.
    2. 그림 프롬프트는 ComfyUI용이므로 'Pororo animation style, 3d render, cute, vivid colors' 등 원본 분위기에 맞는 스타일 태그를 꼭 넣어줘.
    3. 반드시 아래 JSON 형식으로만 답해.
    
    {{
        "slides": [
            {{
                "title": "1장 표지 제목",
                "content": "짧고 강렬한 부제목",
                "img_prompt": "English prompt for cover..."
            }},
            {{
                "title": "2장 소제목",
                "content": "핵심 내용 요약...",
                "img_prompt": "English prompt..."
            }},
            {{
                "title": "3장 소제목",
                "content": "핵심 내용 요약...",
                "img_prompt": "English prompt..."
            }},
            {{
                "title": "4장 소제목",
                "content": "핵심 내용 요약...",
                "img_prompt": "English prompt..."
            }},
            {{
                "title": "5장 마무리",
                "content": "결론 및 행동 유도",
                "img_prompt": "English prompt..."
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
# 2. ComfyUI: 이미지 생성
# ======================================================
def generate_images(slides):
    print("\n🎨 ComfyUI에게 그림 5장을 그리라고 시킵니다...")
    
    # 워크플로우 파일 읽기
    try:
        with open("workflow_api.json", "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        print("❌ 'workflow_api.json' 파일이 없습니다! 같은 폴더에 넣어주세요.")
        return []

    # 5장 반복 생성
    for i, slide in enumerate(slides, 1):
        prompt_text = slide['img_prompt']
        print(f"   [{i}장] 요청: {prompt_text[:30]}...")
        
        # 프롬프트 교체
        workflow[NODE_ID_PROMPT]["inputs"]["text"] = prompt_text
        
        # 시드 랜덤 변경
        if NODE_ID_SEED in workflow:
            workflow[NODE_ID_SEED]["inputs"]["seed"] = random.randint(1, 9999999999)
        
        # 전송
        try:
            requests.post(COMFY_URL, json={"prompt": workflow})
        except:
            print("❌ ComfyUI 서버가 꺼져있습니다! (http://127.0.0.1:8188)")
            return []
        
        # 다음 장 그릴 때까지 잠시 대기
        time.sleep(6) 

    # 최신 이미지 5장 가져오기
    # (ComfyUI 출력 폴더에서 가장 최근에 생긴 파일들을 찾음)
    try:
        all_files = [os.path.join(COMFY_OUTPUT_DIR, f) for f in os.listdir(COMFY_OUTPUT_DIR) 
                     if f.lower().endswith(('.png', '.jpg'))]
        all_files.sort(key=os.path.getmtime, reverse=True) # 최신순 정렬
        
        new_images = all_files[:5] # 상위 5개
        new_images.reverse() # 순서 뒤집기 (1->2->3->4->5)
        return new_images
    except Exception as e:
        print(f"⚠️ 이미지 가져오기 실패: {e}")
        return []

# ======================================================
# 3. HTML 합체
# ======================================================
def create_html_result(slides, image_paths, topic_name):
    print(f"\n📑 '{topic_name}' HTML 조립 중...")
    
    # 결과 저장 폴더 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    save_folder = os.path.join(OUTPUT_HTML_DIR, f"{topic_name}_{timestamp}")
    os.makedirs(save_folder, exist_ok=True)
    
    # 템플릿 읽기
    try:
        with open(template_cover_path, "r", encoding="utf-8") as f: cover_tpl = f.read()
        with open(template_content_path, "r", encoding="utf-8") as f: content_tpl = f.read()
    except FileNotFoundError:
        print("❌ 템플릿 파일(template.html)이 없습니다.")
        return

    for i, slide in enumerate(slides):
        title = slide['title']
        content = slide['content'].replace("\n", "<br>") # 줄바꿈 처리
        
        # 이미지 경로 매칭
        img_path = image_paths[i] if i < len(image_paths) else ""
        
        # HTML 내용 치환
        if i == 0:
            html = cover_tpl.replace("{{ title }}", title).replace("{{ content }}", content)
        else:
            html = content_tpl.replace("{{ title }}", title).replace("{{ content }}", content).replace("{{ image_path }}", img_path)
            
        # 파일 저장
        filename = f"{save_folder}/slide_{i+1:02d}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
            
    print(f"✨ [{topic_name}] 작업 완료! 폴더: {save_folder}")

# ======================================================
# [메인] 폴더 감시 루프
# ======================================================
if __name__ == "__main__":
    print(f"👀 '{INPUT_TXT_DIR}' 폴더를 감시 중입니다...")
    print("텍스트 파일(.txt)을 넣으면 자동으로 작업을 시작합니다.")
    print("(종료하려면 터미널에서 Ctrl+C 를 누르세요)")

    while True:
        try:
            # 1. input 폴더 감시
            input_files = [f for f in os.listdir(INPUT_TXT_DIR) if f.endswith('.txt')]
            
            if input_files:
                target_file = input_files[0]
                file_path = os.path.join(INPUT_TXT_DIR, target_file)
                topic_name = os.path.splitext(target_file)[0]
                
                print(f"\n========================================")
                print(f"📂 파일 발견! 작업 시작: {target_file}")
                print(f"========================================")

                # 2. 파일 읽기
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                
                # 3. 작업 실행 (Gemini -> ComfyUI -> HTML)
                slides_data = get_full_plan_from_text(raw_text)
                if slides_data:
                    generated_images = generate_images(slides_data)
                    create_html_result(slides_data, generated_images, topic_name)
                    
                    # 4. 성공 시 done 폴더로 이동
                    shutil.move(file_path, os.path.join(DONE_TXT_DIR, target_file))
                    print(f"✅ 처리가 끝난 파일은 'done_text' 폴더로 이동했습니다.\n")
                    print(f"👀 다음 파일을 기다리는 중...")
                else:
                    # 실패 시 에러 파일로 이름 바꿔서 이동
                    print("❌ 기획 실패. 파일을 건너뜁니다.")
                    error_dest = os.path.join(DONE_TXT_DIR, f"ERROR_{target_file}")
                    if os.path.exists(error_dest): os.remove(error_dest) # 기존 에러 파일 있으면 삭제
                    shutil.move(file_path, error_dest)

            # 3초 대기
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"⚠️ 오류 발생 (프로그램 계속 실행됨): {e}")
            time.sleep(3)