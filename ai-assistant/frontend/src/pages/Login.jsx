/**
 * 登录页面组件
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getCaptcha } from '../services/api';
import '../assets/styles/Login.css';

const Login = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    captcha_code: '',
  });

  const [captcha, setCaptcha] = useState({
    key: '',
    image: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 如果已登录，重定向到主页
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // 加载验证码
  const loadCaptcha = async () => {
    try {
      const response = await getCaptcha();
      setCaptcha({
        key: response.data.captcha_key,
        image: response.data.captcha_image,
      });
      setFormData((prev) => ({ ...prev, captcha_code: '' }));
    } catch (error) {
      console.error('Failed to load captcha:', error);
      setError('加载验证码失败，请刷新页面重试');
    }
  };

  // 初始加载验证码
  useEffect(() => {
    loadCaptcha();
  }, []);

  // 处理输入变化
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    setError('');
  };

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // 验证表单
    if (!formData.email || !formData.password || !formData.captcha_code) {
      setError('请填写所有必填字段');
      return;
    }

    if (formData.captcha_code.length !== 4) {
      setError('验证码必须是4位字符');
      return;
    }

    setLoading(true);

    try {
      const result = await login({
        email: formData.email,
        password: formData.password,
        captcha_key: captcha.key,
        captcha_code: formData.captcha_code.toUpperCase(),
      });

      if (result.success) {
        navigate('/');
      } else {
        setError(result.error);
        // 登录失败后刷新验证码
        loadCaptcha();
      }
    } catch (error) {
      setError('登录失败，请检查网络连接');
      loadCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>AI Assistant</h1>
          <p>智能对话助手</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="error-message">
              <span>⚠️ {error}</span>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">邮箱账号</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="请输入邮箱地址"
              required
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">密码</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="请输入密码"
              required
              autoComplete="current-password"
              disabled={loading}
            />
          </div>

          <div className="form-group captcha-group">
            <div className="captcha-input">
              <label htmlFor="captcha_code">验证码</label>
              <input
                type="text"
                id="captcha_code"
                name="captcha_code"
                value={formData.captcha_code}
                onChange={handleChange}
                placeholder="请输入验证码"
                maxLength="4"
                required
                disabled={loading}
              />
            </div>
            <div className="captcha-image" onClick={loadCaptcha}>
              {captcha.image ? (
                <img src={captcha.image} alt="验证码" title="点击刷新" />
              ) : (
                <div className="captcha-loading">加载中...</div>
              )}
            </div>
          </div>

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? '登录中...' : '登录'}
          </button>

          <div className="login-tips">
            <p>默认管理员账号：admin@tpl.cntaiping.com</p>
            <p>默认密码：123456</p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
