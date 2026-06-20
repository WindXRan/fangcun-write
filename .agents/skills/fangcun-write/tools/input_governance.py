"""
输入治理：规则优先级系统

参考inkos的input-governance设计：
- L4: 硬约束（不可违反）
- L3: 任务意图（当前章节目标）
- L2: 卷纲规划（整体结构）
- L1: 默认行为（模型默认）

优先级：L4 > L3 > L2 > L1
当L3和L2冲突时，优先执行L3
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class RuleLevel(Enum):
    """规则层级"""
    L1_DEFAULT = 1  # 默认行为
    L2_OUTLINE = 2  # 卷纲规划
    L3_INTENT = 3   # 任务意图
    L4_HARD = 4     # 硬约束


@dataclass
class RuleLayer:
    """规则层"""
    level: RuleLevel
    name: str
    rules: List[str] = field(default_factory=list)


@dataclass
class ChapterIntent:
    """章节意图"""
    chapter: int
    goal: str  # 本章目标
    must_keep: List[str] = field(default_factory=list)  # 必须保留
    must_avoid: List[str] = field(default_factory=list)  # 必须避免
    style_emphasis: List[str] = field(default_factory=list)  # 风格重点


@dataclass
class RuleStack:
    """规则栈"""
    layers: List[RuleLayer] = field(default_factory=list)
    active_overrides: List[Dict] = field(default_factory=list)
    
    def get_effective_rules(self) -> List[str]:
        """获取有效规则（按优先级排序）"""
        # 按优先级排序
        sorted_layers = sorted(self.layers, key=lambda x: x.level.value, reverse=True)
        
        # 合并规则
        rules = []
        for layer in sorted_layers:
            rules.extend(layer.rules)
        
        return rules
    
    def get_hard_constraints(self) -> List[str]:
        """获取硬约束"""
        for layer in self.layers:
            if layer.level == RuleLevel.L4_HARD:
                return layer.rules
        return []
    
    def get_intent(self) -> Optional[ChapterIntent]:
        """获取任务意图"""
        for layer in self.layers:
            if layer.level == RuleLevel.L3_INTENT:
                # 从规则中提取意图
                if layer.rules:
                    return ChapterIntent(
                        chapter=0,
                        goal=layer.rules[0] if layer.rules else "",
                        must_keep=layer.rules[1:] if len(layer.rules) > 1 else []
                    )
        return None


@dataclass
class InputGovernance:
    """输入治理配置"""
    rule_stack: RuleStack = field(default_factory=RuleStack)
    chapter_intent: Optional[ChapterIntent] = None
    
    def build_governance_section(self) -> str:
        """构建输入治理prompt段"""
        lines = ["## 输入治理"]
        
        # 硬约束
        hard_constraints = self.rule_stack.get_hard_constraints()
        if hard_constraints:
            lines.append("\n### 硬约束（不可违反）")
            for i, rule in enumerate(hard_constraints, 1):
                lines.append(f"{i}. {rule}")
        
        # 任务意图
        if self.chapter_intent:
            intent = self.chapter_intent
            lines.append(f"\n### 本章任务")
            lines.append(f"目标：{intent.goal}")
            
            if intent.must_keep:
                lines.append("\n必须保留：")
                for item in intent.must_keep:
                    lines.append(f"- {item}")
            
            if intent.must_avoid:
                lines.append("\n必须避免：")
                for item in intent.must_avoid:
                    lines.append(f"- {item}")
            
            if intent.style_emphasis:
                lines.append("\n风格重点：")
                for item in intent.style_emphasis:
                    lines.append(f"- {item}")
        
        # 有效规则
        effective_rules = self.rule_stack.get_effective_rules()
        if effective_rules:
            lines.append("\n### 有效规则（按优先级排序）")
            for i, rule in enumerate(effective_rules[:10], 1):  # 只显示前10条
                lines.append(f"{i}. {rule}")
        
        return '\n'.join(lines)
    
    def check_conflict(self, new_rule: str) -> Optional[str]:
        """检查新规则是否与现有规则冲突"""
        # 检查是否与硬约束冲突
        hard_constraints = self.rule_stack.get_hard_constraints()
        for constraint in hard_constraints:
            if self._rules_conflict(new_rule, constraint):
                return f"与硬约束冲突：{constraint}"
        
        # 检查是否与任务意图冲突
        if self.chapter_intent:
            if self.chapter_intent.must_avoid:
                for avoid in self.chapter_intent.must_avoid:
                    if avoid in new_rule:
                        return f"与任务意图冲突：必须避免 {avoid}"
        
        return None
    
    def _rules_conflict(self, rule1: str, rule2: str) -> bool:
        """检查两条规则是否冲突"""
        # 简单的冲突检测
        conflict_pairs = [
            ("必须", "禁止"),
            ("一定要", "不能"),
            ("需要", "不需要"),
        ]
        
        for positive, negative in conflict_pairs:
            if positive in rule1 and negative in rule2:
                return True
            if negative in rule1 and positive in rule2:
                return True
        
        return False


def build_governance_from_config(config: Dict) -> InputGovernance:
    """从配置构建输入治理"""
    governance = InputGovernance()
    
    # 构建规则栈
    rule_stack = RuleStack()
    
    # L4: 硬约束
    hard_rules = config.get("hard_constraints", [])
    if hard_rules:
        rule_stack.layers.append(RuleLayer(
            level=RuleLevel.L4_HARD,
            name="硬约束",
            rules=hard_rules
        ))
    
    # L3: 任务意图
    chapter_intent = config.get("chapter_intent", {})
    if chapter_intent:
        intent = ChapterIntent(
            chapter=chapter_intent.get("chapter", 0),
            goal=chapter_intent.get("goal", ""),
            must_keep=chapter_intent.get("must_keep", []),
            must_avoid=chapter_intent.get("must_avoid", []),
            style_emphasis=chapter_intent.get("style_emphasis", [])
        )
        governance.chapter_intent = intent
        
        rule_stack.layers.append(RuleLayer(
            level=RuleLevel.L3_INTENT,
            name="任务意图",
            rules=[intent.goal] + intent.must_keep
        ))
    
    # L2: 卷纲规划
    outline_rules = config.get("outline_rules", [])
    if outline_rules:
        rule_stack.layers.append(RuleLayer(
            level=RuleLevel.L2_OUTLINE,
            name="卷纲规划",
            rules=outline_rules
        ))
    
    governance.rule_stack = rule_stack
    
    return governance
