"""RAG 檢索：管理 Azure AI Search 索引，把課程教材文字灌進去，
並在學生提問時撈出最相關的教材片段。使用 REST API（不額外裝 SDK）。
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_VERSION = '2024-07-01'
_TIMEOUT = 30


def is_search_enabled():
    return bool(
        getattr(settings, 'AZURE_SEARCH_ENDPOINT', '')
        and getattr(settings, 'AZURE_SEARCH_API_KEY', '')
        and getattr(settings, 'AZURE_SEARCH_INDEX', '')
    )


def _headers():
    return {'api-key': settings.AZURE_SEARCH_API_KEY, 'Content-Type': 'application/json'}


def _endpoint():
    return settings.AZURE_SEARCH_ENDPOINT.rstrip('/')


def _index():
    return settings.AZURE_SEARCH_INDEX


def ensure_index():
    """建立索引（若不存在）。使用繁體中文分析器提升中文檢索品質。"""
    url = f'{_endpoint()}/indexes/{_index()}?api-version={API_VERSION}'
    schema = {
        'name': _index(),
        'fields': [
            {'name': 'id', 'type': 'Edm.String', 'key': True, 'filterable': True},
            {'name': 'content', 'type': 'Edm.String', 'searchable': True,
             'analyzer': 'zh-Hant.microsoft'},
            {'name': 'course_id', 'type': 'Edm.Int32', 'filterable': True},
            {'name': 'material_title', 'type': 'Edm.String', 'retrievable': True, 'searchable': True},
            {'name': 'chapter_title', 'type': 'Edm.String', 'retrievable': True},
        ],
    }
    resp = requests.put(url, headers=_headers(), json=schema, timeout=_TIMEOUT)
    if not resp.ok:
        raise RuntimeError(f'建立索引失敗（{resp.status_code}）：{resp.text[:300]}')
    return True


def _upload_documents(docs):
    url = f'{_endpoint()}/indexes/{_index()}/docs/index?api-version={API_VERSION}'
    payload = {'value': [dict(d, **{'@search.action': 'mergeOrUpload'}) for d in docs]}
    resp = requests.post(url, headers=_headers(), json=payload, timeout=_TIMEOUT)
    if not resp.ok:
        raise RuntimeError(f'上傳文件失敗（{resp.status_code}）：{resp.text[:300]}')
    return len(docs)


def _safe_id(material_id, idx):
    return f'm{material_id}-c{idx}'


def index_course(course, stdout=None):
    """抽取一門課的所有教材文字、切塊、上傳到 Azure AI Search。回傳統計 dict。"""
    from .material_extract import extract_text, chunk_text
    from .models import LessonMaterial

    def log(msg):
        if stdout:
            stdout(msg)

    ensure_index()

    materials = LessonMaterial.objects.filter(
        lesson__chapter__course=course
    ).select_related('lesson__chapter')

    total_materials = 0
    total_chunks = 0
    skipped = 0
    batch = []

    for m in materials:
        text = extract_text(m)
        if not text.strip():
            skipped += 1
            continue
        chunks = chunk_text(text)
        if not chunks:
            skipped += 1
            continue
        total_materials += 1
        chapter_title = m.lesson.chapter.title
        for i, chunk in enumerate(chunks):
            batch.append({
                'id': _safe_id(m.id, i),
                'content': chunk,
                'course_id': course.id,
                'material_title': m.title,
                'chapter_title': chapter_title,
            })
            total_chunks += 1
            if len(batch) >= 100:
                _upload_documents(batch)
                batch = []
        log(f'  已處理教材「{m.title}」→ {len(chunks)} 塊')

    if batch:
        _upload_documents(batch)

    return {
        'materials_indexed': total_materials,
        'chunks': total_chunks,
        'skipped': skipped,
    }


def search(query, course_id, top=4):
    """在指定課程的教材中檢索最相關的片段，回傳 [{content, material_title, chapter_title}]。"""
    if not is_search_enabled():
        return []
    url = f'{_endpoint()}/indexes/{_index()}/docs/search?api-version={API_VERSION}'
    payload = {
        'search': query,
        'filter': f'course_id eq {int(course_id)}',
        'top': top,
        'queryType': 'simple',
        'searchFields': 'content',
        'select': 'content,material_title,chapter_title',
    }
    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning('Azure Search 檢索連線失敗: %s', exc)
        return []
    if not resp.ok:
        logger.warning('Azure Search 檢索失敗 %s: %s', resp.status_code, resp.text[:200])
        return []
    results = resp.json().get('value', [])
    return [
        {
            'content': r.get('content', ''),
            'material_title': r.get('material_title', ''),
            'chapter_title': r.get('chapter_title', ''),
        }
        for r in results
    ]
