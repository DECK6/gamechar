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
                    {"type": "text", "text": "이 이미지 속 인물의 외형적 특성을 분석해주세요. 성별, 피부색, 얼굴 형태, 스타일, 색상, 눈에 띄는 특징을 상세히 포착합니다. 이 특징을 기반으로 판타지 세계관에 어울리는 복장과 장식등을 제안합니다. 2D 레트로 RPG 게임의 도트 일러스트 느낌을 주는 상반신이 나오는 캐릭터로 특징과 복장 등을 정리하여 영문 이미지 프롬프트 형태로 제공합니다."},
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

def generate_game_character(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"2D dot retro game graphic character, {prompt}",
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    return image_url

def process_image(image_data):
    # 이미지를 imgbb에 업로드
    upload_response = upload_image_to_imgbb(image_data)
    if upload_response["success"]:
        image_url = upload_response["data"]["url"]
        delete_url = upload_response["data"]["delete_url"]
        
        st.image(image_url, caption="입력된 이미지", use_column_width=True)
        
        if st.button("게임 캐릭터 만들기"):
            try:
                with st.spinner("이미지를 분석하고 있어요..."):
                    description = analyze_image(image_url)
                
                
                with st.spinner("게임 캐릭터를 그리고 있어요..."):
                    game_character_url = generate_game_character(description)
                
                st.write("🎉 완성된 게임 캐릭터:")
                st.image(game_character_url, caption="나만의 게임 캐릭터", use_column_width=True)
            
            finally:
                # 이미지 삭제
                if delete_image_from_imgbb(delete_url):
                    st.success("입력된 이미지가 안전하게 지워졌어요.")
                else:
                    st.warning("입력된 이미지를 지우는 데 문제가 있었어요. 하지만 걱정하지 마세요!")

def main():
    st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮")
    st.title("🖼️ 사진으로 게임 캐릭터 만들기")
    
    st.markdown("""
    안녕하세요! 여러분의 사진을 멋진 게임 캐릭터로 바꿔보세요. 
    사용 방법은 아주 간단해요:
    1. 사진을 올리거나 카메라로 찍어주세요.
    2. '게임 캐릭터 만들기' 버튼을 눌러주세요.
    3. 마법처럼 변신한 캐릭터를 확인하세요!
    """)
    
    image_source = st.radio("이미지 입력 방법을 선택하세요:", ("파일 업로드", "카메라로 찍기"))
    
    if image_source == "파일 업로드":
        uploaded_file = st.file_uploader("사진을 선택해주세요...", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            image_data = uploaded_file.getvalue()
            process_image(image_data)
    else:
        camera_image = st.camera_input("사진을 찍어주세요")
        if camera_image is not None:
            image_data = camera_image.getvalue()
            process_image(image_data)

    st.markdown("""
    ---
    ⚠️ 주의사항:
    - 개인정보가 포함된 사진은 올리지 말아주세요.
    - 만들어진 캐릭터는 저장해두세요. 나중에 다시 볼 수 없어요.
    - 하루에 너무 많은 사진을 변환하면 기다려야 할 수 있어요.
    
    즐겁게 사용해주세요! 😊
    """)

if __name__ == "__main__":
    main()
