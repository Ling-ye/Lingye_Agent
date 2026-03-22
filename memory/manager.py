from typing import Dict, Any, List, Optional
from .base import MemoryItem, MemoryConfig
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory


class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口"""

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "default_user",
        enable_working: bool = True,
        enable_episodic: bool = True,
        enable_semantic: bool = True,
        enable_perceptual: bool = False,
    ):
        self.config = config or MemoryConfig()
        self.user_id = user_id

        # 初始化各类型记忆
        self.memory_types = {}
        
        if enable_working:
            self.memory_types['working'] = WorkingMemory(self.config)
        
        if enable_episodic:
            self.memory_types['episodic'] = EpisodicMemory(self.config)
            
        if enable_semantic:
            self.memory_types['semantic'] = SemanticMemory(self.config)
            
        if enable_perceptual:
            self.memory_types['perceptual'] = PerceptualMemory(self.config)
