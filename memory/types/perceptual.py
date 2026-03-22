from typing import Dict, Any, List, Optional
from ..base import BaseMemory, MemoryItem, MemoryConfig


class PerceptualMemory(BaseMemory):
    """感知记忆实现
    
    特点：
    - 支持多模态数据（文本、图像、音频等）
    - 跨模态相似性搜索
    - 感知数据的语义理解
    - 支持内容生成和检索
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 多模态编码器
        self.text_embedder = get_text_embedder()
        self._clip_model = self._init_clip_model()  # 图像编码
        self._clap_model = self._init_clap_model()  # 音频编码
        
        # 按模态分离的向量存储
        self.vector_stores = {
            "text": QdrantConnectionManager.get_instance(
                collection_name="perceptual_text",
                vector_size=self.vector_dim
            ),
            "image": QdrantConnectionManager.get_instance(
                collection_name="perceptual_image", 
                vector_size=self._image_dim
            ),
            "audio": QdrantConnectionManager.get_instance(
                collection_name="perceptual_audio",
                vector_size=self._audio_dim
            )
        }

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索感知记忆（可筛模态；同模态向量检索+时间/重要性融合）"""
        user_id = kwargs.get("user_id")
        target_modality = kwargs.get("target_modality")
        query_modality = kwargs.get("query_modality", target_modality or "text")
        
        # 同模态向量检索
        try:
            query_vector = self._encode_data(query, query_modality)
            store = self._get_vector_store_for_modality(target_modality or query_modality)
            
            where = {"memory_type": "perceptual"}
            if user_id:
                where["user_id"] = user_id
            if target_modality:
                where["modality"] = target_modality
            
            hits = store.search_similar(
                query_vector=query_vector,
                limit=max(limit * 5, 20),
                where=where
            )
        except Exception:
            hits = []
        
        # 融合排序（向量相似度 + 时间近因性 + 重要性权重）
        results = []
        for hit in hits:
            vector_score = float(hit.get("score", 0.0))
            recency_score = self._calculate_recency_score(hit["metadata"]["timestamp"])
            importance = hit["metadata"].get("importance", 0.5)
            
            # 评分算法
            base_relevance = vector_score * 0.8 + recency_score * 0.2
            importance_weight = 0.8 + (importance * 0.4)
            combined_score = base_relevance * importance_weight
            
            results.append((combined_score, self._create_memory_item(hit)))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]


    def _calculate_recency_score(self, timestamp: str) -> float:
        """计算时间近因性得分"""
        try:
            memory_time = datetime.fromisoformat(timestamp)
            current_time = datetime.now()
            age_hours = (current_time - memory_time).total_seconds() / 3600
            
            # 指数衰减：24小时内保持高分，之后逐渐衰减
            decay_factor = 0.1  # 衰减系数
            recency_score = math.exp(-decay_factor * age_hours / 24)
            
            return max(0.1, recency_score)  # 最低保持0.1的基础分数
        except Exception:
            return 0.5  # 默认中等分数
