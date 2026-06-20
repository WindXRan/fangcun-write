"""
fangcun-write: 同人/续写模式配置

支持inkos风格的4种同人模式：
- canon: 原作向同人（严格遵守正典）
- au: 平行世界同人（世界规则可改，角色性格保持）
- ooc: OOC同人（角色可偏离性格底色，但有情境驱动）
- cp: CP同人（以角色互动和关系发展为核心）
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import json


@dataclass
class FanficMode:
    """同人模式配置"""
    name: str  # canon/au/ooc/cp
    description: str
    allowed_deviations: List[str] = field(default_factory=list)
    
    # 审核维度严重程度
    character_fidelity: str = "critical"  # 角色还原度
    world_rules: str = "critical"  # 世界规则遵守
    relationship_dynamics: str = "warning"  # 关系动态
    canon_consistency: str = "critical"  # 正典事件一致性


# 预定义模式
MODES = {
    "canon": FanficMode(
        name="canon",
        description="原作向同人：严格遵守正典，角色语癖/说话风格/行为模式必须与原作一致",
        character_fidelity="critical",
        world_rules="critical",
        relationship_dynamics="warning",
        canon_consistency="critical",
    ),
    "au": FanficMode(
        name="au",
        description="平行世界同人：世界规则可改，角色核心性格和说话方式保持辨识度",
        allowed_deviations=["世界规则", "时代背景", "地理设定"],
        character_fidelity="critical",
        world_rules="info",
        relationship_dynamics="warning",
        canon_consistency="info",
    ),
    "ooc": FanficMode(
        name="ooc",
        description="OOC同人：角色在极端情境下可偏离性格底色，但有情境驱动",
        allowed_deviations=["角色性格底色"],
        character_fidelity="info",
        world_rules="warning",
        relationship_dynamics="warning",
        canon_consistency="info",
    ),
    "cp": FanficMode(
        name="cp",
        description="CP同人：以角色互动和关系发展为核心",
        allowed_deviations=["关系发展"],
        character_fidelity="warning",
        world_rules="warning",
        relationship_dynamics="critical",
        canon_consistency="info",
    ),
}


@dataclass
class CharacterVoice:
    """角色语音档案"""
    name: str
    catchphrases: List[str] = field(default_factory=list)  # 口头禅/语癖
    speaking_style: str = ""  # 说话风格
    typical_behavior: str = ""  # 典型行为
    forbidden_phrases: List[str] = field(default_factory=list)  # 禁止使用的表达


@dataclass
class ChapterMemo:
    """章节备忘（7段结构化输入）"""
    current_task: str = ""  # 当前任务
    reader_waiting: str = ""  # 读者此刻在等什么
    payoffs: str = ""  # 该兑现的 / 暂不掀的
    daily_tasks: str = ""  # 日常/过渡承担什么任务
    key_choices: str = ""  # 关键抉择过三连问
    ending_changes: str = ""  # 章尾必须发生的改变
    hook_ledger: str = ""  # 本章 hook 账
    prohibitions: str = ""  # 不要做


@dataclass
class HookEntry:
    """伏笔条目"""
    hook_id: str
    description: str
    planted_chapter: int  # 种下时的章节
    seed_text: str = ""  # 种下时的原始文本片段
    status: str = "planted"  # planted/advanced/resolved/deferred
    resolve_chapter: Optional[int] = None  # 兑现章节


@dataclass
class FanficConfig:
    """同人/续写完整配置"""
    mode: str = "canon"  # canon/au/ooc/cp
    fanfic_canon: str = ""  # 正典参照内容
    character_voices: Dict[str, CharacterVoice] = field(default_factory=dict)
    chapter_memo: Optional[ChapterMemo] = None
    hook_ledger: List[HookEntry] = field(default_factory=list)
    
    def get_mode(self) -> FanficMode:
        return MODES.get(self.mode, MODES["canon"])
    
    def build_fanfic_section(self) -> str:
        """构建同人正典参照prompt段"""
        mode_obj = self.get_mode()
        
        sections = []
        
        # 模式说明
        sections.append(f"## 同人模式：{mode_obj.description}")
        
        # 允许的偏离
        if mode_obj.allowed_deviations:
            sections.append(f"允许偏离：{', '.join(mode_obj.allowed_deviations)}")
        
        # 正典参照
        if self.fanfic_canon:
            sections.append(f"## 正典参照\n\n{self.fanfic_canon}")
        
        # 角色语音档案
        if self.character_voices:
            voice_lines = ["## 角色语音档案"]
            for name, voice in self.character_voices.items():
                voice_lines.append(f"\n### {name}")
                if voice.catchphrases:
                    voice_lines.append(f"- 口头禅/语癖：{', '.join(voice.catchphrases)}")
                if voice.speaking_style:
                    voice_lines.append(f"- 说话风格：{voice.speaking_style}")
                if voice.typical_behavior:
                    voice_lines.append(f"- 典型行为：{voice.typical_behavior}")
                if voice.forbidden_phrases:
                    voice_lines.append(f"- 禁止使用：{', '.join(voice.forbidden_phrases)}")
            sections.append('\n'.join(voice_lines))
        
        return '\n\n'.join(sections)
    
    def build_chapter_memo_section(self) -> str:
        """构建章节备忘prompt段"""
        if not self.chapter_memo:
            return ""
        
        memo = self.chapter_memo
        lines = ["## 章节备忘"]
        
        if memo.current_task:
            lines.append(f"\n### 当前任务\n{memo.current_task}")
        if memo.reader_waiting:
            lines.append(f"\n### 读者此刻在等什么\n{memo.reader_waiting}")
        if memo.payoffs:
            lines.append(f"\n### 该兑现的 / 暂不掀的\n{memo.payoffs}")
        if memo.daily_tasks:
            lines.append(f"\n### 日常/过渡承担什么任务\n{memo.daily_tasks}")
        if memo.key_choices:
            lines.append(f"\n### 关键抉择过三连问\n{memo.key_choices}")
        if memo.ending_changes:
            lines.append(f"\n### 章尾必须发生的改变\n{memo.ending_changes}")
        if memo.hook_ledger:
            lines.append(f"\n### 本章 hook 账\n{memo.hook_ledger}")
        if memo.prohibitions:
            lines.append(f"\n### 不要做\n{memo.prohibitions}")
        
        return '\n'.join(lines)
    
    def build_audit_dimensions(self) -> str:
        """构建审核维度prompt段（参考inkos的5维度审核）"""
        mode_obj = self.get_mode()
        
        lines = ["## 审核维度（写完后自检）"]
        
        severity_map = {
            "critical": "（严格检查，违反即不合格）",
            "warning": "（警告级别，建议修正）",
            "info": "（仅记录，不判定失败）",
        }
        
        # 通用维度（5个）
        general_dims = [
            ("核心冲突", "critical", "是否有清晰且有足够张力的核心冲突？"),
            ("开篇节奏", "critical", "前几章能否形成翻页驱动力？"),
            ("世界一致性", "warning", "世界观是否内洽且具体？"),
            ("角色区分度", "warning", "主要角色的声音和动机是否各不相同？"),
            ("节奏可行性", "warning", "是否避免连续多章同一种节拍？"),
        ]
        
        # 同人/续写专用维度（4个）
        fanfic_dims = [
            ("角色还原度", mode_obj.character_fidelity, "检查角色的语癖、说话风格、行为模式是否与正典一致"),
            ("世界规则遵守", mode_obj.world_rules, "检查是否违反正典中的世界规则"),
            ("关系动态", mode_obj.relationship_dynamics, "检查角色之间的关系互动是否合理"),
            ("正典事件一致性", mode_obj.canon_consistency, "检查是否与正典关键事件时间线矛盾"),
        ]
        
        # 合并维度
        all_dims = general_dims + fanfic_dims
        
        for i, (name, severity, desc) in enumerate(all_dims, 1):
            severity_label = severity_map.get(severity, "")
            lines.append(f"{i}. **{name}** {severity_label}: {desc}")
        
        return '\n'.join(lines)
    
    def build_hook_ledger_section(self) -> str:
        """构建hook账本prompt段"""
        if not self.hook_ledger:
            return ""
        
        lines = ["## 伏笔账本"]
        lines.append("")
        lines.append("| ID | 描述 | 种下章节 | 状态 | 兑现章节 |")
        lines.append("|---|------|---------|------|---------|")
        
        for hook in self.hook_ledger:
            resolve_ch = str(hook.resolve_chapter) if hook.resolve_chapter else "-"
            lines.append(f"| {hook.hook_id} | {hook.description} | 第{hook.planted_chapter}章 | {hook.status} | {resolve_ch} |")
        
        lines.append("")
        lines.append("**硬对应规则：** advance/resolve 下面列出的每一个 hook_id 都必须在正文里有一个具体可定位的兑现段——写明人物对着什么物件/事件/信息做出什么可观察的动作或交谈。不允许"侧面暗示""留给下章"。")
        
        return '\n'.join(lines)
