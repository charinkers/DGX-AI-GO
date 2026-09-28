"""Community commands require explicit intent, an actual design and ownership."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys

COMMUNITY = Path(__file__).resolve().parents[3] / 'community'
sys.path.insert(0, str(COMMUNITY))
import store

def local_token():
    token = os.environ.get('KIDCOMM_OWNER_TOKEN')
    if token:
        store.owner_id(token)
        return token
    path = store.DATA_FILE.parent / '.owner-token'
    path.parent.mkdir(parents=True, exist_ok=True)
    from filelock import FileLock
    with FileLock(str(path)+'.lock'):
        if not path.exists():
            with os.fdopen(os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600), 'w') as f:
                f.write(secrets.token_hex(32))
        return path.read_text().strip()

def find_work(key, works):
    matches=[w for w in works if key.strip().lower() in (w['id'].lower(), w['title'].lower(),w['ip_id'].lower())]
    return matches[0] if len(matches)==1 else None

def handle(query, contract=None, owner_token=None):
    q=query.strip()
    if re.search(r'不要|别|不想|取消|不能|不许|不发布|不分享|不公开',q):
        return {'action':'cancel','note':'没有发布或修改任何作品。'}
    m=re.fullmatch(r'给(.+?)(?:点个赞|点赞)',q)
    if m:
        w=find_work(m.group(1),store.list_public())
        return {'action':'like','result':store.like(w['id'],store.owner_id(owner_token) if owner_token else 'guest') if w else None}
    m=re.fullmatch(r'把(.+?)(?:设为|设置为)(私有|公开)',q)
    if m:
        token=owner_token or local_token()
        w=find_work(m.group(1),store.list_owned(token))
        if w:
            return {'action':'set_privacy','work':store.set_privacy(w['id'],m.group(2)=='公开',token)}
        return {'action':'ask','note':'请指定你拥有的作品名或 ID。'}
    publish = re.fullmatch(r'(?:我想|请|帮我)?(?:发布|分享)(?:我的作品|这个作品|当前设计|我的机器人)(?:到社区)?[。！!]?|(?:我想)?把(.+?)发到社区[。！!]?',q)
    if publish:
        if not contract:
            return {'action':'ask','note':'请先完成机器人设计，再发布当前作品。'}
        token=owner_token or local_token()
        w=store.publish(contract, publish.group(1) or '我的机器人伙伴', '我', public=True,owner_token=token)
        return {'action':'publish','work':w}
    if any(w in q for w in ('看看','社区','画廊','有什么')):
        return {'action':'list_public','works':store.list_public()}
    return {'action':'ask','note':'请明确选择：浏览社区、发布我的作品，或把作品设为私有。'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--query',default='')
    ap.add_argument('--design',default='null')
    args=ap.parse_args()
    print(json.dumps(handle(args.query,json.loads(args.design)),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
