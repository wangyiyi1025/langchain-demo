"""
用户认证 API
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.user import UserLogin, TokenResponse, CaptchaResponse, UserResponse
from app.services.auth_service import captcha_service, auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    从请求头获取当前用户

    Args:
        authorization: Authorization header

    Returns:
        用户信息

    Raises:
        HTTPException: 如果token无效
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    # 提取token (格式: "Bearer <token>")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="认证令牌格式错误")

    token = parts[1]
    user = auth_service.get_current_user(token)

    if not user:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    return user


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    """
    获取验证码

    Returns:
        验证码图片和键
    """
    try:
        # 生成验证码文本
        captcha_text = captcha_service.generate_captcha_text()

        # 创建验证码图片
        captcha_image = captcha_service.create_captcha_image(captcha_text)

        # 保存验证码到数据库
        captcha_key = captcha_service.save_captcha(captcha_text)

        return CaptchaResponse(
            captcha_key=captcha_key,
            captcha_image=captcha_image,
            expires_in=300
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成验证码失败: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(user_login: UserLogin):
    """
    用户登录

    Args:
        user_login: 登录信息

    Returns:
        JWT token和用户信息
    """
    try:
        result = auth_service.login(
            user_login.email,
            user_login.password,
            user_login.captcha_key,
            user_login.captcha_code
        )

        if not result:
            raise HTTPException(status_code=401, detail="邮箱、密码或验证码错误")

        return TokenResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            user=UserResponse(**result["user"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_user_from_token)):
    """
    获取当前用户信息

    Args:
        current_user: 从token解析出的用户信息

    Returns:
        用户信息
    """
    return UserResponse(**current_user)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user_from_token)):
    """
    用户登出（前端删除token即可）

    Args:
        current_user: 从token解析出的用户信息

    Returns:
        操作结果
    """
    return {
        "success": True,
        "message": "登出成功"
    }
