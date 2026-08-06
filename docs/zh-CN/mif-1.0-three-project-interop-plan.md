# MIF 1.0 三项目互操作协同计划

状态：信息性工程计划，不是 MIF wire specification，也不创建新的 MIF
conformance target。

参与项目：

- MIF：规范、机器制品、公共语料、测试协议、比较器和发布治理；
- Sanmill：产品侧独立 MIF 1.0 适配器；
- NMM_LLM：训练与搜索侧独立 MIF 1.0 适配器。

## 1. 共同目标

三个项目以同一个冻结的 MIF 1.0 Candidate Wire Contract 为输入，分别产生
可比较的规范化 bytes、逐事件状态和 replay 结果。Sanmill 与 NMM_LLM 的玩法
实现必须彼此独立，也不得导入或复制 MIF Python reference runner 的状态机
代码。

三方一致后，MIF 项目才可以完成 release governance 并发布实际
`mif-suite-1.0.json`。在此之前，任何通过结果都只是 Candidate evidence，
不得声称 MIF Suite 1.0 conformance。

## 2. 启动基线

协作启动通知必须给出一个不可变的 MIF Git commit。适配器在 capability 和
测试报告中记录该 commit，以及以下 raw-file identities：

```text
mif-1.0.md
sha256:330e65145ceb26fe582e58b89405d87bd73e8be200b476aef82c0ee27731d995

docs/zh-CN/mif-1.0.md
sha256:9cc06abb57425e2bc2e26432b6da53abe503e9b5415ea0b4f854f19f68722cc1

artifacts/mif-1.0/index.json
sha256:3849a70897829d6d994c790b64e63484469483a940887fe828a1a0d421d78e90

artifacts/mif-1.0/corpus/executable/reference-cases.json
sha256:a48c50352caebce30deb1de11f8f73dbc4540ee538651c3a139d9bcb166ba983

interop/adapter-protocol-v1.md
sha256:a59e5e5af3e948f6c7cac6a39a490c6eae6338151741b6c7fcdde5c88d991e2d

interop/cases/smoke-v1.json
sha256:a6d292f4d19381172fbc19f89d3ee42145a6d5533d6d81fd719394e25342bb53
```

0.4 是冻结的历史迁移输入。Sanmill 与 NMM_LLM 不需要先实现 0.4，也不以
0.4 conformance 作为 1.0 实施前提。

## 3. 独立性规则

允许共享：

- MIF 规范、Schema、ABNF、registries 和 corpus；
- RFC 8785、SHA-256、JSON Schema 等通用库；
- 测试请求、测试结果和最小复现数据。

禁止共享：

- primary/removal 合法性和状态转移实现；
- stable-boundary、claim、repetition 或 outcome 计算代码；
- decision/resumption projection 和 transform 算法实现；
- 通过调用 MIF reference runner 代替本地实现。

若 NMM_LLM 与 reference runner 使用相同语言，仍须保持独立模块、独立测试和
独立算法实现。reference runner 是第三份证据，不是规范性 oracle。

## 4. 项目职责

### 4.1 MIF

MIF 项目负责：

1. 冻结并发布启动 commit、artifact index 和 corpus digest；
2. 维护非规范性的 Adapter CLI/NDJSON 测试协议；
3. 提供 request/response Schema、smoke cases 和三方比较器；
4. 维护公共 deterministic corpus、migration rejection 和 fuzz seeds；
5. 将差异分类为实现错误、corpus 错误或规范歧义；
6. 在全部发布门槛满足后生成 suite manifest 和签名发布制品。

MIF 在互操作阶段不主动改动冻结的 wire semantics。若确认存在规范缺陷，必须
显式发布新的 Candidate revision、更新全部关联 hash，并要求所有适配器重新
锁定基线。

### 4.2 Sanmill

Sanmill 负责独立实现：

- MFEN、MPK、MIFPOS、MRS 和 MSTATE 的读取、规范输出及 envelope 校验；
- `mif-finite-rules-v3`、stable-boundary 顺序及完整 MSTATE replay；
- claim/offer lifecycle、repetition summary 和 no-progress；
- decision/resumption identities；
- full-state transforms、invariance gate 和 logical-turn projection；
- Adapter CLI 协议和准确的 `MIFCAP/1.0` 声明。

适配器必须能够报告 origin stabilization 后及每个 event 后的状态快照。

### 4.3 NMM_LLM

NMM_LLM 负责相同范围的独立规则实现，并额外负责：

- NMM_LLM 原子动作与 MIF primary/remove event 的双向映射；
- 使用 `decisionDigest` 作为规则充分的训练、PUCT 和缓存身份；
- 使用 `resumptionDigest` 作为精确恢复和审计身份；
- 使用独立 `experimentDigest` 绑定训练环境限制；
- portable MSTATE 训练快照和 full-history transform 数据增强；
- 明确禁止把 MPK 或 primary-ply 当成完整决策身份。

NMM_LLM 同样实现 Adapter CLI，并输出准确的 `MIFCAP/1.0`。

## 5. 里程碑与退出条件

| 里程碑 | 工作 | 退出条件 |
|---|---|---|
| M0 Baseline | MIF 提交并推送当前合同、制品和 runner | 公布完整 commit、四个正式与两个 harness hash |
| M1 Harness | MIF 发布 Adapter CLI、Schema、smoke cases 和比较器 | 两个 reference adapter 进程 loopback 零差异 |
| M2 Adapters | Sanmill、NMM_LLM 各自实现 | 均能完成 handshake、输出 MIFCAP 并执行首批 replay |
| M3 Deterministic | 三方运行完整 deterministic corpus | 所有要求的 byte/state/replay 比较为零差异 |
| M4 Differential | 固定 seed 的随机合法对局和负向变异 | 无未解释差异，失败均可复现 |
| M5 Release | 治理、许可、媒体类型、签名和 suite 绑定 | 发布签名 `mif-suite-1.0.json` 和 Git tag |

Sanmill 与 NMM_LLM 可以在 M1 完成后并行开发，不需要等待对方。两边不得通过
交换状态机代码来修复差异。

### 5.1 当前进度（candidate-2）

- M0 与 M1 的 candidate-2 基线、runner、Schema、比较器和 loopback 已完成；
- M2 的首批退出条件已满足：Sanmill 与 NMM_LLM 均有独立 adapter、
  `MIFCAP/1.0`、replay、identity 与 transform 实现；
- candidate-2 统一修复了 reference/harness 的 RFC 8785 JCS，wire contract
  及其中英文 raw-file hashes 未改变；
- 17-case smoke 已在 MIF reference、Sanmill 与 NMM_LLM 三个进程间零差异；
- M3 尚未完成：下一阶段仍须扩展并执行完整 deterministic corpus，而不是把
  当前 smoke 结果表述为 Suite conformance。

## 6. 比较要求

### 6.1 Byte-level

比较规范化 MFEN/MPK、JCS bytes、所有规范 digest、transformed objects 和
MIFTURN。JSON 的空白和成员输入顺序不参与比较，规范 JCS bytes 参与比较。

### 6.2 State-level

在 origin stabilization 后和每个成功 event 后比较：

- board、side、phase、action、hands 和 outcome；
- obligations 及其顺序、target masks 和 after；
- `lm`、`pc`、`ul` 及其他已注册 semantic state；
- no-progress、repetition root、open offer、claim audit 和 claim rights；
- 当前合法 primary/supplementary action 集合。

### 6.3 Replay-level

比较 accept/reject、首次失败 `eventSeq`、diagnostic category/code、current
checkpoint、完整 active repetition window、claims、decision/resumption object
及其 digest。

对错误响应，非规范 `message` 和 `annotations` 不作为一致性字段；其余规范字段
必须一致。

## 7. 差异处理

每个差异报告至少包含：

```text
MIF commit
artifact index digest
caseId and operation
adapter name/version
first divergent eventSeq or JSON Pointer
canonical expected/actual
diagnostic category/code
minimal input and deterministic seed
```

处理规则：

1. 实现错误只修改对应适配器；
2. corpus 错误在 MIF 修复并刷新 index/corpus digest；
3. 规范歧义由三方共同评审，适配器不得自行猜测；
4. 任何有损或无法证明的转换继续 fail closed；
5. 不允许为了得到一致结果而静默重写输入或降级 profile。

## 8. Suite 发布门槛

发布 MIF Suite 1.0 前必须同时满足：

- Sanmill 与 NMM_LLM 两个独立实现通过必需 conformance classes；
- 三方 deterministic 比较零差异；
- 固定 seed differential/fuzz 测试无未解决结果；
- capability 与测试报告绑定确切 corpus digest；
- LICENSE、registry governance、媒体类型、扩展名和签名策略完成；
- 实际 suite manifest 固定全部规范、Schema、registry、corpus 和报告 hash。

## 9. 开工通知条件

MIF 项目在以下条件同时满足时发出正式开工通知：

1. M0 commit 已推送；
2. Adapter CLI 协议和 Schema 已进入该 commit；
3. reference loopback 比较通过；
4. 启动通知给出 commit、hash、命令和首批 case 清单。

正式通知之后，MIF 可继续扩展公共 comparison cases；Sanmill 与 NMM_LLM 应立即
并行实现，不需要等待完整 fuzz 基础设施。
