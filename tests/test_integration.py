import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from threading import Thread
from types import SimpleNamespace

import pytest
import requests
from src.contracts import validate_contract
from src.cli import _load_cfg, DEFAULT_SKILLS_DIR
from src.harness import Agent
from src.llm import LLMConfig

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name, ROOT/path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
    return m
store=module('store','community/store.py')
server=module('community_server','community/server.py')
frontend=module('frontend','skills/kidcomm-robot-frontend/scripts/agent.py')
community=module('community_skill','skills/kidcomm-community/scripts/main.py')
flow=module('flow','skills/evening-flow/scripts/main.py')
hw=module('hw','skills/homework-coach/scripts/main.py')
review=module('review','skills/evening-review/scripts/main.py')
TOKEN='a'*64
OTHER='b'*64

@pytest.fixture
def contract():
    return json.loads((ROOT/'skills/sim-physics/designs/flying-cat.json').read_text())

@pytest.fixture
def db(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA_FILE',tmp_path/'works.json')
    return store

@pytest.fixture
def http(db):
    srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=Thread(target=srv.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{srv.server_port}'
    srv.shutdown();thread.join();srv.server_close()

def headers(token=TOKEN): return {'X-Owner-Token':token}

def test_default_startup():
    assert Path(DEFAULT_SKILLS_DIR).resolve()==ROOT/'skills'
    r=subprocess.run([sys.executable,'-m','src.cli'],input='exit\n',text=True,capture_output=True,cwd=ROOT)
    assert r.returncode==0,r.stderr
    assert '已加载' in r.stdout

def test_environment_config(monkeypatch):
    monkeypatch.setenv('KIDCOMM_BASE_URL','http://localhost:11434/v1')
    monkeypatch.setenv('KIDCOMM_MODEL','test')
    assert _load_cfg(None).mode=='openai'
    assert _load_cfg(None).model=='test'

@pytest.mark.parametrize('base',['http://localhost:11434','http://localhost:11434/v1','http://localhost:11434/v1/'])
def test_model_url(base,monkeypatch):
    monkeypatch.setenv('KIDCOMM_BASE_URL',base)
    urls=[]
    def post(url,**kw):
        urls.append(url)
        return SimpleNamespace(json=lambda:{'choices':[{'message':{'content':'{"action":"stop","target":{},"missing":[]}'}}]})
    monkeypatch.setattr(requests,'post',post)
    frontend.ground('红色积木',use_model=True)
    assert urls==['http://localhost:11434/v1/chat/completions']

@pytest.mark.parametrize('text,expected',[('停止拿红色积木','stop'),('停下','stop'),('不要动','stop'),('不要拿红色积木',None),('不要去那个地方',None),('不要停',None)])
def test_negated_actions(text,expected):
    out=frontend.ground(text,{'action':'pick_up','target':{'type':'block'}})
    assert out['slots'].get('action')==expected
    if expected is None: assert out['next_action']=='ask'

@pytest.mark.parametrize('branch',['generic','script','skill_model'])
def test_output_guardrail(branch,monkeypatch):
    a=Agent(str(ROOT/'skills'),LLMConfig())
    danger='请把手指插进插座'
    if branch=='generic': skill=None
    else:
        name='kidcomm-robot-designer' if branch=='script' else 'hide-seek'
        skill=next(s for s in a.skills if s.name==name) if branch=='script' else next(s for s in a.skills if not (Path(s.path).parent/'scripts/main.py').exists())
    monkeypatch.setattr('src.harness.dispatch_by_keywords',lambda *args:SimpleNamespace(skill=skill,reason='test'))
    monkeypatch.setattr(a.llm,'complete',lambda *args,**kw:danger)
    monkeypatch.setattr(a,'_run_script',lambda *args:danger)
    assert danger not in a.chat('你好')

@pytest.mark.parametrize('failure',['missing','broken'])
def test_fail_closed(failure,monkeypatch):
    a=Agent(str(ROOT/'skills'),LLMConfig())
    if failure=='missing': a.skills_dir='/does/not/exist'
    else: monkeypatch.setattr('src.harness.importlib.util.spec_from_file_location',lambda *a: (_ for _ in ()).throw(RuntimeError('broken')))
    monkeypatch.setattr(a.llm,'complete',lambda *a,**kw: pytest.fail('model must not run'))
    assert '暂时不可用' in a.chat('我家住在测试路1号')

def test_multi_turn_design(monkeypatch):
    a=Agent(str(ROOT/'skills'),LLMConfig())
    skill=next(s for s in a.skills if s.name=='kidcomm-robot-designer')
    monkeypatch.setattr('src.harness.dispatch_by_keywords',lambda *args:SimpleNamespace(skill=skill,reason='test'))
    a.chat('小型机器人')
    assert a.pending_design
    a.chat('蓝色圆形')
    assert a.pending_design
    out=a.chat('胆小')
    assert not a.pending_design,out
    assert a.latest_contract['appearance']['size']=='small'
    assert a.latest_contract['personality']['type']=='timid'
    validate_contract(a.latest_contract)

def test_personality_without_size_is_not_small():
    m=module('designer_logic','skills/kidcomm-robot-designer/scripts/design.py')
    assert 'size' in m.guide('蓝色圆形，胆小')['missing']

@pytest.mark.parametrize('query',['不要发布我的作品','随便说说','取消发布','能不能发布我的作品？'])
def test_no_implicit_publication(db,contract,query):
    assert community.handle(query,contract,TOKEN)['action']!='publish'
    assert db._load()==[]

def test_explicit_publish_requires_design(db,contract):
    assert community.handle('发布我的作品',None,TOKEN)['action']=='ask'
    out=community.handle('发布我的作品',contract,TOKEN)
    assert out['work']['contract']==contract
    assert len(db.list_owned(TOKEN))==1

def test_http_ownership(http,contract):
    r=requests.post(http+'/api/works',json={'contract':contract,'public':False},headers=headers())
    assert r.status_code==201,r.text
    wid=r.json()['id']
    assert 'owner_id' not in r.json()
    assert requests.get(http+'/api/works').json()==[]
    assert requests.get(http+'/api/mine',headers=headers(OTHER)).json()==[]
    assert requests.get(http+'/api/mine',headers=headers()).json()[0]['id']==wid
    assert requests.post(http+f'/api/works/{wid}/like',json={}).status_code==404
    for h in ({},headers(OTHER)):
        assert requests.post(http+f'/api/works/{wid}/privacy',json={'public':True},headers=h).status_code==403
    assert requests.post(http+f'/api/works/{wid}/privacy',json={'public':True},headers=headers()).status_code==200
    assert len(requests.get(http+'/api/works').json())==1
    assert set(requests.post(http+f'/api/works/{wid}/like',json={}).json())=={'id','likes'}

@pytest.mark.parametrize('data',[{}, {'contract':{}}, {'contract':[], 'public':True}])
def test_invalid_contract_rejected(http,data):
    assert requests.post(http+'/api/works',json=data,headers=headers()).status_code==400

def test_invalid_boolean(http,contract):
    assert requests.post(http+'/api/works',json={'contract':contract,'public':'false'},headers=headers()).status_code==400

def test_threaded_publications(db,contract):
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i:db.publish(contract,str(i),'child',owner_token=TOKEN),range(40)))
    assert len(db._load())==40

def process_publish(path,contract,i):
    store.DATA_FILE=Path(path)
    store.publish(contract,str(i),'child',owner_token=TOKEN)

def test_process_publications(db,contract):
    with ProcessPoolExecutor(3) as pool:
        futures=[pool.submit(process_publish,str(db.DATA_FILE),contract,i) for i in range(12)]
        for f in futures:f.result()
    assert len(db._load())==12

def test_corrupt_store_not_overwritten(db,contract):
    db.DATA_FILE.write_text('broken')
    with pytest.raises(ValueError):db.publish(contract,'x','child')
    assert db.DATA_FILE.read_text()=='broken'

@pytest.mark.parametrize('text',['还没写完作业','作业未完成','我正在写作业'])
def test_no_false_completion(text):
    assert flow.parse_query(text)[0]!='done'
    assert hw.parse_query(text)[0]!='done-item'

def test_cross_day_balance(tmp_path,monkeypatch):
    day=review.date.today().isoformat()
    p=tmp_path/'flow.json'
    p.write_text(json.dumps({'date':day,'points':50,'earnings_by_date':{'2000-01-01':100,day:50}}))
    monkeypatch.setattr(review,'FLOW_STATE',p)
    monkeypatch.setattr(review,'HOMEWORK_STATE',tmp_path/'missing')
    assert review.cmd_points({'redeemed_total':60})['remaining']==90

def test_day_rollover_preserves_income(tmp_path,monkeypatch):
    p=tmp_path/'state.json';p.write_text(json.dumps({'date':'2000-01-01','points':100,'done':{}}))
    monkeypatch.setattr(flow,'STATE_PATH',p)
    state=flow.load_state();state['points']=50;flow.save_state(state)
    assert sum(json.loads(p.read_text())['earnings_by_date'].values())==150

def test_seed_contracts():
    seed=module('seed_check','community/seed.py')
    for row in seed.SAMPLES:validate_contract(row['contract'])

def test_frontend_entrypoint_calls_configured_model(monkeypatch):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    paths=[]
    class Model(BaseHTTPRequestHandler):
        def do_POST(self):
            paths.append(self.path)
            self.rfile.read(int(self.headers['Content-Length']))
            body=json.dumps({'choices':[{'message':{'content':json.dumps({'action':'play','target':{'type':'toy'},'missing':[]})}}]}).encode()
            self.send_response(200);self.end_headers();self.wfile.write(body)
        def log_message(self,*args): pass
    srv=HTTPServer(('127.0.0.1',0),Model)
    thread=Thread(target=srv.serve_forever,daemon=True);thread.start()
    try:
        env={**os.environ,'KIDCOMM_BASE_URL':f'http://127.0.0.1:{srv.server_port}/v1','KIDCOMM_MODEL':'fake'}
        result=subprocess.run([sys.executable,str(ROOT/'skills/kidcomm-robot-frontend/scripts/main.py'),'--query','启动一个新活动'],env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)['slots']['action']=='play'
        assert paths==['/v1/chat/completions']
    finally:
        srv.shutdown();thread.join();srv.server_close()

def test_harness_passes_model_configuration(monkeypatch):
    a=Agent(str(ROOT/'skills'),LLMConfig())
    a.llm_cfg=LLMConfig(mode='openai',base_url='http://localhost:11434/v1',model='test',api_key='EMPTY')
    captured={}
    def run(args,**kwargs):
        captured.update(kwargs['env'])
        return SimpleNamespace(stdout='{}',stderr='',returncode=0)
    monkeypatch.setattr('src.harness.subprocess.run',run)
    a._run_script('skills/kidcomm-robot-frontend/scripts/main.py','hello')
    assert captured['KIDCOMM_BASE_URL']=='http://localhost:11434/v1'
    assert captured['KIDCOMM_MODEL']=='test'

def test_http_pages_available(http):
    assert 'AI造物' in requests.get(http+'/design').text
    assert 'X-Owner-Token' in requests.get(http+'/').text

def test_legacy_private_cannot_be_claimed(db,contract):
    w=db.publish(contract,'legacy','old',public=False)
    with pytest.raises(PermissionError):db.set_privacy(w['id'],True,TOKEN)
    assert db.get(w['id'],TOKEN) is None
    assert db._load()[0]['public'] is False
