# 贡献指南

感谢您对方寸仿写引擎项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告Bug
1. 使用 [Bug报告模板](https://github.com/WindXRan/fangcun-write/issues/new?template=bug_report.md) 创建issue
2. 详细描述问题，包括复现步骤
3. 提供环境信息和错误日志

### 建议功能
1. 使用 [功能请求模板](https://github.com/WindXRan/fangcun-write/issues/new?template=feature_request.md) 创建issue
2. 清晰描述功能需求和使用场景
3. 如果可能，提供实现思路

### 提交代码
1. Fork 项目仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 开发环境设置

### 前置要求
- Python 3.8+
- Git

### 设置步骤
1. 克隆仓库
```bash
git clone https://github.com/WindXRan/fangcun-write.git
cd fangcun-write
```

2. 安装依赖
```bash
pip install -r requirements.txt  # 如果有
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，添加您的API密钥
```

## 代码风格

### Python代码
- 遵循 PEP 8 规范
- 使用有意义的变量名
- 添加必要的注释
- 保持函数简洁

### 提交信息
使用清晰、描述性的提交信息：
```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

## 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_specific.py
```

### 编写测试
- 为新功能编写测试
- 确保现有测试通过
- 测试覆盖率应保持在合理水平

## 文档

### 更新文档
- 如果您的更改影响使用方式，请更新README.md
- 为复杂功能添加使用示例
- 保持文档简洁明了

### 文档风格
- 使用中文撰写文档
- 保持格式一致
- 添加必要的代码示例

## 行为准则

### 我们的承诺
为了营造一个开放和友好的环境，我们作为贡献者和维护者承诺：
- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同情

### 不可接受的行为
- 使用性别化语言或图像
- 人身攻击或政治攻击
- 公开或私下骚扰
- 未经明确许可发布他人的私人信息
- 其他不道德或不专业的行为

## 许可证

通过贡献您的代码，您同意您的贡献将在 [MIT许可证](LICENSE) 下获得许可。

## 问题？

如果您有任何问题，请在 [讨论区](https://github.com/WindXRan/fangcun-write/discussions) 提问。