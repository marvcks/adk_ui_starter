# 特殊工具处理说明

## 概述

为了提供更好的用户体验，我们对某些特殊工具进行了定制化处理，避免显示不必要的信息。

## 特殊工具列表

### 1. transfer_to_agent

**工具名称**: `transfer_to_agent`

**特殊处理**:
- ❌ 不展示输入参数
- ❌ 不展示工具输出结果
- ✅ 只显示执行状态（正在执行/执行完成）

**原因**: 这个工具通常用于内部代理切换，其参数和结果对用户没有实际意义，避免界面混乱。

**实现方式**:
```typescript
// 在 ToolCallPanel.tsx 中
const isTransferToAgent = toolName === 'transfer_to_agent';

// 输入参数部分
{status === 'executing' && !isTransferToAgent && (
  // 输入参数显示逻辑
)}

// 工具输出部分
{status === 'completed' && result && !isTransferToAgent && (
  // 工具输出显示逻辑
)}
```

## 其他工具的标准处理

### 输入参数显示
- 工具执行中时显示
- 支持 JSON 格式化和语法高亮
- 提供复制到剪贴板功能

### 工具输出显示
- 工具完成时显示
- 智能提取 TextContent 中的 text 内容
- 支持 JSON 格式化和语法高亮
- 提供复制到剪贴板功能

## TextContent 智能提取

### 提取逻辑
1. **直接 TextContent**: 检查 `{type: 'text', text: '...'}`
2. **嵌套 Content 数组**: 遍历 `content` 数组，提取所有 `type: 'text'` 的内容
3. **Result 字段**: 递归检查 `result` 字段
4. **降级处理**: 如果没有找到 TextContent，显示原始内容的格式化版本

### 示例
```json
// 输入数据结构
{
  "result": {
    "content": [
      {
        "type": "text",
        "text": "工具执行成功，生成了以下结果："
      },
      {
        "type": "text", 
        "text": "1. 数据已处理完成\n2. 结果已保存到文件"
      }
    ]
  }
}

// 提取后的显示内容
工具执行成功，生成了以下结果：
1. 数据已处理完成
2. 结果已保存到文件
```

## 技术实现

### 组件修改
- `ToolCallPanel.tsx`: 添加特殊工具判断逻辑
- 修改输入参数和工具输出的显示条件
- 增强 `renderJsonContent` 函数

### 样式保持
- 保持原有的浅灰色背景设计
- 维持可折叠面板的交互体验
- 保持复制功能的完整性

## 扩展性

### 添加新的特殊工具
如果需要为其他工具添加特殊处理，只需在 `ToolCallPanel.tsx` 中添加新的判断条件：

```typescript
const isSpecialTool = toolName === 'transfer_to_agent' || 
                     toolName === 'other_special_tool';

// 然后在显示条件中使用 !isSpecialTool
```

### 自定义处理逻辑
可以为不同的特殊工具定义不同的处理逻辑：

```typescript
const getToolDisplayConfig = (toolName: string) => {
  switch (toolName) {
    case 'transfer_to_agent':
      return { showInput: false, showOutput: false };
    case 'other_tool':
      return { showInput: true, showOutput: false };
    default:
      return { showInput: true, showOutput: true };
  }
};
```

## 总结

通过这种特殊工具处理机制，我们实现了：
1. **界面简洁性**: 避免显示无意义的工具信息
2. **用户体验**: 专注于有用的工具调用信息
3. **维护性**: 易于扩展和维护特殊工具的处理逻辑
4. **一致性**: 保持其他工具的标准显示格式 