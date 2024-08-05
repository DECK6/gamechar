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

# 환경 변수를 통한 시크릿 접근 시도
SENDER_EMAIL = "dnmdaia@gmail.com"
SENDER_PASSWORD = "iudy dgqr fuin lukc"

# OpenAI API 키 설정
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]



# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 로고 및 헤더 URL
LOGO_URL = "https://github.com/DECK6/gamechar/blob/main/logo.png?raw=true"
HEADER_URL = "https://i.ibb.co/NKCxYqy/temp-Image-Bl-Kh-HN.jpg"



# 이메일 설정
EMAIL_SETTINGS = {
    "SENDER_EMAIL": SENDER_EMAIL,
    "SENDER_PASSWORD": SENDER_PASSWORD,
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587
}

# 이메일 기능 사용 가능 여부 확인
EMAIL_ENABLED = bool(EMAIL_SETTINGS["SENDER_EMAIL"] and EMAIL_SETTINGS["SENDER_PASSWORD"])


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
        "도트그래픽(고전게임, 메이플스토리 st.)": "potrait of Super deformed cute 2D pixel art retro game character. showing character potrait only. not showing character chart, color pallet, inventory or someting.",
        "2D 일러스트(애니메이션 st.)": "potrait of Super deformed cute 2D illustrated anime character. showing character potrait only. not showing character chart, color pallet, inventory or someting. anime style",
        "3D 게임 캐릭터": "potrait of Super deformed cute 3D rendered game character like overwatch. showing character potrait only. not showing character chart, color pallet, inventory or someting."
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
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    logo_response = requests.get(logo_url)
    logo = Image.open(BytesIO(logo_response.content))
    if logo.mode != 'RGBA':
        logo = logo.convert('RGBA')
    img.paste(logo, (10, 10), logo)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

async def send_email_async(recipient_email, image_data, style):

    msg = MIMEMultipart()
    msg['Subject'] = f'2024 Youth E-Sports Festival에서 제작한 게임 캐릭터가 도착했습니다.'
    msg['From'] = EMAIL_SETTINGS["SENDER_EMAIL"]
    msg['To'] = recipient_email

    text = MIMEText(f"2024 Youth E-Sports Festival에서 제작한 게임 캐릭터가 도착했습니다.")
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
        return True
    except Exception as e:
        st.error(f"이메일 전송 중 오류가 발생했습니다: {str(e)}")
        return False

def process_image(image_data, style, result_column):
    if 'email_sent' not in st.session_state:
        st.session_state.email_sent = None
    if 'final_image' not in st.session_state:
        st.session_state.final_image = None
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

    upload_response = upload_image_to_imgbb(image_data)
    if upload_response["success"]:
        image_url = upload_response["data"]["url"]
        delete_url = upload_response["data"]["delete_url"]
        
        button_col, preview_col = st.columns([1, 2])
        
        with button_col:
            if st.button("게임 캐릭터 만들기") or ('generate_character' in st.session_state and st.session_state.generate_character):
                st.session_state.generate_character = False
                if not st.session_state.processing_complete:
                    try:
                        with st.spinner("이미지를 분석하고 있어요..."):
                            description = analyze_image(image_url)
                        
                        with st.spinner(f"{style} 스타일의 게임 캐릭터를 그리고 있어요..."):
                            game_character_url = generate_game_character(description, style)
                        
                        with st.spinner("로고를 추가하고 있어요..."):
                            st.session_state.final_image = add_logo_to_image(game_character_url, LOGO_URL)
                        
                        st.session_state.processing_complete = True
                        st.experimental_rerun()
                    
                    finally:
                        if delete_image_from_imgbb(delete_url):
                            st.success("입력된 이미지가 안전하게 지워졌어요.")
                        else:
                            st.warning("입력된 이미지를 지우는 데 문제가 있었어요. 하지만 걱정하지 마세요!")
        
        with preview_col:
            preview_image = Image.open(BytesIO(image_data))
            preview_image.thumbnail((300, 300))
            st.image(preview_image, caption="입력된 이미지", use_column_width=False)

    if st.session_state.processing_complete and st.session_state.final_image is not None:
        with result_column:
            st.write(f"🎉 완성된 {style} 게임 캐릭터:")
            st.image(st.session_state.final_image, caption=f"나만의 {style} 게임 캐릭터", use_column_width=True)
            
            if EMAIL_ENABLED:
                recipient_email = st.text_input("이메일로 받아보시겠어요? 이메일 주소를 입력해주세요:")
                if st.button("이메일로 전송"):
                    if recipient_email:
                        with st.spinner("이메일을 전송 중입니다..."):
                            image_bytes = BytesIO()
                            Image.open(BytesIO(st.session_state.final_image)).save(image_bytes, format='PNG')
                            image_bytes = image_bytes.getvalue()
                            
                            st.session_state.email_sent = asyncio.run(send_email_async(recipient_email, image_bytes, style))
                    else:
                        st.warning("이메일 주소를 입력해주세요.")
                
                if st.session_state.email_sent is not None:
                    if st.session_state.email_sent:
                        st.success("이메일이 성공적으로 전송되었습니다!")
                    else:
                        st.error("이메일 전송에 실패했습니다. 다시 시도해주세요.")
                    st.session_state.email_sent = None
            else:
                st.info("이메일 전송 기능은 현재 사용할 수 없습니다.")

def main():
    st.set_page_config(page_title="사진으로 게임 캐릭터 만들기", page_icon="🎮", layout="wide")
    
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
#        st.markdown("""
#        ### 결과
#        여기에 변환된 게임 캐릭터가 표시됩니다.
#        ---
#        """)
        
        st.markdown("""
        ### ⚠️ 주의사항:
        - 만들어진 캐릭터는 이메일로 전송 해주세요. 나중에 다시 볼 수 없어요.
        
        즐겁게 사용해주세요! 😊
        """)

if __name__ == "__main__":
    main()
