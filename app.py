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

# CSS to horizontally align the radio buttons
st.markdown(
    """
    <style>
    .stRadio > label {
        display: flex;
        flex-direction: row;
    }
    .stRadio div {
        display: flex;
        flex-direction: row;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
                    {"type": "text", "text": "이 이미지 속 인물의 외형적 특성을 분석해주세요. 성별, 피부색, 얼굴 형태, 스타일, 색상, 눈에 띄는 특징을 상세히 포착합니다. 이 특징을 유지한채 판타지 세계관에 어울리는 복장과 장식등을 제안합니다. 상반신이 나오는 캐릭터로 특징과 복장 등을 정리하여 영문 이미지 프롬프트 형태로 제공합니다."},
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
        "도트그래픽(고전게임, 메이플스토리 st.)": "potrait of Super deformed 2D pixel art retro game character. showing character potrait only. not showing character chart, color pallet, inventory or someting.",
        "2D 일러스트(애니메이션 st.)": "potrait of 2D illustrated anime character. showing character potrait only. not showing character chart, color pallet, inventory or someting. anime style",
        "3D 게임 캐릭터": "potrait of Super deformed 3D rendered game character like overwatch. showing character potrait only. not showing character chart, color pallet, inventory or someting."
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

def add_logo_to_image(image_url, logo_url):
    # 생성된 이미지 다운로드
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    # 로고 다운로드
    logo_response = requests.get(logo_url)
    logo = Image.open(BytesIO(logo_response.content))

    # 로고에 알파 채널이 없다면 추가
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')

    # 이미지에 로고 추가 (로고 크기 조정 없이)
    img.paste(logo, (10, 10), logo)

    # 처리된 이미지를 BytesIO 객체로 변환
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

def process_image(image_data, style, result_column):
    upload_response = upload_image_to_imgbb(image_data)
    if upload_response["success"]:
        image_url = upload_response["data"]["url"]
        delete_url = upload_response["data"]["delete_url"]
        
        # 버튼과 미리보기 이미지를 나란히 배치
        button_col, preview_col = st.columns([1, 2])
        
        with button_col:
            if st.button("게임 캐릭터 만들기"):
                try:
                    with st.spinner("이미지를 분석하고 있어요..."):
                        description = analyze_image(image_url)
                    
                    with st.spinner(f"{style} 스타일의 게임 캐릭터를 그리고 있어요..."):
                        game_character_url = generate_game_character(description, style)
                    
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
        
        with preview_col:
            preview_image = Image.open(BytesIO(image_data))
            preview_image.thumbnail((300, 300))
            st.image(preview_image, caption="입력된 이미지", use_column_width=False)
            
def main():
    st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮", layout="wide")
    
    st.image(HEADER_URL, use_column_width=True)
    
    #st.title("🖼️ 사진으로 게임 캐릭터 만들기")
    
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
        
        즐겁게 사용해주세요! 😊
        """)

if __name__ == "__main__":
    main()
