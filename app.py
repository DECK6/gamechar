import streamlit as st
import requests
import base64
from openai import OpenAI
from PIL import Image
from io import BytesIO

# Streamlit secrets에서 API 키 가져오기
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

def upload_image_to_imgbb(image_data):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_data).decode("utf-8"),
    }
    response = requests.post(url, payload)
    return response.json()

def delete_image_from_imgbb(delete_url):
    response = requests.get(delete_url)
    return response.status_code == 200

def analyze_image(image_url):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 이미지 속 인물의 외형적 특성을 분석해주세요. 성별, 피부색, 얼굴 형태, 스타일, 색상, 눈에 띄는 특징을 상세히 포착합니다. 이 특징을 기반으로 판타지 세계관에 어울리는 복장과 장식등을 제안합니다. 상반신이 나오는 캐릭터로 특징과 복장 등을 정리하여 영문 이미지 프롬프트 형태로 제공합니다."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        max_tokens=1000
    )
    return response.choices[0].message.content

def generate_game_character(prompt, style):
    style_prompts = {
        "도트그래픽": "2D pixel art retro game character potrait, showing character potrait only, not character chart",
        "일러스트": "2D illustrated game character portrait, showing character potrait only, not character chart, anime style",
        "3D 게임 캐릭터": "3D rendered game character model, showing character potrait only, not character chart, unreal engine, cute Super deformed 3D"
    }
    full_prompt = f"{style_prompts[style]}, {prompt}"
    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    return image_url

def process_image(image_data, style, result_placeholder):
    upload_response = upload_image_to_imgbb(image_data)
    if upload_response["success"]:
        image_url = upload_response["data"]["url"]
        delete_url = upload_response["data"]["delete_url"]
        
        result_placeholder.image(image_url, caption="찍은 사진", use_column_width=True)
        
        if result_placeholder.button("게임 캐릭터 만들기"):
            try:
                with result_placeholder.spinner("이미지를 분석하고 있어요..."):
                    description = analyze_image(image_url)
                
                with result_placeholder.spinner(f"{style} 스타일의 게임 캐릭터를 그리고 있어요..."):
                    game_character_url = generate_game_character(description, style)
                
                result_placeholder.write(f"🎉 완성된 {style} 게임 캐릭터:")
                result_placeholder.image(game_character_url, caption=f"나만의 {style} 게임 캐릭터", use_column_width=True)
            
            finally:
                if delete_image_from_imgbb(delete_url):
                    result_placeholder.success("입력된 이미지가 안전하게 지워졌어요.")
                else:
                    result_placeholder.warning("입력된 이미지를 지우는 데 문제가 있었어요. 하지만 걱정하지 마세요!")

def main():
    st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮", layout="wide")
    st.title("🖼️ 사진으로 게임 캐릭터 만들기")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        안녕하세요! 여러분의 사진을 멋진 게임 캐릭터로 바꿔보세요. 
        사용 방법은 아주 간단해요:
        1. 원하는 캐릭터 스타일을 선택해주세요.
        2. 카메라로 사진을 찍어주세요.
        3. '게임 캐릭터 만들기' 버튼을 눌러주세요.
        4. 마법처럼 변신한 캐릭터를 확인하세요!
        """)
        
        style = st.radio("원하는 캐릭터 스타일을 선택하세요:", ["도트그래픽(고전게임, 메이플스토리 st.)", "2D 일러스트(애니메이션 st.)", "3D 게임 캐릭터"])
        
        # 파일 업로드 옵션 주석 처리
        # image_source = st.radio("이미지 입력 방법을 선택하세요:", ("파일 업로드", "카메라로 찍기"))
        
        # if image_source == "파일 업로드":
        #     uploaded_file = st.file_uploader("사진을 선택해주세요...", type=["jpg", "jpeg", "png"])
        #     if uploaded_file is not None:
        #         image_data = uploaded_file.getvalue()
        #         process_image(image_data, style, col2)
        # else:
        camera_image = st.camera_input("사진을 찍어주세요")
        if camera_image is not None:
            image_data = camera_image.getvalue()
            process_image(image_data, style, col2)
    
    with col2:
        st.markdown("""
        ### 결과
        여기에 변환된 게임 캐릭터가 표시됩니다.
        """)
        
        st.markdown("""
        ---
        ### ⚠️ 주의사항:
        - 만들어진 캐릭터는 저장해두세요. 나중에 다시 볼 수 없어요.
        - 하루에 너무 많은 사진을 변환하면 기다려야 할 수 있어요.
        
        즐겁게 사용해주세요! 😊
        """)

if __name__ == "__main__":
    main()
