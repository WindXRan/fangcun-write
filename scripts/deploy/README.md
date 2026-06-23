# 自动化部署指南

## 配置GitHub Secrets

在GitHub仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 | 获取方式 |
|--------|------|----------|
| `COZE_TOKEN` | Coze API Token | coze.cn → 个人设置 → API密钥 |
| `COZE_SPACE_ID` | Coze Space ID | coze.cn → 空间设置 → 空间ID |
| `OPENCLAW_TOKEN` | OpenClaw Token | openclaw.ai → 设置 → API Token |
| `SLACK_WEBHOOK_URL` | Slack通知（可选） | Slack → Incoming Webhooks |

## 使用方式

### 1. 自动部署（推荐）

打tag触发：

```bash
# 打tag
git tag v1.0.0
git push origin v1.0.0

# 自动部署所有skill到所有平台
```

### 2. 手动部署

在GitHub Actions页面手动触发：

1. 进入 Actions → Deploy Skills to Platforms
2. 点击 "Run workflow"
3. 选择平台和skill
4. 点击 "Run workflow"

### 3. 本地测试

```bash
# 测试Coze部署
python scripts/deploy/deploy_coze.py \
  --skill .agents/skills/fangcun-write \
  --token YOUR_COZE_TOKEN \
  --space-id YOUR_SPACE_ID

# 测试OpenClaw部署
claw login --token YOUR_OPENCLAW_TOKEN
claw validate .agents/skills/fangcun-write
claw publish .agents/skills/fangcun-write
```

## 平台说明

### Coze（扣子）

- 有完整的API支持
- 可以创建/更新Bot
- 商店上架需要人工审核（1-3天）
- 国内流量主力

### OpenClaw

- 有完整的CLI支持
- 支持 `claw publish` 命令
- 自动上架到ClawHub
- 审核较快（通常几小时）

### 飞书aily

- 目前没有公开API
- 需要手动在控制台操作
- 可以用RPA（影刀/UiBot）模拟点击
- 适合B端客户按需部署

## 注意事项

1. **审核无法绕过**：所有平台的"上架到商店/市场"环节都有审核
2. **API变更频繁**：各平台API仍在快速迭代，需做好版本兼容
3. **安全合规前置**：部署前确保内容安全，避免被封号
4. **不要追求100%自动化**：首次上架和重大版本更新务必人工验证
