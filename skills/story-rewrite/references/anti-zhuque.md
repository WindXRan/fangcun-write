# 朱雀 AI 检测专项防御

> 基于 2026-05-30 实测反馈（仿写产出正文 AIGC 0.93-0.99）。
> 本文件供 Phase 3 prompt 构造时嵌入，以及 Phase 5 质量检查时参考。

---

## 核心认知

朱雀检测的不是"禁用词"，而是**叙事结构的完整性**。

AI 写作和人类写作的本质区别：
- AI：每个场景都完整（进入→展开→高潮→反应→收尾），段落均匀，逻辑链完整
- 人类：场景断裂、段落长短悬殊、思考不完整、对话标签混乱

**目标**：把 AIGC 值从 0.9+ 压到 0.5 以下。

---

## 朱雀识别的 4 个高权重特征（按杀伤力排序）

### 特征 1：场景弧线完整度（权重最高）

朱雀能识别每个场景是否包含完整的"进入→展开→高潮→反应→收尾"五步。

**解法**：每 2 个场景破坏至少 1 个。
- 砍头：不写"她走进门"，直接写"桌子上摆着三菜一汤"
- 砍尾：冲突完不写角色反应，直接切下一场
- 拦腰：在高潮处突然中断，下一段跳到完全无关的事

### 特征 2：段落长度分布

朱雀计算相邻段落的字数差，差值小 → AI。

**解法**：强制相邻段字数差 ≥3 倍。
```
10字 → 120字 → 8字 → 200字 → 15字
```
每章至少 1 个独词段。

### 特征 3：内心独白完整性

朱雀识别角色思考的"推理链"——从问题到分析到结论的完整过程。

**解法**：内心独白 ≤2 句，第 3 句必须切动作/对话。
- ❌ "跑什么？跑得掉吗？七块三毛钱，她能跑哪儿去？跑出去冻死？还不如淹死呢。先稳住。必须稳住。"（6句完整链）
- ✓ "跑什么？跑得掉吗？算了，先稳住。"（2句+动作）

### 特征 4：对话标签交替规律

朱雀识别"她说→他说→她说"的规律交替模式。

**解法**：4 种标签格式混用，任一种不连续出现 2 次。
1. 无标签：直接写对话内容
2. 动作代标签：他把杯子放下。"内容"
3. 后置标签："内容"他说
4. 前置标签：他说："内容"

---

## Phase 5 验证脚本

```powershell
# 快速朱雀筛查（4项）

$content = Get-Content '文件路径' -Encoding UTF8 -Raw

# 1. 内心独白超长检测
$innerThoughts = [regex]::Matches($content, '[。！？][^。！？]{10,}(想|觉得|知道|明白)[^。！？]{10,}[。！？]')
if ($innerThoughts.Count -ge 3) { Write-Warning "内心独白过长："+$innerThoughts.Count }

# 2. 情绪词密度
$emotionWords = "心里咯噔|心跳漏了一拍|愣住了|僵住了|大脑空白"
$matches = [regex]::Matches($content, $emotionWords)
if ($matches.Count -ge 2) { Write-Warning "情绪词重复："+$matches.Count }

# 3. 对话标签规律性
$dialogTags = [regex]::Matches($content, '(他说|她说|他问|她问)')
# 简单检查：每100字超过3个标签则可能太规律
$tagsPer100 = [math]::Round($dialogTags.Count / ($content.Length / 100), 1)
if ($tagsPer100 -gt 3) { Write-Warning "对话标签过密："+$tagsPer100+"/100字" }

# 4. 段落长度分布
$paragraphs = $content -split '\r?\n\r?\n'
$lengths = $paragraphs | ForEach-Object { ($_ -replace '\s','').Length }
$avg = ($lengths | Measure-Object -Average).Average
$std = 0
if ($lengths.Count -gt 1) {
    $variance = ($lengths | ForEach-Object { [math]::Pow($_ - $avg, 2) } | Measure-Object -Average).Average
    $std = [math]::Sqrt($variance)
}
Write-Output "段落长度均值：$avg, 标准差：$std"
if ($std -lt 30) { Write-Warning "段落太均匀，标准差仅 $std" }
```
