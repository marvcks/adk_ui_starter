// 这是一个简单的API端点，用于下载HTML文件
// 在实际项目中，这应该在后端服务器中实现

import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';

const execAsync = promisify(exec);

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { url, fileName } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    // 创建临时文件名
    const tempFileName = `temp_${Date.now()}_${fileName || 'download.html'}`;
    const tempFilePath = path.join('/tmp', tempFileName);

    // 使用curl下载文件
    const curlCommand = `curl -o "${tempFilePath}" "${url}"`;
    
    console.log('Executing curl command:', curlCommand);
    await execAsync(curlCommand);

    // 读取下载的文件
    const content = fs.readFileSync(tempFilePath, 'utf8');

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
}