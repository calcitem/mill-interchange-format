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
sha256:5acbb714bed77e24eaac72fa5f24d2e54d1e17aaf568a8b60718c840281a6541

artifacts/mif-1.0/corpus/executable/reference-cases.json
sha256:350b7ff02772e820a57431e11c4e2f15a874d0779fb6e7afb01e9b16f6992741

interop/adapter-protocol-v1.md
sha256:253c1d201ea1db625e0c534da445ca4ecaa0b07597dfc7dbf59fbd6adf89874f

interop/cases/smoke-v1.json
sha256:a6d292f4d19381172fbc19f89d3ee42145a6d5533d6d81fd719394e25342bb53

interop/cases/deterministic-v1.json
sha256:d11317a090300f8a47f77afed647bdbd236dcdb1996c0147a81c874fa39dfd82
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

### 5.1 当前进度（candidate-4 M3 基线）

- M0 与 M1 的合同、runner、Schema、比较器和 17-case smoke 已完成；
- candidate-2 统一修复了 reference/harness 的 RFC 8785 JCS，wire contract
  及其中英文 raw-file hashes 未改变；
- candidate-3 增加 MPK canonicalization、`legal-actions-v1` 和 55-case
  deterministic corpus；Sanmill 与 NMM_LLM 完成对应实现后，本地三方诊断运行
  达到 55/55；
- 随后复核发现 MIF reference 的 `stabilize_origin()` 未在 stable-boundary
  处理前按当前行动者 reserve 同步 phase/action。该缺陷在非对称 reserve
  origin 上使 reference 错误接受未稳定 `p/p`，但不改变冻结的 wire contract；
- candidate-4 修复该 reference/harness 缺陷，在 executable corpus 增加 origin
  `p/p` → `m/m` 状态回归，并把 deterministic corpus 扩展为 58 项；
- 58-case 双 reference loopback、三 adapter 比较及独立复跑均为零差异；
- Sanmill 在 `e6d639d41f079b15ca697268d0c2c21dad5c2bc3` 持久化原始报告，
  并在 `fe780b7d40ce1c101b2f635e45bee780dfd30606` 发布 companion manifest；
- companion manifest 绑定 MIF `7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978`、
  Sanmill `e6d639d41f079b15ca697268d0c2c21dad5c2bc3`、NMM_LLM
  `11bebd14e0d538a41a4b43aebfe57ee74c2a2601`、七个输入 hash、报告 hash
  及 case/config digest；
- MIF 的 `interop/evidence/mif-1.0-candidate-4-m3.json` 固定上述证据和独立
  字节级复跑结果。

M3 已完成：candidate-4 的 byte/state/replay deterministic 比较为 58/58，且
证据链绑定三个已发布的被测提交。该结论仍只是 Candidate interoperability
evidence，不是 MIF Suite 1.0 conformance。

### 5.2 Candidate-4 边界与闭合结果

新增边界使用 `placing.movementAllowed=true`、White reserve 为 0、Black reserve
为 1 的 ongoing origin。根据 11.4，当前 White 必须处于 phase/action `m/m`：

1. `execute-origin-phase-sync-asymmetric-reserve` 从输入 `p/p` 稳定化为 `m/m`；
2. `project-legal-actions-asymmetric-reserve-unstabilized` 对同一未稳定 `p/p`
   返回 `inconsistent/unstabilized-boundary`；
3. `project-legal-actions-asymmetric-reserve-moving` 对稳定 `m/m` 返回 57 个
   规范排序的飞行动作。

两个外部项目已经更新 candidate-4 pin、重跑聚焦测试和 58-case 比较、发布各自
提交并完成 commit-bound evidence。复核未发现 Sanmill 或 NMM_LLM 玩法实现需要
因本次修复而改变。

### 5.3 M4 Differential 启动

M4 不改变 candidate-4 wire 或 M3 corpus。MIF 项目先发布独立的 differential
launch package，至少固定：

1. 版本化 PRNG、seed 列表、每个 seed 的最大 logical turns 与资源上限；
2. 覆盖 placing、moving、flying、removal、claim/repetition 和终局的 ruleset
   场景矩阵；
3. 通过 `project-legal-actions` 取得三方一致动作集、确定性选择动作并用
   `execute`/`replay` 比较每个 stable boundary 的 driver；
4. 非法 event、非规范文本、digest/envelope 冲突、历史截断和资源上限的负向
   变异族；
5. 首次差异停止、固定 seed 重放和最小化复现输出；
6. 绑定 MIF/Sanmill/NMM_LLM commit、launch-package hash、seed 和结果的报告。

MIF 发布该 launch package 和开工 hash 之前，Sanmill 与 NMM_LLM 不需要修改
适配器。收到通知后，两边使用现有独立 adapter 运行同一 seed/mutation 集，持久化
各自及三方报告；若发现差异，继续按第 7 节分类。M4 的退出条件是全部固定 seed
和必需负向变异均无未解释差异，且每个失败都可由单一 seed 与最小输入重放。

### 5.4 M4 开工基线

MIF 已实现并验证第 5.3 节要求的 launch package，现固定以下输入：

- 算法合同：`interop/differential-v1.md`；
- launch：`interop/differential-candidate-4-v1.json`，raw SHA-256 为
  `560ef369fde248bd96d3468a4336442db1d970ede04f488821509e69925fd48e`；
- launch/report Schema：`interop/schema/differential-launch-v1.schema.json`
  与 `interop/schema/differential-report-v1.schema.json`；
- 协议级负向 case：`interop/cases/differential-negative-v1.json`；
- driver：`tools/run_mif_1_0_differential.py`；
- 双 reference 基线：
  `interop/evidence/mif-1.0-candidate-4-m4-reference-baseline.json`，raw
  SHA-256 为
  `29d198dbcf8221fa0235af6a72db9d6a82646b45fc653c584071821a9a4bb61b`。

该基线使用 `splitmix64-v1` 的四组跨语言测试向量，执行 7 个场景、10 个
`(scenario, seed)` trajectory 和 5 个负向 mutation family。双 reference
结果为 10/10 与 5/5，且只读重跑可逐字节恢复同一报告。它只证明 launch 与
harness 可重现，不是独立实现证据，也不改变 candidate-4 wire、artifact 或 M3
corpus。

Sanmill 与 NMM_LLM 现在可以开工，且不需要修改玩法语义或 adapter protocol。
两边应：

1. 固定本次 MIF M4 launch 提交的完整 SHA，并核验上述 launch hash；
2. 保持 launch 文件逐字节不变，只在 `MIF-INTEROP-CONFIG/1` 中替换 adapter
   command；
3. 使用现有 `project-legal-actions`、`execute`、`replay` 与
   `project-logical-turns` 实现运行：

   ```text
   python -B tools/run_mif_1_0_differential.py --config <three-project-config.json> --launch interop/differential-candidate-4-v1.json --report <three-project-report.json>
   ```

4. 先各自持久化与 reference 的报告，再由任一项目持久化三 adapter 报告；
5. companion evidence 必须绑定三个被测 commit、MIF launch commit、launch
   hash、config hash 与 raw report hash。

如出现差异，报告已包含首次差异 stage、JSON Pointer、expected/actual、固定 seed
和最短 event prefix；直接按第 7 节分类，不得重新选 seed 或改写 launch。M4 只有
在两个独立实现的相同输入结果与三方报告均无未解释差异后才关闭。

### 5.5 M4 闭合结果

M4 已完成。两个产品项目没有修改 frozen wire、launch、seed 或 mutation：

- Sanmill 的 adapter 实现提交为
  `ae9a1d8a16261478631a3a7583cbf35c7b6e0df5`，两方 evidence 提交为
  `9431b95f151502f415f096c7d96ca944e5d578de`；Reference + Sanmill 报告为
  10/10 seeded trajectories 与 5/5 negative mutation families，raw SHA-256
  为 `0135ba7778a4623cecc0fe07173f50d76d3f06b6afd7830269b2c01e168604a7`；
- NMM_LLM 的 adapter 诊断修复提交为
  `6c1538082fc551203d827782d137a5799c810535`，evidence 提交为
  `382eddd1c5a3364c0056e152b524f517d126a113`；Reference + NMM_LLM 报告为
  10/10 与 5/5，raw SHA-256 为
  `2bc434699902a1c468b604797d4456ee0c968817b057ec4dc8254a623a1ba64c`；
- Sanmill 在 `2a53a89893daae528af64503cc87e34bf07e66e3` 发布最终三方报告和
  companion manifest。三方报告为 10/10 与 5/5，raw SHA-256 为
  `7956c320cf771767dcb3ecf1fbdb5b10c7313028f25aab3a53f9f0d42021d967`，
  manifest raw SHA-256 为
  `5ebc54b551c1b6258d07843cdc86447565ef7710be9678e354ac27ddec5c191f`；
- MIF 在三个已发布提交上独立连续复跑两次，均逐字节产生同一三方报告；
  NMM_LLM 的 62 项 MIF 聚焦测试也独立通过。

`interop/evidence/mif-1.0-candidate-4-m4.json` 固定全部 commit、launch、报告、
manifest 与复核 identity。M4 的结论为 `exact-for-tested-domain`：只覆盖该固定
Candidate-4 launch 的 10 个 trajectory 与 5 个 mutation family，不外推为所有
规则集、所有历史或所有实现输入的一般等价性，也不是 MIF Suite 1.0 conformance。

下一里程碑为 M5 Release：完成治理、许可、媒体类型、文件扩展名、签名 release
manifest、最终 suite artifact 绑定与 Git tag 后，才可发布实际
`mif-suite-1.0.json`。

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
