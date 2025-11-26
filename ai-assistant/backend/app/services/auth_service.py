"""
用户认证服务
"""
import jwt
import uuid
import base64
import bcrypt
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import random
import string
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import settings
from app.database import db


class CaptchaService:
    """验证码服务"""

    @staticmethod
    def generate_captcha_text(length: int = 4) -> str:
        """生成验证码文本"""
        # 只使用大写字母，避免混淆
        characters = string.ascii_uppercase.replace('O', '').replace('I', '')
        return ''.join(random.choices(characters, k=length))

    @staticmethod
    def create_captcha_image(text: str) -> str:
        """
        创建验证码图片

        Args:
            text: 验证码文本

        Returns:
            Base64编码的图片字符串
        """
        # 创建图片
        width, height = 120, 40
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)

        # 添加干扰线
        for _ in range(3):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)

        # 添加干扰点
        for _ in range(50):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(200, 200, 200))

        # 绘制验证码文字
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        except:
            # 如果找不到字体，使用默认字体
            font = ImageFont.load_default()

        # 计算文字位置
        text_width = len(text) * 25
        x_start = (width - text_width) // 2

        for i, char in enumerate(text):
            x = x_start + i * 25 + random.randint(-3, 3)
            y = random.randint(2, 8)
            color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
            draw.text((x, y), char, font=font, fill=color)

        # 转换为Base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{image_base64}"

    @staticmethod
    def save_captcha(code: str) -> str:
        """
        保存验证码到数据库

        Args:
            code: 验证码文本

        Returns:
            验证码键
        """
        captcha_key = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=5)

        sql = """
            INSERT INTO captcha_codes (code_key, code_value, expires_at)
            VALUES (%s, %s, %s)
        """
        db.execute_update(sql, (captcha_key, code.upper(), expires_at))

        # 清理过期验证码
        db.execute_update("DELETE FROM captcha_codes WHERE expires_at < NOW()")

        return captcha_key

    @staticmethod
    def verify_captcha(captcha_key: str, captcha_code: str) -> bool:
        """
        验证验证码

        Args:
            captcha_key: 验证码键
            captcha_code: 用户输入的验证码

        Returns:
            验证是否成功
        """
        sql = """
            SELECT code_value FROM captcha_codes
            WHERE code_key = %s AND expires_at > NOW()
        """
        result = db.execute_query(sql, (captcha_key,))

        if not result:
            return False

        # 验证后删除验证码（一次性使用）
        db.execute_update("DELETE FROM captcha_codes WHERE code_key = %s", (captcha_key,))

        return result[0]['code_value'].upper() == captcha_code.upper()


class AuthService:
    """用户认证服务"""

    @staticmethod
    def create_access_token(user_id: int, email: str) -> str:
        """
        创建访问令牌

        Args:
            user_id: 用户ID
            email: 用户邮箱

        Returns:
            JWT token
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        验证令牌

        Args:
            token: JWT token

        Returns:
            解码后的payload，如果验证失败返回None
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def verify_user_credentials(email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户凭据（独立方法，方便后续对接第三方）

        Args:
            email: 用户邮箱
            password: 密码

        Returns:
            用户信息，如果验证失败返回None
        """
        sql = """
            SELECT id, email, password_hash, created_at, last_login_at, is_active
            FROM users
            WHERE email = %s AND is_active = 1
        """
        result = db.execute_query(sql, (email,))

        if not result:
            return None

        user = result[0]

        # 验证密码
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return None

        return {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
            "last_login_at": user["last_login_at"],
            "is_active": user["is_active"]
        }

    @staticmethod
    def login(email: str, password: str, captcha_key: str, captcha_code: str) -> Optional[Dict[str, Any]]:
        """
        用户登录

        Args:
            email: 用户邮箱
            password: 密码
            captcha_key: 验证码键
            captcha_code: 验证码

        Returns:
            包含token和用户信息的字典，如果登录失败返回None
        """
        # 验证验证码
        if not CaptchaService.verify_captcha(captcha_key, captcha_code):
            return None

        # 验证用户凭据
        user = AuthService.verify_user_credentials(email, password)
        if not user:
            return None

        # 更新最后登录时间
        db.execute_update(
            "UPDATE users SET last_login_at = NOW() WHERE id = %s",
            (user["id"],)
        )

        # 生成token
        token = AuthService.create_access_token(user["id"], user["email"])

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }

    @staticmethod
    def get_current_user(token: str) -> Optional[Dict[str, Any]]:
        """
        获取当前用户信息

        Args:
            token: JWT token

        Returns:
            用户信息，如果token无效返回None
        """
        payload = AuthService.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        sql = """
            SELECT id, email, created_at, last_login_at, is_active
            FROM users
            WHERE id = %s AND is_active = 1
        """
        result = db.execute_query(sql, (user_id,))

        if not result:
            return None

        return result[0]


# 创建全局服务实例
captcha_service = CaptchaService()
auth_service = AuthService()
