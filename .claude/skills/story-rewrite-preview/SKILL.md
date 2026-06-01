---
name: story-rewrite-preview
description: |
  仿写试水。只写3章预览效果，不写全书。
  触发方式：/story-rewrite-preview、/仿写试水、「先试写3章」「仿写预览」
---

# story-rewrite-preview · 仿写试水

## 功能

用爆款骨架只写3章，预览仿写效果。确认OK后再用 /story-rewrite 写全书。

## 使用方式

```
/story-rewrite-preview
```

## 流程

1. 读取源小说（authors/ 目录下）
2. 分析骨架结构
3. 用新设定写3章预览
4. 输出到 `仿写试水库/预览_{书名}/`
5. 询问用户是否继续写全书

## 与 story-rewrite 的关系

- preview：只写3章，快速验证效果
- rewrite：写全书，完整流程