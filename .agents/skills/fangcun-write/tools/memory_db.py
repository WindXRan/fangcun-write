"""
记忆系统：持久化存储故事状态

参考inkos的memory-db设计：
- 角色状态追踪
- 伏笔追踪
- 关系变化追踪
- 事件时间线
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class CharacterState:
    """角色状态"""
    name: str
    current_status: str = ""  # 当前状态
    location: str = ""  # 当前位置
    mood: str = ""  # 当前情绪
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他角色的关系
    last_seen_chapter: int = 0  # 最后出场章节
    notes: str = ""  # 备注


@dataclass
class HookState:
    """伏笔状态"""
    hook_id: str
    description: str
    planted_chapter: int
    seed_text: str = ""  # 种下时的原始文本片段
    status: str = "planted"  # planted/advanced/resolved/deferred
    resolve_chapter: Optional[int] = None
    resolve_text: str = ""  # 兑现时的文本片段


@dataclass
class RelationshipChange:
    """关系变化"""
    chapter: int
    character1: str
    character2: str
    old_status: str
    new_status: str
    reason: str


@dataclass
class TimelineEvent:
    """时间线事件"""
    chapter: int
    event: str
    characters: List[str] = field(default_factory=list)
    location: str = ""


@dataclass
class MemoryDB:
    """记忆数据库"""
    book_name: str = ""
    total_chapters: int = 0
    characters: Dict[str, CharacterState] = field(default_factory=dict)
    hooks: List[HookState] = field(default_factory=list)
    relationships: List[RelationshipChange] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    chapter_summaries: Dict[int, str] = field(default_factory=dict)
    last_updated: str = ""
    
    def save(self, path: str):
        """保存到文件"""
        self.last_updated = datetime.now().isoformat()
        data = asdict(self)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'MemoryDB':
        """从文件加载"""
        if not Path(path).exists():
            return cls()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        db = cls()
        db.book_name = data.get('book_name', '')
        db.total_chapters = data.get('total_chapters', 0)
        db.last_updated = data.get('last_updated', '')
        
        # 加载角色状态
        for name, char_data in data.get('characters', {}).items():
            db.characters[name] = CharacterState(**char_data)
        
        # 加载伏笔
        for hook_data in data.get('hooks', []):
            db.hooks.append(HookState(**hook_data))
        
        # 加载关系变化
        for rel_data in data.get('relationships', []):
            db.relationships.append(RelationshipChange(**rel_data))
        
        # 加载时间线
        for event_data in data.get('timeline', []):
            db.timeline.append(TimelineEvent(**event_data))
        
        # 加载章节摘要
        db.chapter_summaries = {int(k): v for k, v in data.get('chapter_summaries', {}).items()}
        
        return db
    
    def update_character(self, name: str, **kwargs):
        """更新角色状态"""
        if name not in self.characters:
            self.characters[name] = CharacterState(name=name)
        char = self.characters[name]
        for key, value in kwargs.items():
            if hasattr(char, key):
                setattr(char, key, value)
    
    def add_hook(self, hook_id: str, description: str, chapter: int, seed_text: str = ""):
        """添加伏笔"""
        hook = HookState(
            hook_id=hook_id,
            description=description,
            planted_chapter=chapter,
            seed_text=seed_text
        )
        self.hooks.append(hook)
    
    def advance_hook(self, hook_id: str, chapter: int, text: str = ""):
        """推进伏笔"""
        for hook in self.hooks:
            if hook.hook_id == hook_id:
                hook.status = "advanced"
                break
    
    def resolve_hook(self, hook_id: str, chapter: int, text: str = ""):
        """兑现伏笔"""
        for hook in self.hooks:
            if hook.hook_id == hook_id:
                hook.status = "resolved"
                hook.resolve_chapter = chapter
                hook.resolve_text = text
                break
    
    def add_relationship_change(self, chapter: int, char1: str, char2: str, 
                                old_status: str, new_status: str, reason: str):
        """添加关系变化"""
        change = RelationshipChange(
            chapter=chapter,
            character1=char1,
            character2=char2,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        )
        self.relationships.append(change)
    
    def add_timeline_event(self, chapter: int, event: str, 
                           characters: List[str] = None, location: str = ""):
        """添加时间线事件"""
        event_obj = TimelineEvent(
            chapter=chapter,
            event=event,
            characters=characters or [],
            location=location
        )
        self.timeline.append(event_obj)
    
    def set_chapter_summary(self, chapter: int, summary: str):
        """设置章节摘要"""
        self.chapter_summaries[chapter] = summary
    
    def get_character_context(self, name: str) -> str:
        """获取角色上下文（用于prompt注入）"""
        if name not in self.characters:
            return ""
        
        char = self.characters[name]
        lines = [f"【{name}】"]
        
        if char.current_status:
            lines.append(f"- 当前状态：{char.current_status}")
        if char.location:
            lines.append(f"- 当前位置：{char.location}")
        if char.mood:
            lines.append(f"- 当前情绪：{char.mood}")
        if char.relationships:
            lines.append("- 关系：")
            for other, rel in char.relationships.items():
                lines.append(f"  - 与{other}：{rel}")
        if char.notes:
            lines.append(f"- 备注：{char.notes}")
        
        return '\n'.join(lines)
    
    def get_active_hooks(self) -> List[HookState]:
        """获取活跃伏笔"""
        return [h for h in self.hooks if h.status in ("planted", "advanced")]
    
    def get_hooks_context(self) -> str:
        """获取伏笔上下文（用于prompt注入）"""
        active_hooks = self.get_active_hooks()
        if not active_hooks:
            return ""
        
        lines = ["## 活跃伏笔"]
        for hook in active_hooks:
            lines.append(f"- [{hook.hook_id}] {hook.description}（第{hook.planted_chapter}章种下）")
        
        return '\n'.join(lines)
    
    def get_recent_timeline(self, max_events: int = 10) -> str:
        """获取最近的时间线事件"""
        recent = self.timeline[-max_events:] if self.timeline else []
        if not recent:
            return ""
        
        lines = ["## 最近事件"]
        for event in recent:
            chars = '、'.join(event.characters) if event.characters else ''
            lines.append(f"- 第{event.chapter}章：{event.event}（{chars}）")
        
        return '\n'.join(lines)
    
    def build_context_for_chapter(self, ch_num: int) -> str:
        """为指定章节构建上下文"""
        parts = []
        
        # 角色状态
        char_lines = []
        for name, char in self.characters.items():
            if char.last_seen_chapter >= ch_num - 5:  # 只显示最近5章出场的角色
                context = self.get_character_context(name)
                if context:
                    char_lines.append(context)
        
        if char_lines:
            parts.append("## 角色状态\n" + '\n\n'.join(char_lines))
        
        # 活跃伏笔
        hooks_ctx = self.get_hooks_context()
        if hooks_ctx:
            parts.append(hooks_ctx)
        
        # 最近时间线
        timeline_ctx = self.get_recent_timeline()
        if timeline_ctx:
            parts.append(timeline_ctx)
        
        return '\n\n'.join(parts)
