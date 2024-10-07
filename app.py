import streamlit as st
import requests
import base64
from openai import OpenAI
from PIL import Image
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import asyncio
import os
import datetime
import json
import urllib.parse
import traceback
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# watchdog 로거의 로깅 레벨을 WARNING으로 설정하여 디버그 메시지 제외
logging.getLogger('watchdog').setLevel(logging.WARNING)

# 환경 변수를 통한 시크릿 접근
SENDER_EMAIL = "dnmdaia@gmail.com"
SENDER_PASSWORD = "lvap ujnx nweb ifsr"

# OpenAI API 키 설정
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 로고 및 헤더 URL
LOGO_URL = "https://github.com/DECK6/gamechar/raw/main/logo.png"
HEADER_URL = "https://github.com/DECK6/gamechar/raw/main/header.png"

# 이메일 설정
EMAIL_SETTINGS = {
    "SENDER_EMAIL": SENDER_EMAIL,
    "SENDER_PASSWORD": SENDER_PASSWORD,
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587
}

# 이메일 기능 사용 가능 여부 확인
EMAIL_ENABLED = bool(EMAIL_SETTINGS["SENDER_EMAIL"] and EMAIL_SETTINGS["SENDER_PASSWORD"])

st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮", layout="wide")

def encode_image(image_data):
    return base64.b64encode(image_data).decode('utf-8')

def analyze_image(image_data):
    logger.info("이미지 분석 시작")
    try:
        base64_image = encode_image(image_data)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please analyze the image and capture the person's external features such as gender, skin tone, facial structure, hairstyle, colors, and noticeable characteristics. While maintaining these features, suggest costumes and accessories suitable for a fantasy setting. Provide an English image prompt for an upper-body character that includes these characteristics and costumes."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        analysis_result = response.json()["choices"][0]["message"]["content"]
        logger.info(f"이미지 분석 완료: {analysis_result[:100]}...")  # 처음 100자만 로그
        return analysis_result
    except Exception as e:
        logger.error(f"이미지 분석 중 오류 발생: {str(e)}")
        logger.error(f"오류 타입: {type(e)}")
        logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")
        if hasattr(e, 'response'):
            logger.error(f"응답 내용: {e.response.text}")
        return None

def generate_game_character(prompt, style):
    logger.info(f"{style} 스타일의 게임 캐릭터 생성 시작")
    style_prompts = {
        "도트그래픽(고전게임, 메이플스토리 st.)": "potrait of Super deformed cute 2D pixel art retro game character. showing character potrait only. not showing character chart, color pallet, inventory or someting.",
        "2D 일러스트(애니메이션 st.)": "potrait of Super deformed cute 2D illustrated anime character. showing character potrait only. not showing character chart, color pallet, inventory or someting. anime style",
        "3D 게임 캐릭터": "potrait of Super deformed cute 3D rendered game character like overwatch. showing character potrait only. not showing character chart, color pallet, inventory or someting."
    }
    full_prompt = f"{style_prompts[style]}, {prompt}"
    logger.debug(f"DALL-E 프롬프트: {full_prompt}")
    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    logger.info(f"게임 캐릭터 이미지 생성 완료: {image_url}")
    return image_url

def add_logo_to_image(image_url, logo_url):
    logger.info("로고 추가 시작")
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    logo_response = requests.get(logo_url)
    logo = Image.open(BytesIO(logo_response.content))
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    img.paste(logo, (10, 10), logo)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    logger.info("로고 추가 완료")
    return buffered.getvalue()

async def send_email_async(recipient_email, image_data, style):
    logger.info(f"이메일 전송 시작: {recipient_email}")
    msg = MIMEMultipart()
    msg['Subject'] = f'2024 K-사이언스 월드에서 제작한 캐릭터가 도착했습니다.'
    msg['From'] = EMAIL_SETTINGS["SENDER_EMAIL"]
    msg['To'] = recipient_email

    text = MIMEText(f"2024 K-사이언스 월드에서 제작한 캐릭터가 도착했습니다.")
    msg.attach(text)

    image = MIMEImage(image_data)
    image.add_header('Content-Disposition', 'attachment', filename=f"{style}_game_character.png")
    msg.attach(image)

    try:
        server = smtplib.SMTP(EMAIL_SETTINGS["SMTP_SERVER"], EMAIL_SETTINGS["SMTP_PORT"])
        await asyncio.to_thread(server.starttls)
        await asyncio.to_thread(server.login, EMAIL_SETTINGS["SENDER_EMAIL"], EMAIL_SETTINGS["SENDER_PASSWORD"])
        await asyncio.to_thread(server.send_message, msg)
        server.quit()
        logger.info("이메일 전송 성공")
        return True
    except Exception as e:
        logger.error(f"이메일 전송 중 오류 발생: {str(e)}")
        return False


def initialize_session_state():
    if 'original_image' not in st.session_state:
        st.session_state.original_image = None
    if 'generated_character' not in st.session_state:
        st.session_state.generated_character = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'processing' not in st.session_state:
        st.session_state.processing = False

def process_image(style, result_column):
    logger.info("이미지 처리 시작")

    # 원본 이미지 표시
    if st.session_state.original_image is not None:
        preview_image = Image.open(BytesIO(st.session_state.original_image))
        preview_image.thumbnail((300, 300))
        st.image(preview_image, caption="입력된 이미지", use_column_width=False)

    # 캐릭터 생성 버튼
    if st.session_state.original_image is not None and not st.session_state.processing_complete:
        if st.button("게임 캐릭터 만들기"):
            st.session_state.processing = True

    # 캐릭터 생성 프로세스
    if st.session_state.processing:
        try:
            with st.spinner("캐릭터 생성 중..."):
                description = analyze_image(st.session_state.original_image)
                if description:
                    game_character_url = generate_game_character(description, style)
                    final_image = add_logo_to_image(game_character_url, LOGO_URL)
                    
                    st.session_state.generated_character = final_image
                    st.session_state.processing_complete = True
                else:
                    st.error("이미지 분석에 실패했습니다.")
            
            st.session_state.processing = False
        except Exception as e:
            logger.error(f"캐릭터 생성 중 오류 발생: {str(e)}")
            st.error(f"캐릭터 생성 중 오류 발생: {str(e)}")
            st.session_state.processing = False

    # 생성된 캐릭터 표시
    if st.session_state.processing_complete and st.session_state.generated_character is not None:
        with result_column:
            st.write(f"🎉 완성된 {style} 게임 캐릭터:")
            st.image(st.session_state.generated_character, caption=f"나만의 {style} 게임 캐릭터", use_column_width=True)
            
                
            if EMAIL_ENABLED:
                recipient_email = st.text_input("이메일로 받아보시겠어요? 이메일 주소를 입력해주세요:")
                if st.button("이메일로 전송"):
                    if recipient_email:
                        with st.spinner("이메일을 전송 중입니다..."):
                            image_bytes = BytesIO()
                            Image.open(BytesIO(st.session_state.generated_character)).save(image_bytes, format='PNG')
                            image_bytes = image_bytes.getvalue()
                            
                            email_sent = asyncio.run(send_email_async(recipient_email, image_bytes, style))
                            if email_sent:
                                st.success("이메일이 성공적으로 전송되었습니다!")
                            else:
                                st.error("이메일 전송에 실패했습니다. 다시 시도해주세요.")
                    else:
                        st.warning("이메일 주소를 입력해주세요.")
            else:
                st.info("이메일 전송 기능은 현재 사용할 수 없습니다.")

def main():
    initialize_session_state()  # 세션 상태 초기화
    
    st.image(HEADER_URL, use_column_width=True)
    
    col1, col2 = st.columns(2)
        
    with col1:
        st.markdown("""
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
        """, unsafe_allow_html=True)
        
        st.markdown("""
        안녕하세요! 여러분의 사진을 멋진 게임 캐릭터로 바꿔보세요. 
        사용 방법은 아주 간단해요:
        1. 원하는 캐릭터 스타일을 선택해주세요.
        2. 사진을 찍어주세요.
        3. '게임 캐릭터 만들기' 버튼을 눌러주세요.
        4. 마법처럼 변신한 캐릭터를 확인하세요!
        """)
        
        style = st.radio("원하는 캐릭터 스타일을 선택하세요:", [
            "도트그래픽(고전게임, 메이플스토리 st.)",
            "2D 일러스트(애니메이션 st.)",
            "3D 게임 캐릭터"
        ])
        
        image_source = st.radio("이미지 입력 방법을 선택하세요:", ("카메라로 찍기","파일 업로드"))
        
        if image_source == "카메라로 찍기":
            camera_image = st.camera_input("사진을 찍어주세요")
            if camera_image is not None:
                st.session_state.original_image = camera_image.getvalue()
                st.session_state.processing_complete = False
                st.session_state.generated_character = None

        else:
            uploaded_file = st.file_uploader("사진을 선택해주세요...", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                st.session_state.original_image = uploaded_file.getvalue()
                st.session_state.processing_complete = False
                st.session_state.generated_character = None
        
        process_image(style, col2)
    
    
    with col2:
        st.markdown("""
        ### ⚠️ 주의사항:
        - 만들어진 캐릭터는 이메일로 전송 해주세요. 나중에 다시 볼 수 없어요.
        
        즐겁게 사용해주세요! 😊
        """)

if __name__ == "__main__":
    main()
