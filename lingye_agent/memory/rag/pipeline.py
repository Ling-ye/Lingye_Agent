from typing import List, Dict, Optional, Any
import logging
import os
import hashlib
import time

logger = logging.getLogger(__name__)
from ..embedding import get_text_embedder, get_dimension
from ..storage.qdrant_store import QdrantVectorStore, QdrantConnectionManager


# 全 pipeline 统一使用的默认 RAG 集合名（可被 RAG_COLLECTION 环境变量覆盖）
_DEFAULT_RAG_COLLECTION = os.getenv("RAG_COLLECTION", "lingye_agents_rag_vectors")


def _get_markitdown_instance():
    """
    Get a configured MarkItDown instance for document conversion.
    """
    try:
        from markitdown import MarkItDown
        return MarkItDown()
    except ImportError:
        logger.warning("MarkItDown not available. Install with: pip install markitdown")
        return None


def _is_markitdown_supported_format(path: str) -> bool:
    """
    Check if the file format is supported by MarkItDown.
    Supports: PDF, Office docs (docx, xlsx, pptx), images (jpg, png, gif, bmp, tiff), 
    audio (mp3, wav, m4a), HTML, text formats (txt, md, csv, json, xml), ZIP files, etc.
    """
    ext = (os.path.splitext(path)[1] or '').lower()
    supported_formats = {
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        # Text formats
        '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
        # Images (OCR + metadata)
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
        # Audio (transcription + metadata) 
        '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg',
        # Archives
        '.zip', '.tar', '.gz', '.rar',
        # Code files
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.css', '.scss',
        # Other text
        '.log', '.conf', '.ini', '.cfg', '.yaml', '.yml', '.toml'
    }
    return ext in supported_formats


def _convert_to_markdown(path: str) -> str:
    """
    Universal document reader using MarkItDown with enhanced PDF processing.
    将任意格式文档转换为Markdown文本
    
    支持格式：
    - 文档：PDF、Word、Excel、PowerPoint
    - 图像：JPG、PNG、GIF（通过OCR）
    - 音频：MP3、WAV、M4A（通过转录）
    - 文本：TXT、CSV、JSON、XML、HTML
    - 代码：Python、JavaScript、Java等
    """
    if not os.path.exists(path):
        return ""
    
    # 对PDF文件使用增强处理
    ext = (os.path.splitext(path)[1] or '').lower()
    if ext == '.pdf':
        return _enhanced_pdf_processing(path)
    
    # 其他格式使用原有MarkItDown
    md_instance = _get_markitdown_instance()
    if md_instance is None:
        return _fallback_text_reader(path)
    
    try:
        result = md_instance.convert(path)
        text = getattr(result, "text_content", None)
        if isinstance(text, str) and text.strip():
            return text
        return ""
    except Exception as e:
        logger.warning(f"MarkItDown failed for {path}: {e}")
        return _fallback_text_reader(path)

def _enhanced_pdf_processing(path: str) -> str:
    """
    Enhanced PDF processing with post-processing cleanup.
    """
    logger.info(f"[RAG] Using enhanced PDF processing for: {path}")

    # 使用原有MarkItDown提取
    md_instance = _get_markitdown_instance()
    if md_instance is None:
        return _fallback_text_reader(path)

    try:
        result = md_instance.convert(path)
        raw_text = getattr(result, "text_content", None)
        if not raw_text or not raw_text.strip():
            return ""

        # 后处理：清理和重组文本
        cleaned_text = _post_process_pdf_text(raw_text)
        logger.info(f"[RAG] PDF post-processing completed: {len(raw_text)} -> {len(cleaned_text)} chars")
        return cleaned_text

    except Exception as e:
        logger.warning(f"Enhanced PDF processing failed for {path}: {e}")
        return _fallback_text_reader(path)

def _post_process_pdf_text(text: str) -> str:
    """
    Post-process PDF text to improve quality.
    """
    import re
    
    # 1. 按行分割并清理
    lines = text.splitlines()
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 移除单个字符的行（通常是噪音）
        if len(line) <= 2 and not line.isdigit():
            continue
            
        # 移除明显的页眉页脚噪音
        if re.match(r'^\d+$', line):  # 纯数字行（页码）
            continue
        if line.lower() in ['github', 'project', 'forks', 'stars', 'language']:
            continue
            
        cleaned_lines.append(line)
    
    # 2. 智能合并短行
    merged_lines = []
    i = 0
    
    while i < len(cleaned_lines):
        current_line = cleaned_lines[i]
        
        # 如果当前行很短，尝试与下一行合并
        if len(current_line) < 60 and i + 1 < len(cleaned_lines):
            next_line = cleaned_lines[i + 1]
            
            # 合并条件：都是内容，不是标题
            if (not current_line.endswith('：') and 
                not current_line.endswith(':') and
                not current_line.startswith('#') and
                not next_line.startswith('#') and
                len(next_line) < 120):
                
                merged_line = current_line + " " + next_line
                merged_lines.append(merged_line)
                i += 2  # 跳过下一行
                continue
        
        merged_lines.append(current_line)
        i += 1
    
    # 3. 重新组织段落
    paragraphs = []
    current_paragraph = []
    
    for line in merged_lines:
        # 检查是否是新段落的开始
        if (line.startswith('#') or  # 标题
            line.endswith('：') or   # 中文冒号结尾
            line.endswith(':') or    # 英文冒号结尾
            len(line) > 150 or       # 长句通常是段落开始
            not current_paragraph):  # 第一行
            
            # 保存当前段落
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            
            paragraphs.append(line)
        else:
            current_paragraph.append(line)
    
    # 添加最后一个段落
    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))
    
    return '\n\n'.join(paragraphs)


def _fallback_text_reader(path: str) -> str:
    """
    Simple fallback reader for basic text files when MarkItDown is unavailable.
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        try:
            with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""


def _detect_lang(sample: str) -> str:
    try:
        from langdetect import detect
        return detect(sample[:1000]) if sample else "unknown"
    except Exception:
        return "unknown"


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF or  # CJK统一汉字
        0x3400 <= code <= 0x4DBF or  # CJK扩展A
        0x20000 <= code <= 0x2A6DF or # CJK扩展B
        0x2A700 <= code <= 0x2B73F or # CJK扩展C
        0x2B740 <= code <= 0x2B81F or # CJK扩展D
        0x2B820 <= code <= 0x2CEAF or # CJK扩展E
        0xF900 <= code <= 0xFAFF      # CJK兼容汉字
    )


def _approx_token_len(text: str) -> int:
    # 近似估计：CJK字符按1 token，其他按空白分词
    cjk = sum(1 for ch in text if _is_cjk(ch))
    non_cjk_tokens = len([t for t in text.split() if t])
    return cjk + non_cjk_tokens


def _split_paragraphs_with_headings(text: str) -> List[Dict]:
    """按 markdown 标题切段并保留 heading 路径与**真实**字符偏移。

    与旧实现的差别：旧实现用 `end_pos - len(content)` 反推 start，遇到
    跨多行段落或被 strip 的空白会偏；这里在第一行加入 buf 时记录
    `buf_start`，确保 start/end 与原始 `text` 中的实际位置一致。
    """
    lines = text.splitlines(keepends=True)  # 保留换行符以便按 cumulative 偏移
    heading_stack: List[str] = []
    paragraphs: List[Dict] = []
    buf: List[str] = []
    buf_start: Optional[int] = None
    char_pos = 0

    def flush_buf(end_pos: int):
        nonlocal buf, buf_start
        if not buf or buf_start is None:
            buf, buf_start = [], None
            return
        joined = "".join(buf)  # 含原始换行
        # 内容用 strip 显示，但偏移仍记录原始范围
        content = joined.strip()
        if content:
            paragraphs.append({
                "content": content,
                "heading_path": " > ".join(heading_stack) if heading_stack else None,
                "start": buf_start,
                "end": end_pos,
            })
        buf, buf_start = [], None

    for ln in lines:
        ln_no_nl = ln.rstrip("\n").rstrip("\r")
        if ln_no_nl.strip().startswith("#"):
            flush_buf(char_pos)
            level = len(ln_no_nl) - len(ln_no_nl.lstrip("#"))
            title = ln_no_nl.lstrip("#").strip()
            if level <= 0:
                level = 1
            if level <= len(heading_stack):
                heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
            char_pos += len(ln)
            continue
        if ln_no_nl.strip() == "":
            flush_buf(char_pos)
        else:
            if buf_start is None:
                buf_start = char_pos
            buf.append(ln)
        char_pos += len(ln)

    flush_buf(char_pos)
    if not paragraphs:
        paragraphs = [{"content": text, "heading_path": None, "start": 0, "end": len(text)}]
    return paragraphs


def _split_oversized_paragraph(p: Dict, chunk_tokens: int) -> List[Dict]:
    """把单个超长段落（>chunk_tokens）按字符近似切分成多个小段。

    简单实现：按"目标 token 数 / 字符密度"估算每段字符数上限，沿原始内容滑动切分。
    Token 近似算法见 `_approx_token_len`。
    """
    content = p.get("content", "") or ""
    if not content:
        return [p]
    total_tokens = _approx_token_len(content) or 1
    if total_tokens <= chunk_tokens:
        return [p]
    # 字符 ≈ token 时按比例换算每片字符数；保留最少 50 字符避免无限循环
    chars_per_token = max(1.0, len(content) / float(total_tokens))
    max_chars = max(50, int(chunk_tokens * chars_per_token))

    pieces: List[Dict] = []
    base_start = p.get("start", 0) or 0
    pos = 0
    while pos < len(content):
        sub = content[pos: pos + max_chars]
        if not sub:
            break
        pieces.append({
            "content": sub,
            "heading_path": p.get("heading_path"),
            "start": base_start + pos,
            "end": base_start + pos + len(sub),
        })
        pos += max_chars
    return pieces or [p]


def _chunk_paragraphs(paragraphs: List[Dict], chunk_tokens: int, overlap_tokens: int) -> List[Dict]:
    # 先把任何超长段落预切分，确保单段不会超过 chunk_tokens（防止 embedding 超长 / OOM）
    expanded: List[Dict] = []
    for p in paragraphs:
        expanded.extend(_split_oversized_paragraph(p, chunk_tokens))
    paragraphs = expanded

    chunks: List[Dict] = []
    cur: List[Dict] = []
    cur_tokens = 0
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        p_tokens = _approx_token_len(p["content"]) or 1
        if cur_tokens + p_tokens <= chunk_tokens or not cur:
            cur.append(p)
            cur_tokens += p_tokens
            i += 1
        else:
            # emit current chunk
            content = "\n\n".join(x["content"] for x in cur)
            start = cur[0]["start"]
            end = cur[-1]["end"]
            heading_path = next((x["heading_path"] for x in reversed(cur) if x.get("heading_path")), None)
            chunks.append({
                "content": content,
                "start": start,
                "end": end,
                "heading_path": heading_path,
            })
            # build overlap by keeping tail tokens
            if overlap_tokens > 0 and cur:
                kept: List[Dict] = []
                kept_tokens = 0
                for x in reversed(cur):
                    t = _approx_token_len(x["content"]) or 1
                    if kept_tokens + t > overlap_tokens:
                        break
                    kept.append(x)
                    kept_tokens += t
                cur = list(reversed(kept))
                cur_tokens = kept_tokens
            else:
                cur = []
                cur_tokens = 0
    if cur:
        content = "\n\n".join(x["content"] for x in cur)
        start = cur[0]["start"]
        end = cur[-1]["end"]
        heading_path = next((x["heading_path"] for x in reversed(cur) if x.get("heading_path")), None)
        chunks.append({
            "content": content,
            "start": start,
            "end": end,
            "heading_path": heading_path,
        })
    return chunks


def load_and_chunk_texts(paths: List[str], chunk_size: int = 800, chunk_overlap: int = 100, namespace: Optional[str] = None, source_label: str = "rag") -> List[Dict]:
    """
    Universal document loader and chunker using MarkItDown.
    Converts all supported formats to markdown, then chunks intelligently.
    """
    logger.info(f"[RAG] Universal loader start: files={len(paths)} chunk_size={chunk_size} overlap={chunk_overlap} ns={namespace or 'default'}")
    chunks: List[Dict] = []
    seen_hashes = set()

    for path in paths:
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            continue

        logger.info(f"[RAG] Processing: {path}")
        ext = (os.path.splitext(path)[1] or '').lower()

        # Convert to markdown using MarkItDown
        markdown_text = _convert_to_markdown(path)
        if not markdown_text.strip():
            logger.warning(f"No content extracted from: {path}")
            continue
        
        lang = _detect_lang(markdown_text)
        doc_id = hashlib.md5(f"{path}|{len(markdown_text)}".encode('utf-8')).hexdigest()
        
        # Always use markdown-aware chunking for better structure preservation
        para = _split_paragraphs_with_headings(markdown_text)
        token_chunks = _chunk_paragraphs(para, chunk_tokens=max(1, chunk_size), overlap_tokens=max(0, chunk_overlap))
        
        for ch in token_chunks:
            content = ch["content"]
            start = ch.get("start", 0)
            end = ch.get("end", start + len(content))
            norm = content.strip()
            if not norm:
                continue
                
            content_hash = hashlib.md5(norm.encode('utf-8')).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            
            chunk_id = hashlib.md5(f"{doc_id}|{start}|{end}|{content_hash}".encode('utf-8')).hexdigest()
            chunks.append({
                "id": chunk_id,
                "content": content,
                "metadata": {
                    "source_path": path,
                    "file_ext": ext,
                    "doc_id": doc_id,
                    "lang": lang,
                    "start": start,
                    "end": end,
                    "content_hash": content_hash,
                    "namespace": namespace or "default",
                    "source": source_label,
                    "external": True,
                    "heading_path": ch.get("heading_path"),
                    "format": "markdown",  # Mark all content as markdown-processed
                },
            })
            
    logger.info(f"[RAG] Universal loader done: total_chunks={len(chunks)}")
    return chunks


def build_graph_from_chunks(neo4j, chunks: List[Dict]) -> None:
    """把 chunks 灌进 Neo4j：Document / Memory 节点 + HAS_CHUNK 关系。

    任意一步失败都打 warning（之前是静默 pass），方便排查图谱缺失问题。
    """
    created_docs = set()
    for ch in chunks:
        mem_id = ch["id"]
        meta = ch.get("metadata", {})
        source_path = meta.get("source_path")
        doc_id = meta.get("doc_id")
        if doc_id and doc_id not in created_docs:
            created_docs.add(doc_id)
            try:
                neo4j.add_entity(
                    entity_id=doc_id,
                    name=os.path.basename(source_path or doc_id),
                    entity_type="Document",
                    properties={"source_path": source_path, "lang": meta.get("lang")}
                )
            except Exception as e:
                logger.warning(f"[RAG][graph] add Document entity 失败 doc_id={doc_id}: {e}")
        try:
            neo4j.add_entity(entity_id=mem_id, name=mem_id, entity_type="Memory", properties={
                "source_path": source_path,
                "doc_id": doc_id,
                "start": meta.get("start"),
                "end": meta.get("end"),
            })
        except Exception as e:
            logger.warning(f"[RAG][graph] add Memory entity 失败 mem_id={mem_id}: {e}")
        if doc_id:
            try:
                neo4j.add_relationship(
                    from_entity_id=doc_id,
                    to_entity_id=mem_id,
                    relationship_type="HAS_CHUNK",
                    properties={},
                )
            except Exception as e:
                logger.warning(f"[RAG][graph] add HAS_CHUNK 失败 {doc_id}->{mem_id}: {e}")


def _preprocess_markdown_for_embedding(text: str) -> str:
    """
    Preprocess markdown text for better embedding quality.
    Removes excessive markup while preserving semantic content.
    """
    import re
    
    # Remove markdown headers symbols but keep the text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown links but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown emphasis markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # italic
    text = re.sub(r'`([^`]+)`', r'\1', text)        # inline code
    
    # Remove markdown code blocks but keep content
    text = re.sub(r'```[^\n]*\n([\s\S]*?)```', r'\1', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def _create_default_vector_store(
    dimension: Optional[int] = None,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> QdrantVectorStore:
    """统一创建 RAG 默认 Qdrant 向量库（走 ConnectionManager 避免重复连接）。"""
    if dimension is None:
        dimension = get_dimension(384)

    return QdrantConnectionManager.get_instance(
        url=qdrant_url if qdrant_url is not None else os.getenv("QDRANT_URL"),
        api_key=qdrant_api_key if qdrant_api_key is not None else os.getenv("QDRANT_API_KEY"),
        collection_name=collection_name or _DEFAULT_RAG_COLLECTION,
        vector_size=dimension,
        distance="cosine",
    )


def _normalize_embedder_batch_output(part_vecs) -> List:
    """将 embedder.encode(批量文本) 的返回值统一为 list[list]，避免 ndarray 列表被误判为「单向量」。"""
    if not isinstance(part_vecs, list):
        if hasattr(part_vecs, "tolist"):
            return [part_vecs.tolist()]
        return [list(part_vecs)]
    if not part_vecs:
        return []
    first = part_vecs[0]
    if not isinstance(first, (list, tuple)) and hasattr(first, "__len__"):
        normalized = []
        for v in part_vecs:
            if hasattr(v, "tolist"):
                normalized.append(v.tolist())
            else:
                normalized.append(list(v))
        return normalized
    if not isinstance(first, (list, tuple)):
        if hasattr(part_vecs, "tolist"):
            return [part_vecs.tolist()]
        return [list(part_vecs)]
    return part_vecs


def _encode_one_vector(embedder, text: str, dimension: int) -> List[float]:
    """编码单条文本并严格校验维度，不匹配直接抛错（不再静默截断/零填充）。"""
    raw = embedder.encode(text)
    # encode 单条返回可能是 ndarray 或 list；批量返回是 list
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, list) and raw and isinstance(raw[0], (list, tuple)):
        raw = raw[0]  # 单条但被包成 [vec] 的情况
    vec = [float(x) for x in raw]
    if len(vec) != dimension:
        raise ValueError(f"嵌入维度不匹配: 期望 {dimension}, 实际 {len(vec)}")
    return vec


def index_chunks(
    store=None,
    chunks: List[Dict] = None,
    batch_size: int = 64,
    rag_namespace: str = "default",
) -> None:
    """对 chunks 做嵌入并写入 Qdrant。

    设计要点：
    - 维度不匹配 → 抛错，不再静默截断或零填充（破坏检索语义）；
    - 单批 encoding 失败 → 自动按 8 条小批次重试一次；仍失败则**整批跳过这部分 chunks 并告警**，
      不再写入零向量假装成功。
    """
    if not chunks:
        logger.info("[RAG] No chunks to index")
        return

    embedder = get_text_embedder()
    # 优先使用 embedder 真实维度，避免与 fallback(384) 不一致
    dimension = int(getattr(embedder, "dimension", None) or get_dimension(384))

    if store is None:
        store = _create_default_vector_store(dimension)
        logger.info(f"[RAG] Created default Qdrant store with dimension {dimension}")

    processed_texts: List[str] = [
        _preprocess_markdown_for_embedding(c["content"]) for c in chunks
    ]
    logger.info(f"[RAG] Embedding start: total_texts={len(processed_texts)} batch_size={batch_size}")

    # vecs[i] = chunks[i] 对应的向量；失败位置标 None，最后过滤
    vecs: List[Optional[List[float]]] = [None] * len(processed_texts)

    def _encode_batch(texts: List[str]) -> Optional[List[List[float]]]:
        try:
            raw = _normalize_embedder_batch_output(embedder.encode(texts))
        except Exception as e:
            logger.warning(f"[RAG] batch encode failed n={len(texts)}: {e}")
            return None
        if len(raw) != len(texts):
            logger.warning(
                f"[RAG] embedder 返回条数与请求不一致: {len(raw)} vs {len(texts)}, 整批丢弃"
            )
            return None
        out: List[List[float]] = []
        for v in raw:
            if hasattr(v, "tolist"):
                v = v.tolist()
            vec = [float(x) for x in v]
            if len(vec) != dimension:
                logger.warning(
                    f"[RAG] 向量维度不匹配: 期望 {dimension}, 实际 {len(vec)}, 整批丢弃"
                )
                return None
            out.append(vec)
        return out

    for i in range(0, len(processed_texts), batch_size):
        part = processed_texts[i:i + batch_size]
        result = _encode_batch(part)
        if result is not None:
            for k, v in enumerate(result):
                vecs[i + k] = v
        else:
            # 自动小批量重试一次，避免上游一次性请求超长/限流
            logger.info(f"[RAG] retry batch {i} with smaller sub-batches")
            time.sleep(1)
            sub_size = 8
            for j in range(0, len(part), sub_size):
                small_part = part[j:j + sub_size]
                small_result = _encode_batch(small_part)
                if small_result is not None:
                    for k, v in enumerate(small_result):
                        vecs[i + j + k] = v
                else:
                    logger.warning(
                        f"[RAG] 小批次 {j // sub_size} 仍然失败，跳过 {len(small_part)} 个 chunk"
                    )
        logger.info(f"[RAG] Embedding progress: {min(i + batch_size, len(processed_texts))}/{len(processed_texts)}")

    # 过滤掉失败位置：宁可少索引也不写脏数据
    final_vecs: List[List[float]] = []
    final_metas: List[Dict] = []
    final_ids: List[str] = []
    skipped = 0
    for ch, v in zip(chunks, vecs):
        if v is None:
            skipped += 1
            continue
        meta = {
            "memory_id": ch["id"],
            "user_id": "rag_user",
            "memory_type": "rag_chunk",
            "content": ch["content"],
            "data_source": "rag_pipeline",
            "rag_namespace": rag_namespace,
            "is_rag_data": True,
        }
        meta.update(ch.get("metadata", {}))
        final_vecs.append(v)
        final_metas.append(meta)
        final_ids.append(ch["id"])

    if skipped:
        logger.warning(f"[RAG] {skipped}/{len(chunks)} chunks 因嵌入失败被跳过")

    if not final_vecs:
        logger.error("[RAG] 所有 chunks 嵌入失败，未写入任何向量")
        raise RuntimeError("Failed to embed any chunks")

    logger.info(f"[RAG] Qdrant upsert start: n={len(final_vecs)}")
    success = store.add_vectors(vectors=final_vecs, metadata=final_metas, ids=final_ids)
    if success:
        logger.info(f"[RAG] Qdrant upsert done: {len(final_vecs)} vectors indexed")
    else:
        logger.error("[RAG] Qdrant upsert failed")
        raise RuntimeError("Failed to index vectors to Qdrant")


def embed_query(query: str) -> List[float]:
    """对查询做嵌入；维度不匹配直接抛错，避免用零向量"假成功"污染检索。"""
    embedder = get_text_embedder()
    dimension = int(getattr(embedder, "dimension", None) or get_dimension(384))
    return _encode_one_vector(embedder, query, dimension)


def search_vectors(
    store = None, 
    query: str = "", 
    top_k: int = 8, 
    rag_namespace: Optional[str] = None, 
    only_rag_data: bool = True, 
    score_threshold: Optional[float] = None
) -> List[Dict]:
    """
    Search RAG vectors using unified embedding and Qdrant.
    """
    if not query:
        return []
    
    # Create default store if not provided
    if store is None:
        store = _create_default_vector_store()
    
    # Embed query with unified embedder
    qv = embed_query(query)
    
    # Build filter for RAG data
    where = {"memory_type": "rag_chunk"}
    if only_rag_data:
        where["is_rag_data"] = True
        where["data_source"] = "rag_pipeline"
    if rag_namespace:
        where["rag_namespace"] = rag_namespace
    
    try:
        return store.search_similar(
            query_vector=qv,
            limit=top_k,
            score_threshold=score_threshold,
            where=where,
        )
    except Exception as e:
        logger.warning(f"[RAG] search failed: {e}")
        return []


def _prompt_mqe(query: str, n: int) -> List[str]:
    try:
        from ...core import LingyeLLM
        llm = LingyeLLM()
        prompt = [
            {"role": "system", "content": "你是检索查询扩展助手。生成语义等价或互补的多样化查询。使用中文，简短，避免标点。"},
            {"role": "user", "content": f"原始查询：{query}\n请给出{n}个不同表述的查询，每行一个。"}
        ]
        text = llm.invoke(prompt)
        lines = [ln.strip("- \t") for ln in (text or "").splitlines()]
        outs = [ln for ln in lines if ln]
        return outs[:n] or [query]
    except Exception:
        return [query]


def _prompt_hyde(query: str) -> Optional[str]:
    try:
        from ...core import LingyeLLM
        llm = LingyeLLM()
        prompt = [
            {"role": "system", "content": "根据用户问题，先写一段可能的答案性段落，用于向量检索的查询文档（不要分析过程）。"},
            {"role": "user", "content": f"问题：{query}\n请直接写一段中等长度、客观、包含关键术语的段落。"}
        ]
        return llm.invoke(prompt)
    except Exception:
        return None


def search_vectors_expanded(
    store = None,
    query: str = "",
    top_k: int = 8,
    rag_namespace: Optional[str] = None,
    only_rag_data: bool = True,
    score_threshold: Optional[float] = None,
    enable_mqe: bool = False,
    mqe_expansions: int = 2,
    enable_hyde: bool = False,
    candidate_pool_multiplier: int = 4,
) -> List[Dict]:
    """
    Search with query expansion using unified embedding and Qdrant.
    """
    if not query:
        return []

    # Create default store if not provided
    if store is None:
        store = _create_default_vector_store()

    logger.info(
        "RAG search_expanded: 开始 top_k=%s mqe=%s hyde=%s mqe_n=%s",
        top_k,
        enable_mqe,
        enable_hyde,
        mqe_expansions,
    )

    # expansions
    expansions: List[str] = [query]

    if enable_mqe and mqe_expansions > 0:
        t0 = time.perf_counter()
        logger.info("RAG search_expanded: MQE — 调用 LLM 生成查询扩展…")
        expansions.extend(_prompt_mqe(query, mqe_expansions))
        logger.info(
            "RAG search_expanded: MQE — 完成 %.0fms (当前变体数=%d)",
            (time.perf_counter() - t0) * 1000,
            len(expansions),
        )
    if enable_hyde:
        t0 = time.perf_counter()
        logger.info("RAG search_expanded: HyDE — 调用 LLM 生成假设文档…")
        hyde_text = _prompt_hyde(query)
        if hyde_text:
            expansions.append(hyde_text)
        logger.info(
            "RAG search_expanded: HyDE — 完成 %.0fms (是否追加=%s)",
            (time.perf_counter() - t0) * 1000,
            bool(hyde_text),
        )

    # unique and trim
    uniq: List[str] = []
    for e in expansions:
        if e and e not in uniq:
            uniq.append(e)
    expansions = uniq[: max(1, len(uniq))]

    # distribute pool per expansion
    pool = max(top_k * candidate_pool_multiplier, 20)
    per = max(1, pool // max(1, len(expansions)))

    # Build filter for RAG data
    where = {"memory_type": "rag_chunk"}
    if only_rag_data:
        where["is_rag_data"] = True
        where["data_source"] = "rag_pipeline"
    if rag_namespace:
        where["rag_namespace"] = rag_namespace

    logger.info(
        "RAG search_expanded: 向量检索 %d 路 | 每路召回上限=%d | pool=%d",
        len(expansions),
        per,
        pool,
    )

    # collect hits across expansions
    agg: Dict[str, Dict] = {}
    t_vec_total = time.perf_counter()
    for i, q in enumerate(expansions):
        t_q = time.perf_counter()
        qv = embed_query(q)
        hits = store.search_similar(query_vector=qv, limit=per, score_threshold=score_threshold, where=where)
        logger.info(
            "RAG search_expanded: 变体 %d/%d embed+qdrant %.0fms | 本路命中=%d | 文本长度=%d",
            i + 1,
            len(expansions),
            (time.perf_counter() - t_q) * 1000,
            len(hits),
            len(q),
        )
        for h in hits:
            mid = h.get("metadata", {}).get("memory_id", h.get("id"))
            s = float(h.get("score", 0.0))
            if mid not in agg or s > float(agg[mid].get("score", 0.0)):
                agg[mid] = h
    logger.info(
        "RAG search_expanded: 全部 embed+qdrant %.0fms | 去重后候选=%d → 返回 top_%d",
        (time.perf_counter() - t_vec_total) * 1000,
        len(agg),
        top_k,
    )
    # return top by score
    merged = list(agg.values())
    merged.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return merged[:top_k]


def _try_load_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(model_name)
    except Exception:
        return None


def _item_content(it: Dict) -> str:
    """统一从 hit 取出文本内容：优先 metadata.content，再回退 it.content。

    `search_similar` / `search_vectors` 返回的结果文本一般在 metadata.content 中，
    而 `rank()` 输出会把它平铺到 it.content；这里两种都兼容。
    """
    return (it.get("metadata", {}) or {}).get("content") or it.get("content", "") or ""


def _item_memory_id(it: Dict) -> Optional[str]:
    """统一从 hit 取出 memory_id：优先 metadata.memory_id，再回退 it.memory_id / it.id。"""
    meta = it.get("metadata", {}) or {}
    return meta.get("memory_id") or it.get("memory_id") or it.get("id")


def rerank_with_cross_encoder(query: str, items: List[Dict], model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", top_k: int = 10) -> List[Dict]:
    ce = _try_load_cross_encoder(model_name)
    if ce is None or not items:
        return items[:top_k]
    pairs = [[query, _item_content(it)] for it in items]
    try:
        scores = ce.predict(pairs)
        for it, s in zip(items, scores):
            it["rerank_score"] = float(s)
        items.sort(key=lambda x: x.get("rerank_score", x.get("score", 0.0)), reverse=True)
        return items[:top_k]
    except Exception as e:
        logger.warning(f"[RAG] cross-encoder rerank 失败: {e}")
        return items[:top_k]


def compute_graph_signals_from_pool(vector_hits: List[Dict], same_doc_weight: float = 1.0, proximity_weight: float = 1.0, proximity_window_chars: int = 1600) -> Dict[str, float]:
    """
    Compute graph signals with direct parameters instead of environment variables.
    """

    # group by doc
    by_doc: Dict[str, List[Dict]] = {}
    for h in vector_hits:
        meta = h.get("metadata", {})
        did = meta.get("doc_id")
        if not did:
            # fall back to memory_id grouping if doc missing
            did = meta.get("memory_id") or h.get("id")
        by_doc.setdefault(did, []).append(h)

    # same-doc density score
    doc_counts = {d: len(arr) for d, arr in by_doc.items()}
    max_count = max(doc_counts.values()) if doc_counts else 1

    # proximity score per hit within same doc
    graph_signal: Dict[str, float] = {}
    for did, arr in by_doc.items():
        arr.sort(key=lambda x: x.get("metadata", {}).get("start", 0))
        # precompute density
        density = doc_counts.get(did, 1) / max_count
        # proximity accumulation
        for i, h in enumerate(arr):
            mid = h.get("metadata", {}).get("memory_id", h.get("id"))
            pos_i = h.get("metadata", {}).get("start", 0)
            prox_acc = 0.0
            # look around neighbors within window
            # two-pointer expansion
            # left
            j = i - 1
            while j >= 0:
                pos_j = arr[j].get("metadata", {}).get("start", 0)
                dist = abs(pos_i - pos_j)
                if dist > proximity_window_chars:
                    break
                prox_acc += max(0.0, 1.0 - (dist / max(1.0, float(proximity_window_chars))))
                j -= 1
            # right
            j = i + 1
            while j < len(arr):
                pos_j = arr[j].get("metadata", {}).get("start", 0)
                dist = abs(pos_i - pos_j)
                if dist > proximity_window_chars:
                    break
                prox_acc += max(0.0, 1.0 - (dist / max(1.0, float(proximity_window_chars))))
                j += 1
            # combine
            score = same_doc_weight * density + proximity_weight * prox_acc
            graph_signal[mid] = graph_signal.get(mid, 0.0) + score

    # normalize to [0,1]
    if graph_signal:
        max_v = max(graph_signal.values())
        if max_v > 0:
            for k in list(graph_signal.keys()):
                graph_signal[k] = graph_signal[k] / max_v
    return graph_signal


def rank(vector_hits: List[Dict], graph_signals: Optional[Dict[str, float]] = None, w_vector: float = 0.7, w_graph: float = 0.3) -> List[Dict]:
    """
    Rank results with direct weight parameters instead of environment variables.
    """
    items: List[Dict] = []
    graph_signals = graph_signals or {}
    for h in vector_hits:
        mid = h.get("metadata", {}).get("memory_id", h.get("id"))
        g = float(graph_signals.get(mid, 0.0))
        v = float(h.get("score", 0.0))
        score = w_vector * v + w_graph * g
        items.append({
            "memory_id": mid,
            "score": score,
            "vector_score": v,
            "graph_score": g,
            "content": h.get("metadata", {}).get("content", ""),
            "metadata": h.get("metadata", {}),
        })
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def merge_snippets(ranked_items: List[Dict], max_chars: int = 1200) -> str:
    out: List[str] = []
    total = 0
    for it in ranked_items:
        text = it.get("content", "").strip()
        if not text:
            continue
        if total + len(text) > max_chars:
            remain = max_chars - total
            if remain <= 0:
                break
            out.append(text[:remain])
            total += remain
            break
        out.append(text)
        total += len(text)
    return "\n\n".join(out)


def expand_neighbors_from_pool(selected: List[Dict], pool: List[Dict], neighbors: int = 1, max_additions: int = 5) -> List[Dict]:
    """根据已选 hit 在同 doc 内向左右各扩 neighbors 个 chunk，丰富上下文。

    注意：hit 的 memory_id 可能在 metadata.memory_id 也可能直接在顶层 id，
    统一通过 _item_memory_id 读取，避免之前"取不到 id 永远扩不出来"的 bug。
    """
    if not selected or not pool or neighbors <= 0:
        return selected
    # 按 doc_id 分组并按 start 排序
    by_doc: Dict[str, List[Dict]] = {}
    for it in pool:
        did = (it.get("metadata", {}) or {}).get("doc_id")
        if not did:
            continue
        by_doc.setdefault(did, []).append(it)
    for did, arr in by_doc.items():
        arr.sort(key=lambda x: (x.get("metadata", {}).get("start", 0)))

    selected_ids = {mid for mid in (_item_memory_id(it) for it in selected) if mid}
    additions: List[Dict] = []
    for it in selected:
        did = (it.get("metadata", {}) or {}).get("doc_id")
        cur_mid = _item_memory_id(it)
        if not did or did not in by_doc or not cur_mid:
            continue
        arr = by_doc[did]
        try:
            idx = next(i for i, x in enumerate(arr) if _item_memory_id(x) == cur_mid)
        except StopIteration:
            continue
        for offset in range(1, neighbors + 1):
            for j in (idx - offset, idx + offset):
                if 0 <= j < len(arr):
                    cand = arr[j]
                    mid = _item_memory_id(cand)
                    if mid and mid not in selected_ids:
                        additions.append(cand)
                        selected_ids.add(mid)
                        if len(additions) >= max_additions:
                            break
            if len(additions) >= max_additions:
                break
        if len(additions) >= max_additions:
            break
    extended = list(selected) + additions
    extended.sort(key=lambda x: (x.get("rerank_score", x.get("score", 0.0))), reverse=True)
    return extended


def merge_snippets_grouped(ranked_items: List[Dict], max_chars: int = 1200, include_citations: bool = True) -> str:
    # Group by doc_id and aggregate doc score
    by_doc: Dict[str, List[Dict]] = {}
    doc_score: Dict[str, float] = {}
    for it in ranked_items:
        meta = it.get("metadata", {})
        did = meta.get("doc_id") or meta.get("source_path") or "unknown"
        by_doc.setdefault(did, []).append(it)
        doc_score[did] = doc_score.get(did, 0.0) + float(it.get("score", 0.0))
    # Sort docs by aggregate score
    ordered_docs = sorted(by_doc.keys(), key=lambda d: doc_score.get(d, 0.0), reverse=True)
    # Within doc, order by start offset to preserve context
    for d in ordered_docs:
        by_doc[d].sort(key=lambda x: (x.get("metadata", {}).get("start", 0)))
    out: List[str] = []
    citations: List[Dict] = []
    total = 0
    cite_index = 1
    for did in ordered_docs:
        parts = by_doc[did]
        for it in parts:
            text = (it.get("content", "") or "").strip()
            if not text:
                continue
            # add citation marker if enabled
            suffix = ""
            if include_citations:
                suffix = f" [{cite_index}]"
            need = len(text) + (len(suffix) if suffix else 0)
            if total + need > max_chars:
                remain = max_chars - total
                if remain <= 0:
                    break
                clipped = text[: max(0, remain - len(suffix))]
                if clipped:
                    out.append(clipped + suffix)
                    total += len(clipped) + len(suffix)
                    if include_citations:
                        m = it.get("metadata", {})
                        citations.append({
                            "index": cite_index,
                            "source_path": m.get("source_path"),
                            "doc_id": m.get("doc_id"),
                            "start": m.get("start"),
                            "end": m.get("end"),
                            "heading_path": m.get("heading_path"),
                        })
                        cite_index += 1
                break
            out.append(text + suffix)
            total += need
            if include_citations:
                m = it.get("metadata", {})
                citations.append({
                    "index": cite_index,
                    "source_path": m.get("source_path"),
                    "doc_id": m.get("doc_id"),
                    "start": m.get("start"),
                    "end": m.get("end"),
                    "heading_path": m.get("heading_path"),
                })
                cite_index += 1
        if total >= max_chars:
            break
    merged = "\n\n".join(out)
    if include_citations and citations:
        lines: List[str] = [merged, "", "References:"]
        for c in citations:
            loc = ""
            if c.get("start") is not None and c.get("end") is not None:
                loc = f" ({c['start']}-{c['end']})"
            hp = f" – {c['heading_path']}" if c.get("heading_path") else ""
            sp = c.get("source_path") or c.get("doc_id") or "source"
            lines.append(f"[{c['index']}] {sp}{loc}{hp}")
        return "\n".join(lines)
    return merged


def compress_ranked_items(ranked_items: List[Dict], enable_compression: bool = True, max_per_doc: int = 2, join_gap: int = 200) -> List[Dict]:
    """
    Compress ranked items with direct parameters instead of environment variables.
    """
    if not enable_compression:
        return ranked_items
    by_doc_count: Dict[str, int] = {}
    last_by_doc: Dict[str, Dict] = {}
    new_items: List[Dict] = []
    for it in ranked_items:
        meta = it.get("metadata", {})
        did = meta.get("doc_id") or meta.get("source_path") or "unknown"
        start = int(meta.get("start") or 0)
        end = int(meta.get("end") or (start + len(it.get("content", "") or "")))
        if did not in last_by_doc:
            last_by_doc[did] = it
            by_doc_count[did] = 1
            new_items.append(it)
            continue
        last = last_by_doc[did]
        lmeta = last.get("metadata", {})
        lstart = int(lmeta.get("start") or 0)
        lend = int(lmeta.get("end") or (lstart + len(last.get("content", "") or "")))
        if start - lend <= join_gap and start >= lstart:
            # merge into last
            merged_text = (last.get("content", "") or "").strip()
            add_text = (it.get("content", "") or "").strip()
            if add_text:
                if merged_text:
                    merged_text = merged_text + "\n\n" + add_text
                else:
                    merged_text = add_text
                last["content"] = merged_text
                lmeta["end"] = max(lend, end)
                # keep the higher score
                try:
                    last["score"] = max(float(last.get("score", 0.0)), float(it.get("score", 0.0)))
                except Exception as e:
                    logger.debug(f"compress_ranked_items: 合并 score 失败已忽略: {e}")
            last_by_doc[did] = last
        else:
            cnt = by_doc_count.get(did, 0)
            if cnt >= max_per_doc:
                continue
            new_items.append(it)
            last_by_doc[did] = it
            by_doc_count[did] = cnt + 1
    return new_items


def tldr_summarize(text: str, bullets: int = 3) -> Optional[str]:
    try:
        if not text or len(text.strip()) == 0:
            return None
        from ...core import LingyeLLM
        llm = LingyeLLM()
        prompt = [
            {"role": "system", "content": "请将以下内容概括为简洁的要点列表（最多3-5条），用中文，避免重复，突出关键信息。"},
            {"role": "user", "content": f"请用 {max(1, min(5, int(bullets)))} 条要点总结：\n\n{text}"},
        ]
        out = llm.invoke(prompt)
        return out
    except Exception:
        return None


# ==================
# High-level RAG Pipeline API
# ==================

def create_rag_pipeline(
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    collection_name: Optional[str] = None,
    rag_namespace: str = "default",
) -> Dict[str, Any]:
    """
    Create a complete RAG pipeline with Qdrant and unified embedding.

    默认走 ConnectionManager + 统一默认 collection，避免与 _create_default_vector_store 分叉
    导致同一项目同时存在多个 RAG 集合。
    """
    embedder = get_text_embedder()
    dimension = int(getattr(embedder, "dimension", None) or get_dimension(384))

    store = _create_default_vector_store(
        dimension=dimension,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
    )
    
    def add_documents(
        file_paths: List[str],
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        document_id: Optional[str] = None,
    ):
        """Add documents to RAG pipeline.

        如果传入 document_id，会把生成的所有 chunk 的 metadata.doc_id 强制覆盖为该值，
        方便上层（rag_tool）按 doc_id 做后续查询/删除。
        """
        chunks = load_and_chunk_texts(
            paths=file_paths,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            namespace=rag_namespace,
            source_label="rag",
        )
        if document_id:
            for ch in chunks:
                ch.setdefault("metadata", {})["doc_id"] = document_id
        index_chunks(
            store=store,
            chunks=chunks,
            rag_namespace=rag_namespace,
        )
        return len(chunks)
    
    def search(query: str, top_k: int = 8, score_threshold: Optional[float] = None):
        """Search RAG knowledge base"""
        return search_vectors(
            store=store,
            query=query,
            top_k=top_k,
            rag_namespace=rag_namespace,
            score_threshold=score_threshold
        )
    
    def search_advanced(
        query: str, 
        top_k: int = 8, 
        enable_mqe: bool = False,
        enable_hyde: bool = False,
        score_threshold: Optional[float] = None
    ):
        """Advanced search with query expansion"""
        return search_vectors_expanded(
            store=store,
            query=query,
            top_k=top_k,
            rag_namespace=rag_namespace,
            enable_mqe=enable_mqe,
            enable_hyde=enable_hyde,
            score_threshold=score_threshold
        )
    
    def get_stats():
        """Get pipeline statistics"""
        return store.get_collection_stats()
    
    return {
        "store": store,
        "namespace": rag_namespace,
        "add_documents": add_documents,
        "search": search,
        "search_advanced": search_advanced,
        "get_stats": get_stats
    }