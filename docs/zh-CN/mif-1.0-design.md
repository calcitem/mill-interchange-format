# MIF 1.0 设计基线与发布门槛

状态：保留的设计依据；wire 决定已经落实

参考基线：提交 `9ecc134853628dc29d3037727a566702505fda1f` 的 MIF Community Working Draft 0.4

规范性后继：[`mif-1.0.md`](mif-1.0.md)，MIF 1.0 Candidate Wire Contract

符合性状态：不再作为规范性 wire 正文；MIF Suite 1.0 尚不是符合性目标

Candidate Wire Contract 已落实本文记录的决定。本文仅保留为评审理由和发布
门槛历史；若与 wire contract 不一致，以 wire contract 为准。

本文记录 MIF 1.0 Candidate 及其发布制品必须实现的决定。文中的
“必须”“应当”“可以”约束未来 Candidate，不改变 MIF/0.4。

本轮评审结论为：**修改后采纳**。五项 1.0 阻塞意见全部采纳，其他强烈
建议也纳入 1.0 工作，具体发布等级见第 13 节。相对原建议作四点收紧：

- 保留紧凑 MFEN，新增自识别的位置 envelope；
- `semanticDigest` 的投影由具体 semantics profile 定义，不能对未知对象
  简单删除几个字段后就声称语义等价；
- 0.4 的 `legal-state-v1` 只在 0.4 中继续有效，1.0 通过显式转换映射引入
  不易误解的新名称；
- 区分精确 resumption identity、decision equivalence 与可选的对称
  normalization。

第二轮维护人评审新增六项 wire freeze 前的修正：玩家与行动顺序身份、
resumption 与 decision 等价性拆分、MPK 直接绑定规则语义、变换不变性声明、
放置阶段活性和重复观察范围。六项全部采纳；前四项是冻结 1.0 wire contract
前的最高优先级阻塞项。

## 1. 兼容边界

### 1.1 冻结的 0.4 基线与实施目标

引用的 0.4 版本继续作为可独立识别的工作草案。1.0 实现不得把任何 0.4
signature、digest 或 `legal-state-v1` 对象按 1.0 的含义重新解释。

提交 `9ecc134853628dc29d3037727a566702505fda1f` 的版本冻结为历史工作
草案和迁移测试输入。其规范正文与 conformance corpus 不再接受协议修正。
后续可以新增消费这些冻结 0.4 字节的 1.0 conversion/rejection vector，但
不得改变原字节，也不得静默升级有歧义的输入。
冻结的英文规范原始文件 SHA-256 为
`F1F1D839318A4D45F3ECEA4850FEE080C47FFCBC81025BD74E3EA48C815F3093`。

NMM_LLM 与 Sanmill 直接以 MIF Suite 1.0 为实施目标。实现或声称符合 0.4
不是前置条件。

### 1.2 保留的架构

MIF 1.0 保持四层架构：

- MFEN：紧凑的瞬时局面；
- MPK：有意有损的稳定结构分析键；
- MSTATE：可恢复的历史和审计状态；
- MRS：有限规则集清单。

MIFPOS 只是 MFEN 外层 envelope，不合并上述层次。完整 1.0 发布必须同时
具备新规范、schema、grammar、registry 和 conformance vectors；只替换四个
`0.4` signature 不构成 1.0 发布。

### 1.3 玩家身份与行动顺序

MIF 1.0 选择固定颜色身份解释：

- `w` 是 White，也是稳定的 player identity 0；
- `b` 是 Black，也是稳定的 player identity 1；
- 两种身份都不暗示谁先行动；
- **initial player** 仅由 `turn.initial` 的值决定。

规范术语 *first player*、*second player* 不得再作为 White、Black 的别名。
只有引用外部材料并明确解释其含义时才可以使用。

MRS/0.4 的 board-full token 实际编码固定颜色效果，但名称使用了 `first`
与 `second`。MRS/1.0 因此替换如下：

| MRS/0.4 token | MRS/1.0 token |
|---|---|
| `first-player-loses` | `white-loses` |
| `first-then-second-remove` | `white-then-black-remove` |
| `second-then-first-remove` | `black-then-white-remove` |

`active-player-removes`、`draw`、`disabled` 保留不依赖顺序的名称。0.4
转换器必须按三个旧值已经规定的效果映射，不得依据 `turn.initial`，也
不得依据某种语言对“先手”的习惯用法。

1.0 corpus 必须包含完整的 `turn.initial=b` 初始状态、replay、board-full
终局和 board-full 移除顺序向量。每个固定颜色 token 在
`turn.initial=w` 与 `turn.initial=b` 下必须保持相同颜色效果。

### 1.4 回合计数术语

一个 **MIF logical turn（逻辑回合）** 是一名玩家的一次 primary `place`
或 `move`，加上直到下一个 stable boundary 为止由其产生的全部强制
`remove`。primary ply 只计算一次成功 primary action；补充移除不增加
primary ply。

一个 **full move（整回合）** 或 **round（轮）** 通常包含双方各一个
logical turn。规范文本在实际指 logical turn、primary ply 或 full move
时，不得使用未限定的“turn”。这样可避免与棋题文献中“一回合等于两 ply”
的计数习惯混淆。

## 2. 规则身份与两个摘要域

### 2.1 摘要定义

MRS/1.0 定义两个摘要域：

- `semanticDigest`：标识有效 manifest 规范化后的玩法语义；
- `documentDigest`：标识完整的规范 manifest 文档。

二者沿用：

```text
sha256:<64 个小写十六进制数字>
```

`documentDigest` 是完整 MRS 对象的 RFC 8785 JCS UTF-8 字节的 SHA-256。
参与散列的对象中不插入任何 digest 字段。

`semanticDigest` 是 semantic projection 对象的 JCS UTF-8 字节的 SHA-256。
投影对象包含 `mrs-semantic-v1` 之类的投影 profile 标识，从而与完整文档
进行摘要域隔离。

### 2.2 语义投影

每个注册的 semantics profile 必须定义完整的语义投影算法。算法必须：

1. 列出全部纳入成员以及数组的顺序或集合规范化方式；
2. 纳入 semantics profile 身份、拓扑、启用的规则机制、状态转移政策、
   终局政策、semantic-state 声明以及所有已理解的语义扩展；
3. 排除规则别名、生命周期和表现元数据，包括 `id`、`version`、`title`、
   `status`、`description` 和 `annotations`；
4. 对该 profile 声明为“机制禁用时不生效”的值进行规范化或省略；
5. 遇到未知语义扩展时拒绝，而不是丢弃；
6. 对仅有非语义元数据不同的 manifest 产生同一投影。

通用实现不得通过“从未知 MRS 对象中删除一份硬编码字段名单”生成投影。
实现必须支持所选 projection profile；未知 profile 或未知语义扩展必须
fail closed。

1.0 采用的 `mif-finite-rules` profile 在冻结标识符前，必须发布逐成员投影
表和向量。原因是 MRS/0.4 有些为保持固定形状而保留的值，在机制禁用时并
不影响玩法。

### 2.3 用途

MSTATE、decision-state、训练环境和玩法缓存使用 `semanticDigest` 绑定玩法
身份。实现不得仅因 `title`、`status`、`description` 或 annotation 改动而
使玩法身份失效。

registry 记录、release package、签名和精确文档完整性使用
`documentDigest`。portable envelope 同时携带二者：前者标识玩法语义，
后者校验实际内嵌文档。

规则集 `id@version` 仍是来源和解析身份。两个不同命名的规则集可以具有
相同 `semanticDigest`；它们在该投影下玩法等价，但不是同一发布物。

必须提供以下向量：

- 只改 title 或 status：`semanticDigest` 不变，`documentDigest` 改变；
- 修改已启用规则：两个摘要都改变；
- 改变 `id@version` 的别名：`semanticDigest` 不变，`documentDigest` 改变；
- 只改变禁用机制的无效成员：`semanticDigest` 不变；
- 出现未知语义扩展：投影失败，不生成猜测摘要。

## 3. 自识别位置 envelope

### 3.1 选定方案

MIF 1.0 保持裸 MFEN 紧凑，新增 JSON envelope `MIFPOS/1.0`；不采用把规则
身份直接加入 MFEN 的方案。

以下是不符合格式的最小结构草图，其中省略号和空 manifest 都只是
placeholder：

```json
{
  "format": "MIFPOS/1.0",
  "positionFormat": "MFEN/1.0",
  "stateProfile": "mill24-state-v1",
  "position": "MFEN/1.0 ...",
  "ruleset": {
    "mode": "portable",
    "id": "example-rules",
    "version": 1,
    "semanticDigest": "sha256:...",
    "documentDigest": "sha256:...",
    "manifest": {}
  }
}
```

精确的闭合成员集合和 schema 留给 1.0 Candidate 完成，但以下行为已经
确定：

- `mode` 必须显式为 `portable` 或 `reference`；
- portable 必须内嵌精确 manifest，并校验两个 digest；
- reference 省略 manifest，必须携带 `semanticDigest` 并显式使用 resolver；
  只有需要锁定某一精确发布文档时才携带 `documentDigest`；
- 规则语义无法解析或发生冲突时 fail closed；
- consumer 不得自动访问网络；
- 通用 export、copy、二维码或 share 操作默认输出 portable，只有调用方
  明确请求紧凑引用时才输出 reference。

### 3.2 裸 MFEN 的边界

MFEN/1.0 必须明确标为 **context-bound**。裸 MFEN 在外部提供规则上下文时
是完整瞬时状态，但不是自识别交换对象。文档和 capability 声明不得把裸
MFEN 描述为可以独立分享或独立完成语义验证。

MIFPOS 只为一个瞬时局面补齐规则闭包，不携带事件历史、有效 repetition
window 或 draw-offer 审计，因此不能替代 MSTATE、resumption state 或
decision state。

## 4. Portable 与 reference MSTATE

MSTATE/1.0 使用与 MIFPOS 相同的显式规则模式。

`portable` 模式的 ruleset envelope 必须内嵌精确 MRS manifest、
`semanticDigest` 和 `documentDigest`。replay 前必须校验身份、语义投影和
完整文档。

`reference` 模式可以省略 manifest。resolver 使用
`(id, version, semanticDigest)`。需要锁定精确发布 manifest 时，envelope
可以同时携带 `documentDigest`；存在该成员时 resolver 结果必须匹配，不存在
时非语义文档改动不得使解析失效。所需 digest 层级缺失或冲突即失败。
reference 是显式存储优化，不再根据规则集是否“已注册”隐式决定。

默认导出政策为：

- 训练数据、存档和跨项目交换必须使用 portable；
- 通用 save、export 和 share API 默认使用 portable，除非调用方明确要求
  reference；
- 应用内部 compact cache 在能够控制并说明 resolver 生命周期时可以使用
  reference。

压缩和 package 级去重可以减少重复 manifest 字节，但单个被声明为
portable 的对象必须保持自包含。

## 5. 状态与键身份

### 5.1 Repetition observation

MRS/1.0 用 `repetition-observation-v1` 替换 0.4 的投影 token
`legal-state-v1`。它仍是重复规则投影，不是完整 decision key；规范必须
继续明确列出它排除的权威字段。

`repetition-observation-v1` 使用 `semanticDigest` 绑定规则语义，不使用
`documentDigest` 或规则发布元数据。包含它的 MSTATE 可以保留规则集
`id@version` 来源，但该来源不得改变 repetition equality。
观察边界及其放置/移动阶段范围见 10.2。

0.4→1.0 转换只有在完整验证 0.4 规则和状态后，才能把
`legal-state-v1` 映射为 `repetition-observation-v1` 并计算 semantic
projection；不得原地改写已存储的 0.4 字节。

### 5.2 `resumption-state-v1`

MIF 1.0 注册 `resumption-state-v1`，作为保留坐标帧的精确恢复和审计
身份。其规范 JCS 对象包含：

- resumption profile 标识；
- position format 标识与当前权威 MFEN 的规范文本；
- MRS `semanticDigest`；
- 完整有序 repetition window，使用 `repetition-observation-v1` 对象，并
  保留精确 replay 所需的 observation 与 source/event provenance；
- 当前 open draw offer，以及合法 accept、decline 或 withdraw 所需的 wire
  reference；没有时为 `null`；
- 当前可实际行使的 draw-claim reason 精确集合；
- 规范 origin、pre-origin seed 和已 replay event prefix 的内容摘要，以及
  当前 event-sequence anchor；
- 精确 replay 所需的完整 claim/offer audit 与 wire reference；
- 所选 profile 要求的全部已注册语义 resumption extension。

内嵌的权威 MFEN 已经携带 no-progress、primary-ply、pending obligation、
语义状态和 terminal outcome；这些值不得被静默删除，也不得复制成可独立
变化的第二份字段。

`resumptionDigest` 是完整 `resumption-state-v1` 对象 JCS UTF-8 字节的
SHA-256；参与散列的对象中不插入 digest 成员，词法形式见 2.1。它用于
存档、replay checkpoint、跨实现恢复比较和审计身份，不得默认用作训练
去重或 PUCT 节点键。

无法建立完整 repetition history、replay-prefix 身份、offer reference 或
claim audit 时，producer 必须报告历史不足，不得输出
`resumption-state-v1`。

### 5.3 `decision-state-v1`

MIF 1.0 另外注册 `decision-state-v1`，它只保留在所选 semantics profile
下会改变合法动作、后续状态转移或结果的充分状态。它是 profile 定义的
projection，不是完整 MFEN 或 MSTATE 的不透明副本。

projection 必须包含：

- decision profile 与 MRS `semanticDigest`；
- 可能影响未来决策的 board、active player、phase/action、hands 与 pending
  obligation；
- 仅在所选 semantics profile 要求时包含 no-progress、terminal outcome
  与语义扩展；
- repetition profile 的充分统计量；
- 以 actor 和可用操作表达的语义 open-offer state，不包含原始
  `offerEventSeq`；
- 当前可以实际行使的 draw-claim reason 精确集合。

projection 必须排除：

- `primary-ply`，除非所选 semantics profile 明确声明它会改变合法动作、
  状态转移或结果；
- 只用作 wire reference 的 event sequence 和 history provenance；
- 已关闭的 offer/claim audit record；
- 当所选 repetition profile 声明顺序无关的充分统计量时，完整有序
  repetition history；
- `documentDigest`、title、status 与 annotation。

adapter 把规范 offer operation 映射回当前 wire `offerEventSeq`；该引用
属于 resumption identity，不属于 decision equivalence。

每个 repetition profile 必须定义自己的 sufficient-statistic profile。
对 reset-clears-window 语义，基线统计量是从
`repetition-observation` digest 到出现次数的规范 map；次数封顶为 claim
或 automatic threshold。数组顺序与观察来源不属于该统计量。未来的
sliding-window 或顺序敏感规则必须使用另一个版本化统计 profile。

统计量及其摘要必须定义增量更新算法；按不同 active observation 数量计，
复杂度不得差于对数级。producer 不得在每次 primary action 后重新散列
不断增长的完整有序 window。portable 诊断表示可以物化 map，搜索节点可以
保留注册的 persistent-map root 及其 backing state。

`decisionDigest` 是规范 `decision-state-v1` projection 的 JCS UTF-8
字节 SHA-256；参与散列的对象中不插入 digest 成员，词法形式见 2.1。它是
训练去重、PUCT 节点、decision cache 和跨实现决策比较的标准精确坐标身份。

不属于游戏规则的训练限制，包括 `max_ply`、rollout limit 和 truncation
policy，必须由单独的版本化 `experimentDigest` 绑定。训练身份至少绑定
suite、ruleset semantic、experiment 和 decision 四类 digest；不得把
`primary-ply` 当成实验配置的隐式替代。

identity vector 必须包含多组 decision-equivalent 的有效历史：它们只在
不影响决策的 primary-ply/provenance、具有相同注册充分统计量的有序
repetition history，或原始 `offerEventSeq` 上不同。每组必须产生相同的
规范 decision state 与 `decisionDigest`，但产生不同 resumption state
与 `resumptionDigest`。

negative vector 必须分别改变每个语义组成，包括 active player、影响合法
动作的 obligation、可用 offer operation、claim right、repetition threshold
状态、适用时的 no-progress 状态和 outcome。每项变化都必须反映在规范
decision state 及预期 digest 中。

基础 digest 保留来源坐标帧。需要按对称等价去重的应用，必须先应用已注册
的 full-state normalization profile，在规范对象中包含该 profile 标识，再
计算 digest；不得暗中拿 MPK normalization 替代。

### 5.4 MPK/1.0 规则绑定

MPK 继续是有意不完整的结构键，不得作为 repetition key、resumable-state
key 或 decision-state key。

但独立 MPK/1.0 record 必须直接绑定规则语义。wire form 把完整
`semanticDigest` 放在 `ruleset-id@version` 之后、`key-profile` 之前：

```text
MPK/1.0 <state-profile> <ruleset-id@version> <semanticDigest>
<key-profile> <board24> <side> <phase> <hands> [<key-extension> ...]
```

以上仅为排版而换行。dataset envelope 可以重复该绑定，但值必须与 MPK
record 一致。只携带 `id@version` 的 MPK/1.0，或 resolver 得到的 manifest
产生不同 `semanticDigest` 时，record 无效。MPK 虽可自绑定规则语义，
在做语义验证或验证发布者信任时仍需要可信 manifest 或 registry。

MPK vector 必须覆盖缺失 `semanticDigest`、envelope/record digest 失配、
resolved-manifest 失配，以及 `id@version` 相同而 semantic digest 不同的
两个其他字段相同的 MPK record。前三种拒绝；最后一组具有不同的规范 MPK
字节，不得作为相同文本数据库键。

### 5.5 Claim right 生命周期

MIF 1.0 把 claim entitlement 定义为确定性派生状态，边界如下：

1. no-progress 或 repetition claim right 只在全部确定性处理完成、到达
   stable primary decision boundary 且 claim-mode threshold 满足后产生；
2. 权利属于 active player，并记录当前可 claim 的精确 reason 集合；
3. 当 gameplay decision boundary 未变化时，offer、decline、withdraw 不
   消耗该权利；accept、resign、adjudication 或其他 terminal transition
   将其关闭；
4. 任一成功 primary 或 supplementary gameplay action 被接受之前，该权利
   立即失效；
5. 旧权利不得带入 pending-removal state；logical turn 到达下一个 stable
   boundary 前也不产生新权利；
6. 合法 `claim-draw` 消耗所选权利并进入 terminal state。

玩家选择继续执行 primary action 后，不得再使用上一 boundary 的权利。
pending obligation 期间的 `claim-draw` 在 1.0 中无效。导入的 resumption
state 必须包含或可派生当前权利；replay 必须验证权利，不能仅凭 counter
猜测其持续性。

向量必须覆盖权利产生、在非 gameplay draw negotiation 中持续、primary
action 前失效、primary action 产生 pending removal、remove 后重新评估，
以及终局消费。

## 6. 逻辑回合投影与原子动作转换

MSTATE/1.0 标准化从 replay 派生的 logical-turn projection，但不把 remove
事件隐藏进 primary event。

基础算法必须：

1. 按顺序 replay origin 和 events；
2. 每个成功 `place` 或 `move` 开始一个 logical turn；
3. 把此后解决该 primary sequence 因果产生的 obligation 的每个 `remove`
   事件归入该回合，包括在 stable boundary 确定性生成的 obligation；
4. 所有相关 obligation 与 stable-boundary processing 完成后关闭该回合；
   若中途发生终局，则标记 truncated；
5. 保留原始 `seq` 和有序 remove-event seq 列表；
6. origin 已存在 obligation 时，把对应 remove 表示为没有虚构 primary event
   的 origin fragment；
7. origin 原本没有 obligation，但 origin stabilization 确定性产生
   board-full、stalemate 或 mill-count obligation 时，把对应 remove 表示为
   没有虚构 primary event 的 `origin-stabilization` fragment。

draw negotiation 或其他允许的非 gameplay event 可以位于该事件区间；它们
继续保留在 MSTATE 中，但不被改写为 logical-turn action list 的 primary 或
remove action。

基础事件格式不强制增加 `causedBySeq`：有效 replay 已能唯一确定因果
primary sequence。未来 profile 只有在规定校验和规范化方式后，才可以增加
冗余因果索引。

conformance corpus 必须提供以下 NMM_LLM 双向向量：

- 无移除的 place；
- 无移除的 move；
- place 或 move 加一次 board removal；
- 目标表示支持时的 hand removal；
- 多个后续 removal；
- pending-origin fragment；
- obligation-free origin 经 stabilization 产生的 board-full、stalemate 和
  mill-count fragment；
- 所有有损或不可表示的反向映射。

只有当目标原子记录可以无猜测表示完整 logical turn 时才能输出。MSTATE
继续把每个 removal 序列化为独立事件。

## 7. 标准诊断 envelope

MIF 1.0 为 parse、validation、replay 和 conversion failure 定义统一 JSON
诊断 envelope。它至少包含 format 标识和非空、有序 `errors` 数组。每个
error 都包含标准 `category` 和 `code`。

以下定位和详情字段必须标准化，只在不适用时省略：

- `instancePath`：指向 JSON 输入的 RFC 6901 JSON Pointer；
- `textOffset`：原始文本输入 UTF-8 字节的零起点 `start`（含）和 `end`
  （不含）；
- `eventSeq`：正在验证或 replay 的 MSTATE event；
- `expected`、`actual`：受资源限制约束的 I-JSON 诊断值；
- `resourceLimit`：资源名、配置上限和实际观测值。

同一缺陷可在多个验证阶段报告时，envelope 必须定义确定性优先级。实现可以
增加本地化人类文本，但互操作 consumer 不需要解析该文本。

## 8. 机器可读 capability

MIF 1.0 定义带版本 format 标识的 capability document，可声明：

- 实现名称和版本；
- 精确 suite digest；
- 支持读取和写出的 format；
- conformance class；
- semantics、state、repetition、repetition-summary、resumption、decision、
  key 和 transform profile；
- placing-liveness、claim-right、MPK semantic-binding 与 transform-invariance 声明；
- ruleset `id@version`、`semanticDigest`，以及声明精确发布支持时的
  `documentDigest`；
- 支持的 source/target conversion mapping 和 loss policy；
- 配置的资源限制；
- 符合性声明所针对的 conformance-corpus digest。

read support、write support、tested conformance 和 experimental support 必须
可以区分。capability document 是机器可读声明，不是正确性或发布者信任的
证明。

## 9. 完整状态变换

1.0 transform 规范覆盖 MFEN、MIFPOS、MSTATE、resumption state、decision
state 和 action，不再只重点覆盖 MPK。注册的 full-state transform 必须
变换所有坐标或线相关值，包括：

- origin、current、resumption 和 decision position 的 board；
- primary event 的 `at`、`from`、`to`、`interventionLine`；
- board-removal target；
- obligation target bitset 和分支中其他坐标数据；
- `lm`、`ul` 和已注册语义扩展；
- repetition observation 的 board 和语义值；
- 与状态关联的规范 action、principal variation 或 result coordinate。

按玩家绑定的标量、event seq、counter、offer reference 和无坐标审计数据
保持含义。变换后的 MSTATE 在同一规则语义下 replay，必须得到变换后的
current checkpoint。

向量覆盖每个注册 transform 及其 inverse、pending obligation、`lm`、`ul`、
repetition history、action 和至少一个完整多事件 logical turn。transform
profile 必须说明是保留来源帧还是选择规范帧，以及 tie-break 方法。

坐标转换与等价归一化是不同声明。实现可以把 record 转换到另一个坐标帧，
但只有精确组合存在版本化 invariance declaration 时，才能声称保持规则
等价：

```text
(semanticDigest, transform-profile)
```

声明必须标识自身版本、state profile、允许的 transform ID、每个语义扩展的
处理方式和自身 document digest，并证明合法动作、状态转移、claim right
和结果在两个方向都保持。

没有该声明时，变换后 record 只能用于明确的坐标帧转换，不得用于 decision
canonicalization、训练去重、PUCT 合并、tablebase 合并，也不得声称 MPK
normalization 等价。

suite 与 capability document 必须固定其声称的每个 invariance declaration。
向量必须包含一个可完成结构坐标转换、但不得用于等价归一化的绝对坐标语义
扩展；每个已声明 transform 还要有正向与 inverse case。

## 10. 有限规则活性与重复观察范围

### 10.1 放置阶段没有合法 primary action

MRS/1.0 必须新增有限且必填的 `placing.noLegalPrimaryAction` 机制。在任一
ongoing、stable 的 phase-`p` primary decision boundary，完成确定性处理后，
引擎必须检查 active player 是否有合法 place 或获准的 move。若没有，必须
执行且只执行所选的一种 action：

- `apply-board-full`：执行 `boardFull.action`；只有 manifest consistency
  分析能证明每个可达触发点都满足 full-board predicate，且
  `boardFull.action` 不为 `disabled` 时，该选择才有效；
- `loss`：active player 以 `no-legal-primary-action` reason 负；
- `draw`：以 `no-legal-primary-action` reason 和棋。

状态不得在没有合法 primary action 时继续保持 ongoing。该规则也覆盖
full board 仍有 reserve、delayed blocked point，以及
`placing.movementAllowed=true` 但没有 move destination 的情形。

能到达此类状态、又没有决定以上效果的 0.4 ruleset，转换时必须显式选择
policy。转换器不得根据 `boardFull.action=disabled` 猜测。

向量必须覆盖 phase `p` 下 full board 加 reserve 的三种 action、无效的
`apply-board-full`/`disabled` 组合、delayed blocked point，以及两种
`turn.initial`。

### 10.2 Repetition observation 范围

MRS/1.0 至少支持两个明确的 observation profile：

- `stable-moving-v1` 只观察 ongoing、stable 的 phase-`m`、action-`m`
  boundary；选择它就明确表示 repetition 只在 moving phase 生效；
- `stable-primary-decision-v1` 在确定性处理后、没有 pending obligation
  时，观察 phase `p` 或 `m` 的每个 ongoing、stable primary decision
  boundary。

启用 repetition 且 `placing.movementAllowed=true` 的 manifest，必须选择
`stable-primary-decision-v1`，或有意选择并公开仅 moving-phase 的范围。
capability 与面向用户的规则说明不得只写“三次重复”，而不写所选观察范围。

向量必须覆盖 placing-regime movement cycle、普通 moving cycle、placement
reset event、不参与观察的 pending removal、origin stabilization，以及
automatic 和 claim 两种模式。

## 11. MIF Suite 1.0 manifest

1.0 正式发布必须包含规范的 `mif-suite-1.0.json`，固定一组已经共同测试的
组合，不让 consumer 猜测组件版本是否兼容。

suite manifest 至少包含：

- 自身 format 和 suite 标识；
- MFEN、MPK、MSTATE、MIFPOS、MRS 的精确版本；
- diagnostic 与 capability format 或 schema 的精确标识；
- 选定的 semantics、state、repetition、repetition-summary、resumption、
  decision、key、transform profile；
- placing-liveness policy、claim-right profile、MPK semantic-binding profile
  与每个 transform-invariance declaration；
- 规范 commit 与原始文件 SHA-256；
- registry、conformance corpus、JSON Schema、ABNF 原始文件 SHA-256；
- conversion vectors 和 0.4→1.0 migration vectors SHA-256；
- corpus-integrity checker 与 executable reference runner 的标识和原始文件
  SHA-256；
- media type 和推荐扩展名；
- compatibility policy；
- signature manifest 标识或位置。

suite digest 是 suite 对象 JCS UTF-8 字节的 SHA-256，对象中不插入 digest
字段。发布工具在文件旁公布 digest，并签署绑定它的 release manifest。

训练 run、数据库和跨项目测试应记录 suite digest，以及使用的每个规则集
`semanticDigest`。既没有精确 suite digest、也没有显式组件清单的
“支持 MIF 1.0”声明是不完整的。

最终 suite 文件不得含 placeholder；所有被引用的 1.0 制品冻结并验证后才
计算真实 hash。

## 12. 版本生命周期、annotations 与 extensions

MRS/1.0 和其他 JSON envelope 分别预留 `annotations` 与 `extensions` 容器。

对 MRS：

- `annotations` 非语义，计入 `documentDigest`，不计入
  `semanticDigest`，可以按 MRS 的规则忽略或 round-trip；
- `extensions` 是语义内容，计入 `semanticDigest`，必须标识明确 profile，
  不支持时 fail closed。

对其他 envelope，`annotations` 不进入玩法和 decision projection；若该格式
定义完整文档摘要，则计入该摘要。`extensions` 进入所有适用的 semantic 或
decision projection，同样必须标识明确 profile。

实现不得把玩法行为放入 `annotations`，也不得把未知 `extensions` 当成可
忽略元数据。

1.x 生命周期政策如下：

| 变化 | 必要动作 |
|---|---|
| 使用既有闭合格式和 profile 新增 ruleset 或 registry annotation | 更新 registry；不改变既有 digest |
| 新增 optional syntax 或 capability，且不重解释既有字节 | 使用新的 minor format signature 或独立命名的 profile，并增加 schema、向量和 suite release |
| 改变规则集合法动作、状态转移、终局行为或语义扩展 | 新 ruleset version 和新 `semanticDigest` |
| 只改变发布元数据 | 新 `documentDigest`；ruleset version 与 `semanticDigest` 不变 |
| 改变既有 signature/profile 的含义、规范形式、摘要投影、必需成员或默认行为 | 升级 2.0；只有在既有字节仍保留原身份和含义时，才可另设 1.x signature/profile |
| 删除或重命名既有 token、弱化 fail-closed、改变缺省数据的默认含义 | 升级 2.0 |

只增加 registry value 不得扩展闭合 grammar 或重解释既有 profile。

## 13. 发布门槛与意见处置

### 13.1 Wire freeze 前的最高优先级阻塞项

首先必须闭合以下四项：

1. 固定 White/Black 身份、initial-player 术语、重命名 board-full token，
   并提供完整 `turn.initial=b` 向量；
2. 将 `resumption-state-v1`/`resumptionDigest` 与 profile 定义的充分
   `decision-state-v1`/`decisionDigest` 分开，包括增量 repetition
   summary 和独立 `experimentDigest`；
3. 每个 MPK/1.0 record 直接绑定 `semanticDigest`；
4. 每个声称等价的 `(semanticDigest, transform-profile)` 组合具有版本化
   invariance declaration。

### 13.2 Wire freeze 前的其他阻塞项

wire contract 还必须先定义：

1. `placing.noLegalPrimaryAction` 及 full-board/reserve 向量；
2. `stable-primary-decision-v1` 与明确的 moving-only repetition 范围；
3. claim right 的完整产生、持续和失效生命周期；
4. origin-stabilization logical-turn fragment；
5. 上述每项有歧义 0.4 construct 的规范 conversion/rejection 行为。

### 13.3 Wire freeze 后仍需完成的发布制品与证据

以下项目继续阻塞 1.0 正式发布：

1. `semanticDigest`/`documentDigest` 拆分和完整投影向量；
2. MIFPOS portable/reference 符合性向量；
3. `repetition-observation-v1`、`resumption-state-v1`、
   `resumptionDigest`、`decision-state-v1`、`decisionDigest` 和
   `experimentDigest` 的 schema 与向量；
4. portable-by-default MSTATE 和 resolver failure 向量；
5. 最终 `mif-suite-1.0.json` 与签名 release manifest；
6. 规范 logical turn 和 NMM_LLM 双向转换向量；
7. 标准 diagnostic 与 capability schema；
8. 1.x/2.0 lifecycle 与 extension policy；
9. JSON Schema、ABNF、推荐文件扩展名和正式记录的 media-type assignment；
10. 正式仓库 LICENSE 和 registry governance policy；
11. suite 声明的每个 transform 的 full-state vector；
12. 规范 0.4→1.0 conversion 与 failure vector；
13. MIF/0.4 Annex F.9 已列出的双实现、跨语言 replay、fuzzing 和治理条件；
14. 名称和成功文本只声称 `corpus integrity passed`、不声称执行了规则的
    corpus-integrity 命令；
15. 能解析并执行每个适用 1.0 规则、transition、transform 和 MSTATE replay
    vector 的 executable reference runner；它必须把执行符合性与 corpus
    integrity 分开报告。

仓库所有者仍需选择 LICENSE、registry 治理主体、最终 media type 名称和
release signature 机制。本文不会替所有者虚构法律授权或治理共识。

### 13.4 必须遵循的实施顺序

项目按以下顺序推进：

1. 闭合 13.1 和 13.2 的设计阻塞项；
2. 冻结完整 MIF 1.0 wire contract；
3. 生成 1.0 ABNF、JSON Schema、registry 和 conformance corpus；
4. 建立 executable reference runner；
5. 由 Sanmill 与 NMM_LLM 直接实现相互独立的 1.0 adapter；
6. 在同一 corpus 上比较规范字节、语义状态和 replay 结果；
7. 两个实现一致后才发布 `mif-suite-1.0.json`。

corpus-integrity checker 只能证明交付文件内部一致，不能代替第 4 至第 6
步。

### 13.5 明确保留的不变项

以下意见作为 1.0 约束采纳：

- 不把 MFEN、MPK、MSTATE、MRS 合成万能格式；
- removal 继续作为独立 MSTATE event；
- MRS 继续是有限机制 manifest，不扩成通用规则 DSL；
- 有损转换继续显式、按固定优先级、fail closed，不猜测兼容。

所有阻塞制品完成且 suite digest 发布前，仓库只能把 1.0 描述为设计中的
Candidate Wire Contract，并明确尚无已发布的 suite conformance target；不得
声称符合 MIF Suite 1.0。

Sanmill 与 NMM_LLM 都不需要实现 MIF/0.4。0.4 后续唯一用途是字节冻结的
历史基线，以及显式 0.4→1.0 conversion/rejection vector 的 source format。
