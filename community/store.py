"""Local JSON storage with cross-process transactions and owner capabilities.

Old works remain readable when public; ownerless legacy works cannot be claimed
through the API. Restore ownership only through a trusted local migration.
"""
import functools
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import time
import uuid
import sys
from filelock import FileLock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.contracts import validate_contract

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / 'data'
DATA_FILE = DATA_DIR / 'works.json'

def _load():
    if not DATA_FILE.exists():
        return []
    # Never treat corrupt data as an empty database.
    works = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if not isinstance(works, list):
        raise ValueError('Invalid works database')
    return works

def _save(works):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=DATA_FILE.parent, prefix='.works-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(works, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, DATA_FILE)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def transaction(fn):
    @functools.wraps(fn)
    def locked(*args, **kwargs):
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(DATA_FILE) + '.lock', timeout=10):
            return fn(*args, **kwargs)
    return locked

def owner_id(token):
    if not isinstance(token, str) or len(token) < 32:
        raise PermissionError('缺少有效的作品管理凭证')
    return hashlib.sha256(token.encode()).hexdigest()

def owns(work, token):
    return bool(work.get('owner_id')) and hmac.compare_digest(work['owner_id'], owner_id(token))

def public_view(work):
    return {k:v for k,v in work.items() if k not in ('owner_id', 'liked_by')}

@transaction
def publish(contract, title, author, public=False, tags=None, liker_hint='demo', owner_token=None):
    validate_contract(contract)
    if not isinstance(title, str) or not isinstance(author, str):
        raise ValueError('标题和昵称必须是文字')
    if not isinstance(public, bool):
        raise ValueError('public must be boolean')
    works = _load()
    work = {'id':uuid.uuid4().hex, 'ip_id':contract['ip_id'],
            'title':title or contract['ip_id'], 'author':author or '小创作者',
            'contract':contract, 'color':contract['appearance']['body_color'],
            'tags':tags or [], 'public':public, 'likes':0, 'liked_by':[],
            'created_at':time.strftime('%Y-%m-%dT%H:%M:%S')}
    if owner_token is not None:
        work['owner_id'] = owner_id(owner_token)
    works.append(work)
    _save(works)
    return public_view(work)

def list_public():
    return [public_view(w) for w in sorted(_load(), key=lambda w:w.get('likes',0), reverse=True) if w.get('public')]

def list_owned(token):
    owner_id(token)
    return [public_view(w) for w in _load() if owns(w,token)]

def list_by_author(author):
    # A nickname is not proof of ownership.
    return [w for w in list_public() if w.get('author') == author]

def get(work_id, owner_token=None):
    for w in _load():
        if w['id'] == work_id and (w.get('public') or (owner_token and owns(w,owner_token))):
            return public_view(w)
    return None

@transaction
def like(work_id, liker='demo'):
    works = _load()
    for w in works:
        if w['id'] == work_id and w.get('public'):
            liked=w.setdefault('liked_by',[])
            if liker not in liked:
                liked.append(liker)
            w['likes']=len(liked)
            _save(works)
            return {'id':w['id'], 'likes':w['likes']}
    return None

@transaction
def set_privacy(work_id, public, owner_token=None):
    owner_id(owner_token)
    if not isinstance(public, bool):
        raise ValueError('public must be boolean')
    works=_load()
    for w in works:
        if w['id'] == work_id:
            if not owns(w,owner_token):
                raise PermissionError('不能修改其他人的作品')
            w['public']=public
            _save(works)
            return public_view(w)
    return None

@transaction
def remove(work_id, owner_token=None):
    owner_id(owner_token)
    works=_load()
    for w in works:
        if w['id'] == work_id:
            if not owns(w,owner_token):
                raise PermissionError('不能删除其他人的作品')
            works.remove(w);_save(works);return True
    return False

def stats():
    works=_load()
    return {'total':len(works), 'public':sum(bool(w.get('public')) for w in works),
            'private':sum(not w.get('public') for w in works),
            'total_likes':sum(w.get('likes',0) for w in works)}
