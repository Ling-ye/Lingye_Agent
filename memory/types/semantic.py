from typing import Dict, Any, List, Optional
from ..base import BaseMemory, MemoryItem, MemoryConfig

class SemanticMemory(BaseMemory):
    """语义记忆实现
    
    特点：
    - 使用HuggingFace中文预训练模型进行文本嵌入
    - 向量检索进行快速相似度匹配
    - 知识图谱存储实体和关系
    - 混合检索策略：向量+图+语义推理
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 嵌入模型（统一提供）
        self.embedding_model = get_text_embedder()
        
        # 专业数据库存储
        self.vector_store = QdrantConnectionManager.get_instance(**qdrant_config)
        self.graph_store = Neo4jGraphStore(**neo4j_config)
        
        # 实体和关系缓存
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        
        # NLP处理器（支持中英文）
        self.nlp = self._init_nlp()

    def add(self, memory_item: MemoryItem) -> str:
        """添加语义记忆"""
        # 1. 生成文本嵌入
        embedding = self.embedding_model.encode(memory_item.content)
        
        # 2. 提取实体和关系
        entities = self._extract_entities(memory_item.content)
        relations = self._extract_relations(memory_item.content, entities)
        
        # 3. 存储到Neo4j图数据库
        for entity in entities:
            self._add_entity_to_graph(entity, memory_item)
        
        for relation in relations:
            self._add_relation_to_graph(relation, memory_item)
        
        # 4. 存储到Qdrant向量数据库
        metadata = {
            "memory_id": memory_item.id,
            "entities": [e.entity_id for e in entities],
            "entity_count": len(entities),
            "relation_count": len(relations)
        }
        
        self.vector_store.add_vectors(
            vectors=[embedding.tolist()],
            metadata=[metadata],
            ids=[memory_item.id]
        )


    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索语义记忆"""
        # 1. 向量检索
        vector_results = self._vector_search(query, limit * 2, user_id)
        
        # 2. 图检索
        graph_results = self._graph_search(query, limit * 2, user_id)
        
        # 3. 混合排序
        combined_results = self._combine_and_rank_results(
            vector_results, graph_results, query, limit
        )
        
        return combined_results[:limit]

    def _combine_and_rank_results(self, vector_results, graph_results, query, limit):
        """混合排序结果"""
        combined = {}
        
        # 合并向量和图检索结果
        for result in vector_results:
            combined[result["memory_id"]] = {
                **result,
                "vector_score": result.get("score", 0.0),
                "graph_score": 0.0
            }
        
        for result in graph_results:
            memory_id = result["memory_id"]
            if memory_id in combined:
                combined[memory_id]["graph_score"] = result.get("similarity", 0.0)
            else:
                combined[memory_id] = {
                    **result,
                    "vector_score": 0.0,
                    "graph_score": result.get("similarity", 0.0)
                }
        
        # 计算混合分数
        # (向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)
        for memory_id, result in combined.items():
            vector_score = result["vector_score"]
            graph_score = result["graph_score"]
            importance = result.get("importance", 0.5)
            
            # 基础相似度得分
            base_relevance = vector_score * 0.7 + graph_score * 0.3
            
            # 重要性权重 [0.8, 1.2]
            importance_weight = 0.8 + (importance * 0.4)
            
            # 最终得分：相似度 * 重要性权重
            combined_score = base_relevance * importance_weight
            result["combined_score"] = combined_score
        
        # 排序并返回
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return sorted_results[:limit]
