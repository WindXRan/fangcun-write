# 蛙蛙写作 (wawawriter.com) API 全集

**Base URL**: `https://wawawriter.com/wrhp-api`

---

## v1 API

### 🔐 认证 / 用户

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/phone/send_code` | POST | 发送手机验证码 |
| `/api/v1/auth/phone/verify` | POST | 验证手机验证码 |
| `/api/v1/user/login` | POST | 用户登录 |
| `/api/v1/user/logout` | POST | 用户登出 |
| `/api/v1/user/` | GET/PUT | 用户信息 |
| `/api/v1/user/setting` | GET/PUT | 用户设置 |
| `/api/v1/user/b_user_account_info` | GET | B端账户信息 |
| `/api/v1/user/wx_login_web/` | GET | 微信 Web 登录 |
| `/api/v1/wechat/web/login` | POST | 微信网页登录 |
| `/api/v1/wechat/app/login` | POST | 微信 App 登录 |
| `/api/v1/wechat/jsapi/config` | POST | 微信 JSAPI 配置 |
| `/api/v1/wechat/office/event` | POST | 公众号事件回调 |
| `/api/v1/wechat/office/qr` | GET | 公众号二维码 |

### 📖 小说（核心）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/novel/` | POST | 创建小说 |
| `/api/v1/novel/list` | GET | 小说列表 |
| `/api/v1/novel/list/all` | GET | 全部小说列表 |
| `/api/v1/novel/create_convert` | POST | 创建转换任务 |
| `/api/v1/novel/create_unpack/{base_novel_id}` | POST | 创建拆书任务 |
| `/api/v1/novel/convert/{base_novel_id}` | POST | 执行转换（拆书） |
| `/api/v1/novel/convert/{base_novel_id}/free` | POST | 免费转换 |
| `/api/v1/novel/unpack/{base_novel_id}` | POST | 拆书 |
| `/api/v1/novel/import` | POST | 导入小说 |
| `/api/v1/novel/examine` | POST | 审阅 |
| `/api/v1/novel/commit` | POST | 提交 |
| `/api/v1/novel/nodes` | GET | 获取节点树 |
| `/api/v1/novel/status` | GET | 状态查询 |
| `/api/v1/novel/permanent` | DELETE | 永久删除 |
| `/api/v1/novel/restore` | POST | 恢复 |
| `/api/v1/novel/trash` | GET | 回收站列表 |
| `/api/v1/novel/trash/clear` | POST | 清空回收站 |
| `/api/v1/novel/share/{token}` | GET | 通过 token 获取分享 |
| `/api/v1/novel/{base_novel_id}/share` | POST | 分享小说 |
| `/api/v1/novel/{base_novel_id}/import_chapters` | POST | 导入章节 |
| `/api/v1/novel/{novel_id}/chapters` | GET | 获取章节列表 |
| `/api/v1/novel/{novel_id}/chapter/{node_id}` | GET/PUT | 获取/更新单章 |

### 🎬 小说转视频

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/novel/chapter/video/` | POST | 创建视频 |
| `/api/v1/novel/chapter/video/generate` | POST | 生成视频 |
| `/api/v1/novel/chapter/video/list` | GET | 视频列表 |
| `/api/v1/novel/chapter/video/play` | GET | 分镜详情 |
| `/api/v1/novel/chapter/video/play/add` | POST | 添加分镜 |
| `/api/v1/novel/chapter/video/play/generate` | POST | 生成分镜 |
| `/api/v1/novel/chapter/video/play/text/generate` | POST | 生成分镜文本 |
| `/api/v1/novel/chapter/video/play/image/generate` | POST | 生成分镜图片 |
| `/api/v1/novel/chapter/video/play/image/add` | POST | 添加分镜图片 |
| `/api/v1/novel/chapter/video/play/image/list` | GET | 分镜图片列表 |
| `/api/v1/novel/chapter/video/play/image/update` | PUT | 更新分镜图片 |
| `/api/v1/novel/chapter/video/play/image/editing` | POST | 编辑分镜图片 |
| `/api/v1/novel/chapter/video/plays/image/generate` | POST | 批量生成分镜图片 |
| `/api/v1/novel/chapter/video/persona` | GET | 角色详情 |
| `/api/v1/novel/chapter/video/persona/generate` | POST | 生成角色 |
| `/api/v1/novel/chapter/video/persona/list` | GET | 角色列表 |
| `/api/v1/novel/chapter/video/persona/image/generate` | POST | 生成角色图片 |
| `/api/v1/novel/chapter/video/fragment/generate` | POST | 生成视频片段 |
| `/api/v1/novel/chapter/video/voice/list` | GET | 语音列表 |
| `/api/v1/novel/chapter/video/synthesize/static-reminder` | POST | 合成提醒 |
| `/api/v1/novel/chapter/video/permanent` | DELETE | 永久删除视频 |
| `/api/v1/novel/chapter/video/restore` | POST | 恢复视频 |
| `/api/v1/novel/chapter/video/trash` | GET | 视频回收站 |
| `/api/v1/novel/chapter/video/trash/clear` | POST | 清空视频回收站 |

### 💬 AI Chat

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat/completion` | POST | AI 补全（SSE 流式） |
| `/api/v1/chat/conversation` | POST | 创建会话 |
| `/api/v1/chat/conversations` | GET | 会话列表 |
| `/api/v1/chat/conversation/delete` | POST | 删除会话 |
| `/api/v1/chat/conversation/update` | PUT | 更新会话 |
| `/api/v1/chat/messages` | GET | 消息列表 |
| `/api/v1/chat/message/delete` | POST | 删除消息 |
| `/api/v1/chat/message/interaction` | POST | 消息交互（点赞/踩） |
| `/api/v1/chat/message/persist` | POST | 持久化消息 |
| `/api/v1/chat/message/switch` | POST | 切换消息分支 |
| `/api/v1/chat/message/update` | PUT | 更新消息 |
| `/api/v1/chat/file/upload` | POST | 上传文件 |
| `/api/v1/chat/resume` | POST | 恢复会话 |
| `/api/v1/agent-chat` | POST | Agent 对话 |

### 🔧 UGC Debug Chat

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ugc_debug_chat/completion` | POST | UGC 调试补全 |
| `/api/v1/ugc_debug_chat/conversation` | POST | 创建调试会话 |
| `/api/v1/ugc_debug_chat/conversations` | GET | 调试会话列表 |
| `/api/v1/ugc_debug_chat/conversation/delete` | POST | 删除调试会话 |
| `/api/v1/ugc_debug_chat/conversation/update` | PUT | 更新调试会话 |
| `/api/v1/ugc_debug_chat/messages` | GET | 调试消息列表 |
| `/api/v1/ugc_debug_chat/message/delete` | POST | 删除调试消息 |
| `/api/v1/ugc_debug_chat/message/interaction` | POST | 调试消息交互 |
| `/api/v1/ugc_debug_chat/message/persist` | POST | 持久化调试消息 |
| `/api/v1/ugc_debug_chat/message/switch` | POST | 切换调试消息分支 |
| `/api/v1/ugc_debug_chat/message/update` | PUT | 更新调试消息 |

### 🔄 AI Workflow

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ai_workflow/create` | POST | 创建工作流 |
| `/api/v1/ai_workflow/delete` | POST | 删除工作流 |
| `/api/v1/ai_workflow/list` | GET | 工作流列表 |
| `/api/v1/ai_workflow/recommend` | GET | 推荐工作流 |
| `/api/v1/ai_workflow/square` | GET | 工作流广场 |
| `/api/v1/ai_workflow/share` | POST | 分享工作流 |
| `/api/v1/ai_workflow/like` | POST | 点赞工作流 |
| `/api/v1/ai_workflow/favorite/add` | POST | 收藏工作流 |
| `/api/v1/ai_workflow/favorite/list` | GET | 收藏列表 |
| `/api/v1/ai_workflow/favorite/remove` | POST | 取消收藏 |
| `/api/v1/ai_workflow/runs/one-click` | POST | 一键运行 |
| `/api/v1/ai_workflow/runs/step` | POST | 单步运行 |
| `/api/v1/ai_workflow/runs/{run_id}/cancel` | POST | 取消运行 |
| `/api/v1/ai_workflow/permission/handle` | POST | 处理权限请求 |
| `/api/v1/ai_workflow/permission/request` | POST | 请求权限 |
| `/api/v1/ai_workflow/permission/requests` | GET | 权限请求列表 |
| `/api/v1/ai_workflow/permission/status` | GET | 权限状态 |

### 📝 UGC Prompt

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ugc_prompt/create` | POST | 创建 Prompt |
| `/api/v1/ugc_prompt/delete` | POST | 删除 Prompt |
| `/api/v1/ugc_prompt/list` | GET | Prompt 列表 |
| `/api/v1/ugc_prompt/recommend` | GET | 推荐 Prompt |
| `/api/v1/ugc_prompt/square` | GET | Prompt 广场 |
| `/api/v1/ugc_prompt/share` | POST | 分享 Prompt |
| `/api/v1/ugc_prompt/like` | POST | 点赞 Prompt |
| `/api/v1/ugc_prompt/operate` | POST | 操作 Prompt |
| `/api/v1/ugc_prompt/hot_tags` | GET | 热门标签 |
| `/api/v1/ugc_prompt/favorite/add` | POST | 收藏 Prompt |
| `/api/v1/ugc_prompt/favorite/list` | GET | 收藏列表 |
| `/api/v1/ugc_prompt/favorite/remove` | POST | 取消收藏 |
| `/api/v1/ugc_prompt/permission/handle` | POST | 处理权限请求 |
| `/api/v1/ugc_prompt/permission/request` | POST | 请求权限 |
| `/api/v1/ugc_prompt/permission/requests` | GET | 权限请求列表 |
| `/api/v1/ugc_prompt/permission/status` | GET | 权限状态 |

### 💰 支付 / 会员

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/pay/prepay` | POST | 预支付 |
| `/api/v1/pay/course_prepay` | POST | 课程预支付 |
| `/api/v1/pay/order/list` | GET | 订单列表 |
| `/api/v1/pay/order/status` | GET | 订单状态 |
| `/api/v1/coin-goods` | GET | 金币商品列表 |
| `/api/v1/member-goods` | GET | 会员商品列表 |
| `/api/v1/membership/account` | GET | 会员账户信息 |
| `/api/v1/membership/status` | GET | 会员状态 |
| `/api/v1/membership/tabs` | GET | 会员 Tab 配置 |
| `/api/v1/membership/check-total-paid` | GET | 检查累计付费 |
| `/api/v1/membership/check-new-membership-dialog` | GET | 新会员弹窗检查 |
| `/api/v1/membership/mark-new-membership-dialog-viewed` | POST | 标记已看弹窗 |
| `/api/v1/membership/unlimited-benefit-info` | GET | 无限权益信息 |
| `/api/v1/apple-iap/confirm` | POST | Apple IAP 确认 |
| `/api/v1/biz_coin/` | GET | 金币信息 |
| `/api/v1/biz_coin/create` | POST | 创建金币配置 |
| `/api/v1/biz_coin/base_config` | GET | 金币基础配置 |
| `/api/v1/biz_coin/query_config` | GET | 查询金币配置 |
| `/api/v1/biz_coin/batch_update_status` | POST | 批量更新状态 |
| `/api/v1/user/coin/unused` | GET | 未使用金币 |
| `/api/v1/user/coin/new_user_gift` | POST | 新用户金币礼包 |
| `/api/v1/user_transaction/list` | GET | 交易记录 |
| `/api/v1/user_transaction/status` | GET | 交易状态 |
| `/api/v1/user_transaction_backend/list` | GET | 后台交易记录 |

### 👥 邀请 / 提现

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/user/invite_code` | GET | 我的邀请码 |
| `/api/v1/user/bind_invite_code` | POST | 绑定邀请码 |
| `/api/v1/user/invite_leaderboard` | GET | 邀请排行榜 |
| `/api/v1/user/invite_reward` | GET | 邀请奖励 |
| `/api/v1/user/invite_reward_info` | GET | 奖励详情 |
| `/api/v1/user/invite_reward_record` | GET | 奖励记录 |
| `/api/v1/user/withdraw` | POST | 提现 |
| `/api/v1/user/withdraw_eligibility` | GET | 提现资格 |
| `/api/v1/user/withdraw_record` | GET | 提现记录 |
| `/api/v1/user/survey_info` | GET | 问卷信息 |
| `/api/v1/user/guide/complete` | POST | 完成引导 |
| `/api/v1/user/high-freq-words` | GET | 高频词 |

### 📦 收藏 / 历史 / 通知

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/favorite/` | POST | 创建收藏 |
| `/api/v1/favorite/list` | GET | 收藏列表 |
| `/api/v1/favorite/details` | GET | 收藏详情 |
| `/api/v1/favorite/status` | GET | 收藏状态 |
| `/api/v1/favorite/resume` | POST | 恢复收藏 |
| `/api/v1/favorite/categories` | GET | 收藏分类 |
| `/api/v1/history/` | POST | 创建历史 |
| `/api/v1/history/list` | GET | 历史列表 |
| `/api/v1/history/title` | PUT | 更新历史标题 |
| `/api/v1/history/batch/delete` | POST | 批量删除历史 |
| `/api/v1/notify/all` | GET | 全部通知 |
| `/api/v1/notify/list` | GET | 通知列表 |

### 🏷️ 标签 / 模板 / 配置

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/tag/list` | GET | 标签列表 |
| `/api/v1/label/` | POST | 创建标签 |
| `/api/v1/label/list` | GET | 标签列表 |
| `/api/v1/label/category` | GET | 标签分类 |
| `/api/v1/model/` | GET | 模型配置 |
| `/api/v1/template/list` | GET | 模板列表 |
| `/api/v1/setting_template/` | POST | 创建设定模板 |
| `/api/v1/setting_template/list` | GET | 设定模板列表 |
| `/api/v1/setting_template/themes` | GET | 模板主题 |
| `/api/v1/config` | GET | 全局配置 |
| `/api/v1/feature-flags` | GET | 功能开关 |
| `/api/v1/creator` | GET | 创作者信息 |
| `/api/v1/agent_skill` | GET | Agent 技能列表 |
| `/api/v1/prompt_template/list?type=` | GET | Prompt 模板列表 |

### 📊 统计 / 事件 / 工具

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/stat/usage` | GET | 用量统计 |
| `/api/v1/event/trigger` | POST | 事件触发 |
| `/api/v1/event/track_convert` | POST | 转化追踪 |
| `/api/v1/event/utm_report` | POST | UTM 上报 |
| `/api/v1/tools/ai_detect` | POST | AI 检测 |
| `/api/v1/robot/generate` | POST | 机器人生成 |
| `/api/v1/robot/rewrite_ai_generate` | POST | 机器人改写 |
| `/api/v1/captcha/challenge` | POST | 验证码挑战 |
| `/api/v1/captcha/mp/notify-status` | POST | 验证码状态通知 |
| `/api/v1/front-error` | POST | 前端错误上报 |
| `/api/v1/push-message` | POST | 推送消息 |

### 📁 文件 / Job / 学习中心

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/file/simpleupload` | POST | 简单上传 |
| `/api/v1/file/chunkupload/init` | POST | 分块上传初始化 |
| `/api/v1/file/chunkupload/part` | POST | 分块上传分片 |
| `/api/v1/file/chunkupload/complete` | POST | 完成分块上传 |
| `/api/v1/file/chunkupload/abort` | POST | 中止分块上传 |
| `/api/v1/job/status` | GET | Job 状态 |
| `/api/v1/job/status/list` | POST | Job 状态列表 |
| `/api/v1/job/relate/jobs` | GET | 关联 Job |
| `/api/v1/learning_center/list` | GET | 学习中心列表 |
| `/api/v1/learning_center/course/list` | GET | 课程列表 |
| `/api/v1/learning_center/statistic` | POST | 学习统计 |

### 🎯 营销 / 运营

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/promotions/active` | GET | 活动促销 |
| `/api/v1/coupon/list` | GET | 优惠券列表 |
| `/api/v1/campaign/list` | GET | 活动列表 |
| `/api/v1/campaign/{campaign_id}/user` | GET | 活动用户信息 |
| `/api/v1/campaign/{campaign_id}/payoff` | POST | 活动奖励 |
| `/api/v1/acquisition-campaign/me/settle` | POST | 获客活动结算 |
| `/api/v1/activity-checkin/me` | GET | 签到信息 |
| `/api/v1/signin` | POST | 签到 |
| `/api/v1/task-center` | GET | 任务中心 |
| `/api/v1/customer_service_qrcode/list/all` | GET | 客服二维码列表 |

### 🏆 排行榜

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/ugc_leaderboard/config` | GET | UGC 排行榜配置 |
| `/api/v1/ugc_leaderboard/config/list` | GET | 排行榜配置列表 |
| `/api/v1/workflow_leaderboard/config` | GET | 工作流排行榜配置 |
| `/api/v1/workflow_leaderboard/config/list` | GET | 工作流排行榜配置列表 |
| `/api/v1/workflow_leaderboard/leaderboard/{id}/my-rank` | GET | 我的排名 |

### 🔌 其他

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/feedback/` | POST | 提交反馈 |

### 🔧 后台管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/admin/promotions` | GET/POST | 管理促销 |
| `/api/v1/backend/cdk/list` | GET | CDK 列表 |
| `/api/v1/backend/customer_service/qrcode/config` | GET/POST | 客服二维码配置 |
| `/api/v1/backend/invite/list` | GET | 后台邀请列表 |
| `/api/v1/backend/learning_center` | GET/POST | 后台学习中心 |
| `/api/v1/backend/learning_center/list` | GET | 学习中心管理列表 |
| `/api/v1/backend/learning_center/category/config` | GET/POST | 分类配置 |
| `/api/v1/backend/learning_center/course/upload` | POST | 课程上传 |
| `/api/v1/backend/popup/resource/{id}` | GET | 弹窗资源 |

---

## v2 API

### 📖 小说 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/` | POST | 创建小说 |
| `/api/v2/novel/list` | GET | 小说列表 |
| `/api/v2/novel/import` | POST | 导入小说 |
| `/api/v2/novel/export` | POST | 导出小说 |
| `/api/v2/novel/parse_chapters` | POST | 解析章节 |
| `/api/v2/novel/copy/{base_novel_id}/settings` | POST | 复制设定 |
| `/api/v2/novel/{novel_id}/structure` | GET | **获取结构树**（卷→章→节点） |
| `/api/v2/novel/{novel_id}/chapter` | POST | 创建章节 |
| `/api/v2/novel/{novel_id}/chapters_create` | POST | 批量创建章节 |
| `/api/v2/novel/{novel_id}/chapter/{node_id}` | GET/PUT/DELETE | 章内容 CRUD |
| `/api/v2/novel/{novel_id}/chapter/{node_id}/index` | PUT | 章排序 |
| `/api/v2/novel/{novel_id}/volume` | POST | 创建卷 |
| `/api/v2/novel/{novel_id}/volumes` | GET | 卷列表 |
| `/api/v2/novel/{novel_id}/volume/{volume_id}` | GET/PUT/DELETE | 卷 CRUD |
| `/api/v2/novel/{novel_id}/volume/{volume_id}/index` | PUT | 卷排序 |
| `/api/v2/novel/{base_novel_id}/claim` | POST | 认领小说 |
| `/api/v2/novel/{base_novel_id}/quick-preview` | GET | 快速预览 |
| `/api/v2/novel/{base_novel_id}/import_chapters` | POST | 导入章节 |

### 👤 角色 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/{base_novel_id}/character/{character_id}` | GET/PUT/DELETE | 角色 CRUD |
| `/api/v2/novel/{base_novel_id}/character/{character_id}/restore` | POST | 恢复角色 |

### 🌍 设定 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/{base_novel_id}/setting/{setting_id}` | GET/PUT/DELETE | 设定 CRUD |
| `/api/v2/novel/{base_novel_id}/setting/{setting_id}/restore` | POST | 恢复设定 |
| `/api/v2/novel/{base_novel_id}/background_setting/{setting_id}` | GET/PUT/DELETE | 背景设定 CRUD |
| `/api/v2/novel/{base_novel_id}/background_setting/{setting_id}/restore` | POST | 恢复背景设定 |
| `/api/v2/novel/{base_novel_id}/faction_setting/{setting_id}` | GET/PUT/DELETE | 势力设定 CRUD |
| `/api/v2/novel/{base_novel_id}/faction_setting/{setting_id}/restore` | POST | 恢复势力设定 |

### 🗑️ 回收站 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/{base_novel_id}/deleted_content` | GET | 已删除内容 |
| `/api/v2/novel/{base_novel_id}/deleted_items` | GET | 已删除项列表 |
| `/api/v2/novel/{base_novel_id}/restore_content` | POST | 恢复内容 |
| `/api/v2/novel/{base_novel_id}/restore_items` | POST | 批量恢复 |
| `/api/v2/novel/{base_novel_id}/volume/{volume_id}/restore` | POST | 恢复卷 |
| `/api/v2/novel/{base_novel_id}/chapter/{node_id}/restore` | POST | 恢复章 |
| `/api/v2/novel/{base_novel_id}/draft_folder/{folder_id}/restore` | POST | 恢复草稿夹 |
| `/api/v2/novel/{base_novel_id}/draft/{draft_id}/restore` | POST | 恢复草稿 |

### 📝 草稿 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/{novel_id}/draft` | GET/POST | 草稿列表/创建 |
| `/api/v2/novel/{novel_id}/draft/{draft_id}` | GET/PUT/DELETE | 草稿 CRUD |
| `/api/v2/novel/{novel_id}/draft_folder` | GET/POST | 草稿夹列表/创建 |
| `/api/v2/novel/{novel_id}/draft_folder/{folder_id}` | GET/PUT/DELETE | 草稿夹 CRUD |
| `/api/v2/novel/{novel_id}/draft_structure` | GET | 草稿结构 |
| `/api/v2/novel/{novel_id}/draft/{draft_id}/index?reposition=` | PUT | 草稿排序 |
| `/api/v2/novel/{novel_id}/draft_folder/{folder_id}/index?reposition=` | PUT | 草稿夹排序 |

### 🎨 封面 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/cover/detail` | GET | 封面详情 |
| `/api/v2/novel/cover/image/generate` | POST | 生成封面图 |
| `/api/v2/novel/cover/prompt/extract` | POST | 提取封面 Prompt |
| `/api/v2/novel/cover/save` | POST | 保存封面 |
| `/api/v2/novel/cover/upload` | POST | 上传封面 |

### 🎬 视频 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/novel/chapter/video/file/upload` | POST | 上传视频文件 |
| `/api/v2/novel/chapter/video/free/check` | GET | 免费额度检查 |
| `/api/v2/novel/chapter/video/generation/models` | GET | 生成模型列表 |
| `/api/v2/novel/chapter/video/generate/admin/video` | POST | 管理员生成视频 |
| `/api/v2/novel/chapter/video/generate/admin/visual` | POST | 管理员生成视觉 |
| `/api/v2/novel/chapter/video/tts` | POST | TTS 语音合成 |
| `/api/v2/novel/chapter/video/image/editing` | POST | 图片编辑 |
| `/api/v2/novel/chapter/video/materials/download/start` | POST | 开始素材下载 |
| `/api/v2/novel/chapter/video/materials/download/result` | GET | 下载结果 |
| `/api/v2/novel/chapter/video/visual_style/list` | GET | 视觉风格列表 |
| `/api/v2/novel/chapter/video/visual_style/get/{style_id}` | GET | 视觉风格详情 |
| `/api/v2/novel/chapter/video/visual_style/upload` | POST | 上传视觉风格 |
| `/api/v2/novel/chapter/video/visual_style/extract` | POST | 提取视觉风格 |
| `/api/v2/novel/chapter/video/visual_style/refine` | POST | 优化视觉风格 |
| `/api/v2/novel/chapter/video/visual_style/apply` | POST | 应用视觉风格 |
| `/api/v2/novel/chapter/video/visual_style/update_name` | PUT | 更新风格名称 |
| `/api/v2/novel/chapter/video/visual_style/delete/{style_id}` | DELETE | 删除视觉风格 |
| `/api/v2/novel/chapter/video/visual_style/{style_id}/shelf_status` | PUT | 上架/下架风格 |

### 📋 UGC 签约 v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/ugc/contract/status` | GET | 签约状态 |
| `/api/v2/ugc/contract/sign` | POST | 签约 |
| `/api/v2/ugc/contract/eligibility-detail` | GET | 签约资格详情 |
| `/api/v2/ugc/contract/dismiss-popup` | POST | 关闭签约弹窗 |

### 🔑 CDK v2

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/cdk/verify?code=` | GET | CDK 验证 |

---

## 统计

| 版本 | 端点数 |
|------|--------|
| v1 | ~175 |
| v2 | ~55 |
| **总计** | **~230** |

## 核心能力

1. **AI 对话写作** — `/chat/completion`（SSE 流式）、会话管理、消息分支
2. **小说拆书/转换** — `/novel/convert`、`/novel/unpack`、`/novel/import`
3. **小说结构化编辑** — 卷/章/节点树、排序、回收站、草稿系统
4. **角色/设定管理** — character、setting、background_setting、faction_setting
5. **UGC 生态** — Prompt 广场、Workflow 广场、排行榜、权限系统
6. **视频生成** — 分镜、角色、图片、TTS、视觉风格
7. **封面生成** — AI 封面图生成
8. **支付体系** — 会员、金币、IAP、优惠券、订单
9. **邀请裂变** — 邀请码、排行榜、提现
10. **文件上传** — 简单上传 + 分块上传（支持大文件）
