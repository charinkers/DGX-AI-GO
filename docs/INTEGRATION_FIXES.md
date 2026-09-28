# 合并后接口修复

基于 `aedaa10` 修复非物理仿真部分。物理仿真和 Unity 代码保持原样。

## 启动

Python 3.10+，在仓库根目录运行：

```sh
python -m pip install -r requirements.txt
python -m src.cli
python community/server.py --port 8090 --no-browser
```

浏览器访问 `http://localhost:8090/design` 设计机器人，访问 `http://localhost:8090/` 浏览作品。服务默认只监听本机回环地址。

真实模型可通过配置文件或 `KIDCOMM_BASE_URL`、`KIDCOMM_MODEL`、`KIDCOMM_API_KEY` 配置。设置环境变量中的基址会启用模型模式，环境变量优先于配置文件；空 API key 转为本地端点占位值。建议基址统一使用 `http://localhost:11434/v1`。无端点默认 mock。没有验证任何真实模型服务的质量和可用性。

## 修复内容

- 启动、冒烟脚本的技能目录统一相对仓库根目录解析。
- 输入护栏加载失败时停止执行；所有面向孩子的回复都经过输出护栏。
- 否定命令不再转为肯定动作；停止优先于拿取等动作。
- 社区只在明确发布意图和已有设计时发布，不再自动发布演示模板。
- 社区发布校验统一 Schema；Designer 提供完整 `contract`，Web 导出和保存使用同一结构。
- 同一个 Agent 实例保存设计状态。可依次输入“帮我设计一个小型机器人”“蓝色圆形”“胆小”，补全后输出完整契约。“重新设计”重置；“取消设计”或“退出设计”退出追问。进程重启不保留设计对话。
- 解析明确性格，未指定时追问，不再默认替孩子选择开心。性格词里的“小”不再当作体型。
- 作品写入通过跨进程文件锁保护整个读改写过程，临时文件写完后原子替换。损坏的数据库会报错，不会被当作空库覆盖。
- 私有作品仅凭所有者能力令牌可访问或改变公开状态；点赞接口拒绝私有作品且不返回契约。页面输出转义用户文字并限制颜色格式。
- 否定完成状态不再记作打卡。收入按日期保存在原状态文件，余额使用累计收入减累计兑换。

## 本地作品凭证与旧数据

浏览器首次访问生成随机作品管理凭证，存于该浏览器、该站点的 localStorage；服务端只保存其 SHA-256 摘要。`/api/mine`、发布和隐私修改使用 `X-Owner-Token` 请求头。昵称不作为身份依据。两个孩子共用同一浏览器配置时会共用作品凭证；这不是多用户账户系统。

推荐通过同一 `localhost:8090` 地址使用设计页与画廊。切换浏览器、清空站点数据或改用 `127.0.0.1` 会得到不同凭证，原私有作品不会因此自动转移。CLI 使用 `KIDCOMM_OWNER_TOKEN`，未设置时在 `community/data/.owner-token` 创建仅本机用户可读写的凭证；该文件不提交 Git。CLI 与浏览器默认是不同身份。

已有作品未被删除或自动改写。旧作品没有所有者凭证，不能由客户端自行认领；旧公开作品仍可浏览，旧私有数据留在本地文件，需可信本地迁移才能归属新凭证。旧演示数据若不符合 Schema，重新提交时会拒绝；种子脚本的新样例已经对齐 Schema。

积分兼容现有状态文件保留的日期和收入；修复前已被覆盖的历史收入无法从现存文件还原。本次修复不会凭空补记。流程打卡和作业教练仍是两套收入来源，不自动判定跨模块记录是否为同一项作业。

## 验证

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python skills/kidcomm-safety-guardrail/evals/run_redteam.py --guardrail skills/kidcomm-safety-guardrail
python skills/kidcomm-robot-frontend/evals/run_eval.py
python skills/kidcomm-robot-designer/evals/run_eval.py
node tests/web_checks.cjs
```

回归测试包括默认 CLI 启动、模型 URL、三条输出返回路径、护栏异常、连续设计、否定与停止指令、真实本机 HTTP 权限验证、多线程和多进程写入、坏库保护、跨日积分和种子契约。Node 检查两个页面脚本、文本转义、颜色过滤及 Web 导出；不等同于完整浏览器视觉验收。
