"""
用户相关数据模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr = Field(..., description="用户邮箱")


class UserCreate(BaseModel):
    """用户创建模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr = Field(..., description="用户邮箱")
    password: str = Field(..., description="密码")
    captcha_key: str = Field(..., description="验证码键")
    captcha_code: str = Field(..., min_length=4, max_length=4, description="验证码")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    email: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    is_active: bool


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CaptchaResponse(BaseModel):
    """验证码响应模型"""
    captcha_key: str = Field(..., description="验证码键，用于验证时提交")
    captcha_image: str = Field(..., description="Base64编码的验证码图片")
    expires_in: int = Field(300, description="过期时间（秒）")
