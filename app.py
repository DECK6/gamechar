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
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import urllib.parse
import traceback
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 환경 변수를 통한 시크릿 접근
SENDER_EMAIL = "dnmdaia@gmail.com"
SENDER_PASSWORD = "iudy dgqr fuin lukc"

# OpenAI API 키 설정
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
IMGBB_API_KEY = st.secrets["IMGBB_API_KEY"]

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

def upload_image_to_imgbb(image_data):
    logger.info("imgbb 이미지 업로드 시작")
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(image_data).decode("utf-8"),
    }
    response = requests.post(url, payload)
    logger.debug(f"imgbb 응답: {response.json()}")
    if response.status_code == 200 and response.json().get('success'):
        logger.info("imgbb 이미지 업로드 성공")
        return response.json()
    else:
        logger.error(f"imgbb 이미지 업로드 실패: {response.text}")
        return None

def delete_image_from_imgbb(delete_url):
    logger.info(f"imgbb 이미지 삭제 시도: {delete_url}")
    response = requests.get(delete_url)
    success = response.status_code == 200
    logger.info(f"imgbb 이미지 삭제 {'성공' if success else '실패'}")
    return success

def analyze_image(image_url):
    logger.info(f"이미지 분석 시작: {image_url}")
    try:
        encoded_url = urllib.parse.quote(image_url, safe=':/')
        logger.debug(f"인코딩된 이미지 URL: {encoded_url}")
        
        request_data = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 이미지 속 인물의 외형적 특성을 분석해주세요. 성별, 피부색, 얼굴 형태, 스타일, 색상, 눈에 띄는 특징을 상세히 포착합니다. 이 특징을 유지한채 판타지 세계관에 어울리는 복장과 장식등을 제안합니다. 상반신이 나오는 캐릭터로 특징과 복장 등을 정리하여 영문 이미지 프롬프트 형태로 제공합니다."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": encoded_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
        logger.debug(f"OpenAI API 요청 내용: {json.dumps(request_data, indent=2)}")
        
        response = client.chat.completions.create(**request_data)
        analysis_result = response.choices[0].message.content
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
        logger.info("이메일 전송 성공")
        return True
    except Exception as e:
        logger.error(f"이메일 전송 중 오류 발생: {str(e)}")
        return False

def upload_image_to_drive(image_data):
    logger.info("구글 드라이브 업로드 시작")
    try:
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        
        folder_name = 'image_upload'
        folder_id = find_or_create_folder(service, folder_name)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_image_path = f"temp_image_{timestamp}.png"
        with open(temp_image_path, "wb") as f:
            f.write(image_data)
        
        file_metadata = {
            'name': f"generated_image_{timestamp}.png",
            'parents': [folder_id]
        }
        media = MediaFileUpload(temp_image_path, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
        file_id = file.get('id')
        share_link = file.get('webViewLink')
        
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()
        
        logger.info(f"구글 드라이브 업로드 성공: {share_link}")
        return file_id, share_link
    except Exception as e:
        logger.error(f"구글 드라이브 업로드 중 오류 발생: {str(e)}")
        return None, None
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

def find_or_create_folder(service, folder_name):
    logger.info(f"구글 드라이브 폴더 찾기/생성: {folder_name}")
    results = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    folders = results.get('files', [])
    
    if folders:
        logger.info(f"기존 폴더 사용: {folders[0]['id']}")
        return folders[0]['id']
    
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    logger.info(f"새 폴더 생성: {folder.get('id')}")
    return folder.get('id')

def process_image(image_data, style, result_column):
    logger.info("이미지 처리 시작")
    
    # 새로운 이미지가 업로드되면 상태 초기화
    if image_data is not None:
        st.session_state.original_image = image_data
        st.session_state.generated_character = None
        st.session_state.processing_complete = False

    # 원본 이미지 표시
    if st.session_state.original_image:
        preview_image = Image.open(BytesIO(st.session_state.original_image))
        preview_image.thumbnail((300, 300))
        st.image(preview_image, caption="입력된 이미지", use_column_width=False)

    # 캐릭터 생성 버튼
    if st.button("게임 캐릭터 만들기"):
        logger.info("게임 캐릭터 생성 버튼 클릭")
        
        if st.session_state.original_image:
            try:
                with st.spinner("캐릭터 생성 중..."):
                    upload_response = upload_image_to_imgbb(st.session_state.original_image)
                    if upload_response["success"]:
                        image_url = upload_response["data"]["url"]
                        delete_url = upload_response["data"]["delete_url"]
                        
                        description = analyze_image(image_url)
                        game_character_url = generate_game_character(description, style)
                        final_image = add_logo_to_image(game_character_url, LOGO_URL)
                        
                        st.session_state.generated_character = final_image
                        st.session_state.processing_complete = True
                        
                        # 원본 이미지 삭제
                        if delete_image_from_imgbb(delete_url):
                            logger.info("입력된 이미지 안전하게 삭제")
                        else:
                            logger.warning("입력된 이미지 삭제 중 문제 발생")
                        
                        st.rerun()
            except Exception as e:
                logger.error(f"캐릭터 생성 중 오류 발생: {str(e)}")
                st.error(f"캐릭터 생성 중 오류 발생: {str(e)}")
        else:
            logger.warning("이미지가 업로드되지 않음")
            st.warning("먼저 이미지를 업로드해주세요.")

    # 생성된 캐릭터 표시
    if st.session_state.processing_complete and st.session_state.generated_character:
        with result_column:
            st.write(f"🎉 완성된 {style} 게임 캐릭터:")
            st.image(st.session_state.generated_character, caption=f"나만의 {style} 게임 캐릭터", use_column_width=True)
            
            # 구글 드라이브에 업로드
            file_id, share_link = upload_image_to_drive(st.session_state.generated_character)
            if file_id:
                st.write(f"이미지가 구글 드라이브에 업로드되었습니다. 공유 링크: {share_link}")
                
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
        
        uploaded_image = None
        
        if image_source == "파일 업로드":
            uploaded_file = st.file_uploader("사진을 선택해주세요...", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                uploaded_image = uploaded_file.getvalue()
        else:
            camera_image = st.camera_input("사진을 찍어주세요")
            if camera_image is not None:
                uploaded_image = camera_image.getvalue()
        
        if uploaded_image:
            process_image(uploaded_image, style, col2)
        else:
            process_image(None, style, col2)
    
    with col2:
        st.markdown("""
        ### ⚠️ 주의사항:
        - 만들어진 캐릭터는 이메일로 전송 해주세요. 나중에 다시 볼 수 없어요.
        
        즐겁게 사용해주세요! 😊
        """)

if __name__ == "__main__":
    main()
