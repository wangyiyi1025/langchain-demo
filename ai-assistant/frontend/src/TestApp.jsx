// 最简单的测试组件
function TestApp() {
  console.log('TestApp 渲染中...')
  
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: '3em', marginBottom: '20px' }}>
          🎉 React 运行成功！
        </h1>
        <p style={{ fontSize: '1.2em', opacity: 0.9 }}>
          如果你看到这个页面，说明：
        </p>
        <ul style={{ 
          listStyle: 'none', 
          padding: 0, 
          marginTop: '20px',
          fontSize: '1.1em',
          lineHeight: '2'
        }}>
          <li>✅ Vite 配置正确</li>
          <li>✅ React 正常工作</li>
          <li>✅ 依赖安装完整</li>
        </ul>
        <button 
          onClick={() => alert('点击事件工作正常！')}
          style={{
            marginTop: '30px',
            padding: '15px 30px',
            fontSize: '1.1em',
            background: 'white',
            color: '#667eea',
            border: 'none',
            borderRadius: '25px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          测试点击
        </button>
      </div>
    </div>
  )
}

export default TestApp