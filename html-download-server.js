const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const execAsync = promisify(exec);
const app = express();
const port = 8001;

// 中间件
app.use(cors());
app.use(express.json());

// HTML下载API端点
app.post('/api/download-html', async (req, res) => {
  const { url, fileName } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    console.log('Downloading HTML from:', url);
    
    // 创建临时文件名
    const tempFileName = `temp_${Date.now()}_${fileName || 'download.html'}`;
    const tempFilePath = path.join(__dirname, tempFileName);

    // 使用curl下载文件
    const curlCommand = `curl -L -o "${tempFilePath}" "${url}"`;
    
    console.log('Executing curl command:', curlCommand);
    await execAsync(curlCommand);

    // 检查文件是否存在
    if (!fs.existsSync(tempFilePath)) {
      throw new Error('Downloaded file not found');
    }

    // 读取下载的文件
    const content = fs.readFileSync(tempFilePath, 'utf8');
    console.log('Successfully downloaded HTML, length:', content.length);

    // 清理临时文件
    fs.unlinkSync(tempFilePath);

    return res.status(200).json({
      success: true,
      content: content,
      fileName: fileName
    });

  } catch (error) {
    console.error('Download error:', error);
    return res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// 健康检查端点
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'HTML download server is running' });
});

app.listen(port, () => {
  console.log(`HTML download server running at http://localhost:${port}`);
});