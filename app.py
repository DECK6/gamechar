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

# 로고 및 헤더 URL
LOGO_URL = "https://github.com/DECK6/gamechar/blob/main/logo.png?raw=true"
HEADER_URL = "https://github.com/DECK6/gamechar/blob/main/header.png?raw=true"

# 기존 함수들은 그대로 유지...

def process_image(image_data, style, result_column):
    upload_response = upload_image_to_imgbb(image_data)
    if upload_response["success"]:
        image_url = upload_response["data"]["url"]
        delete_url = upload_response["data"]["delete_url"]
        
        # 미리보기 이미지 크기 조절
        preview_image = Image.open(BytesIO(image_data))
        preview_image.thumbnail((300, 300))  # 최대 크기를 300x300으로 제한
        st.image(preview_image, caption="입력된 이미지", use_column_width=False)
        
        if st.button("게임 캐릭터 만들기"):
            try:
                with st.spinner("이미지를 분석하고 있어요..."):
                    description = analyze_image(image_url)
                
                with st.spinner(f"{style} 스타일의 게임 캐릭터를 그리고 있어요..."):
                    game_character_url = generate_game_character(description, style)
                
                # 로고 추가
                with st.spinner("로고를 추가하고 있어요..."):
                    final_image = add_logo_to_image(game_character_url, LOGO_URL)
                
                with result_column:
                    st.write(f"🎉 완성된 {style} 게임 캐릭터:")
                    st.image(final_image, caption=f"나만의 {style} 게임 캐릭터", use_column_width=True)
            
            finally:
                if delete_image_from_imgbb(delete_url):
                    st.success("입력된 이미지가 안전하게 지워졌어요.")
                else:
                    st.warning("입력된 이미지를 지우는 데 문제가 있었어요. 하지만 걱정하지 마세요!")

def main():
    st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮", layout="wide")
    
    # 헤더 이미지 추가
    st.image(HEADER_URL, use_column_width=True)
    
    st.title("🖼️ 사진으로 게임 캐릭터 만들기")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        안녕하세요! 여러분의 사진을 멋진 게임 캐릭터로 바꿔보세요. 
        사용 방법은 아주 간단해요:
        1. 원하는 캐릭터 스타일을 선택해주세요.
        2. 사진을 올리거나 카메라로 찍어주세요.
        3. '게임 캐릭터 만들기' 버튼을 눌러주세요.
        4. 마법처럼 변신한 캐릭터를 확인하세요!
        """)
        
        style = st.radio("원하는 캐릭터 스타일을 선택하세요:", [
            "도트그래픽(고전게임, 메이플스토리 st.)",
            "2D 일러스트(애니메이션 st.)",
            "3D 게임 캐릭터"
        ])
        
        image_source = st.radio("이미지 입력 방법을 선택하세요:", ("파일 업로드", "카메라로 찍기"))
        
        if image_source == "파일 업로드":
            uploaded_file = st.file_uploader("사진을 선택해주세요...", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                image_data = uploaded_file.getvalue()
                process_image(image_data, style, col2)
        else:
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
