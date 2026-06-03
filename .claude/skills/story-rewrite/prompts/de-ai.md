# 全书去AI（Phase 3）

## 流程

```
3.1 脚本处理（自动）
    ├── de-ai-connectors.ps1  # 连接词降频
    ├── de-ai-punctuation.ps1 # 标点处理
    └── de-ai-numbers.ps1     # 数字模糊化

3.2 LLM重写（anti-detect模式）
    └── 逐章重写，降低AI痕迹
```

---

## 3.1 脚本处理

对每个正文文件执行：

```powershell
for file in {书名}/正文/*.txt {
    powershell -ExecutionPolicy Bypass -File tools/de-ai-connectors.ps1 -Path $file
    powershell -ExecutionPolicy Bypass -File tools/de-ai-punctuation.ps1 -Path $file
    powershell -ExecutionPolicy Bypass -File tools/de-ai-numbers.ps1 -Path $file
}
```

---

## 3.2 LLM重写（anti-detect模式）

**改写手法（参考inkos）**：

1. 打破句式规律：连续短句 → 长短交替
2. 口语化替代："然而事情并没有那么简单" → "哪有那么便宜的事"
3. 减少"了"字密度："他走了过去，拿了杯子" → "他走过去，端起杯子"
4. 转折词降频：用角色内心吐槽或动作切换
5. 情绪外化："他感到愤怒" → "他捏碎了茶杯"
6. 删掉叙述者结论：只写行动，让读者自己感受
7. 群像反应具体化："全场震惊" → "老陈的烟掉在裤子上"
8. 段落长度差异化：有的段只有一句话，有的段七八行
9. 消灭AI标记词：不禁、仿佛、宛如

**执行方式**：
- 读取正文
- 按照上述规则重写
- 输出到原文件
