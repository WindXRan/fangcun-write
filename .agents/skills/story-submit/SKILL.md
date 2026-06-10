# Skill: story-submit

# story-submit · 自动投稿

将导出的小说txt自动投稿到蛙蛙写作平台。

## 触发条件

用户说：`/submit`、`投稿`、`自动投稿`、`上传到蛙蛙`

## 前置条件

1. 已安装playwright：`pip install playwright && playwright install chromium`
2. 夸克浏览器已登录蛙蛙写作（首次需手动登录）

## 使用方式

```powershell
python .agents/skills/story-submit/submit.py --book <导出的txt文件路径>
```

示例：
```powershell
python .agents/skills/story-submit/submit.py --book "projects/闻栖/分手了？秦少火速领证上位/rewrites/分手了？秦少火速领证上位仿写/export/他说我配不上？转身我成了他对手.txt"
```

## 投稿流程

1. 连接夸克浏览器（CDP调试端口9222）
2. 打开投稿页：https://wawawriter.com/app/submission/create
3. 上传txt文件
4. 关闭章节预览弹窗
5. 自动填写：作品名称、笔名、字数、类目、简介
6. 需手动选择：频道（女频）、状态（连载中）、标签

## 限制

- Element Plus的Vue组件（radio按钮、tag标签）不响应playwright的程序化点击
- 频道、状态、标签需手动选择（约30秒工作量）
