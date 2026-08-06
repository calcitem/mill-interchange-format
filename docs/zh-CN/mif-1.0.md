# Mill Interchange Format 1.0

## 候选 Wire Contract

状态：wire contract 已冻结；MIF Suite 1.0 conformance 尚不可用

本文档是 MIF 1.0 完整、独立的规范性 wire contract。它定义后续独立
ABNF、JSON Schema、registry、conformance corpus 和可执行 runner 必须实现的
字节、JSON 数据模型、状态转移、身份与失败行为。

冻结本合同不表示上述后续制品或两个独立实现已经存在。在最终
`MIFSUITE/1.0` manifest 标识这些制品之前，producer 不得声称符合
MIF Suite 1.0。

commit `9ecc134853628dc29d3037727a566702505fda1f` 的 MIF Community
Working Draft 0.4 保持字节冻结，仅作为历史输入。其英文规范 raw-file
SHA-256 为
`F1F1D839318A4D45F3ECEA4850FEE080C47FFCBC81025BD74E3EA48C815F3093`。

# 1 范围

MIF 为 Mill 系列游戏定义可互操作的表示：

- MFEN：依赖外部规则集上下文的紧凑即时局面；
- MPK：有意不完整的结构分析键；
- MIFPOS：自带规则身份的即时局面 envelope；
- MSTATE：含权威 checkpoint、可恢复的事件历史；
- MRS：有限机制规则集 manifest。

MIF 还定义派生的 resumption 与 decision 身份、诊断、capability、转换报告、
变换不变性声明、逻辑回合投影，以及未来 suite manifest 的形状。

MIF 不标准化竞赛规程、搜索评估、UI 行为、数据库压缩、通用规则 DSL、
网络发现或发布者信任。

# 2 规范性引用

本合同依赖以下规范：

- RFC 5234，Augmented BNF for Syntax Specifications: ABNF；
- RFC 7405，区分大小写的 ABNF 字符串字面量；
- RFC 8259，The JavaScript Object Notation (JSON) Data Interchange Format；
- RFC 7493，The I-JSON Message Format；
- RFC 8785，JSON Canonicalization Scheme (JCS)；
- RFC 6901，JSON Pointer；
- FIPS PUB 180-4，SHA-256。

# 3 术语和定义

## 3.1 玩家身份与初始玩家

`w` 是 White，且固定为玩家身份 0。`b` 是 Black，且固定为玩家身份 1。
身份均不隐含行动顺序。**初始玩家**是 `turn.initial` 的值。

未加限定的 *first player* 与 *second player* 不是 White 和 Black 的规范性
别名。

## 3.2 权威状态

consumer 必须保留、不得以派生缓存或猜测值替换的状态。

## 3.3 稳定 primary 决策边界

一个 ongoing、无 obligation、已经执行完全部确定性转移的状态；此时可以选择
primary gameplay event，或行使当前 claim right。

## 3.4 primary 与 supplementary action

primary action 是成功的 `place` 或 `move`。supplementary action 是解决
obligation 的 `remove`。

## 3.5 MIF 逻辑回合与 round

一个 **MIF logical turn** 是一名玩家的一次 primary action，加上直到下一个
稳定边界为止的全部后续强制 removal。一个 **full move** 或 **round** 通常
包含双方各一个 logical turn。

## 3.6 profile

state profile 定义局面字段。semantics profile 定义转移和终局优先级。
key profile 定义 MPK 投影与规范化。transform profile 定义坐标变换。
每个 profile 标识符独立版本化。

# 4 Conformance 边界

## 4.1 合同状态

本合同冻结以下格式签名和 profile 含义：

```text
MFEN/1.0
MPK/1.0
MIFPOS/1.0
MSTATE/1.0
MRS/1.0
MIFDIAG/1.0
MIFCAP/1.0
MIFCONV/1.0
MIFINV/1.0
MIFTURN/1.0
MIFSUITE/1.0
```

本合同注册：

- state profile `mill24-state-v1`；
- topology profile `mill24-orthogonal-v1` 与 `mill24-diagonal-v1`；
- semantics profile `mif-finite-rules-v3`；
- finite transition subprofile `after-unobligated-place-v1`、
  `on-enter-moving-v1`、`target-commits-v1` 与
  `stable-after-primary-sequence-v1`；
- MRS semantic projection `mrs-semantic-v1`；
- key profile `structural-d4-v1` 与 `structural-aut16-v1`；
- repetition projection `repetition-observation-v1`；
- observation profile `stable-moving-v1` 与
  `stable-primary-decision-v1`；
- repetition summary `reset-count-smt-v1`；
- resumption profile `resumption-state-v1`；
- decision profile `decision-state-v1`；
- claim lifecycle `stable-claim-rights-v1`；
- MPK binding profile `inline-semantic-digest-v1`；
- full-state transform profile `mill24-full-state-v1`；
- invariance declaration profile `transform-invariance-v1`；
- logical-turn projection `logical-turn-v1`。

实现只能输出自己已实现的签名与 profile。不得把未知签名解释为最接近的已知
版本。

## 4.2 Conformance class

未来 suite 可分别声明：

- `position`：MFEN/MIFPOS 解析、验证与规范输出；
- `key`：MPK eligibility、投影与规范化；
- `ruleset`：MRS 验证和两个 digest domain；
- `replay`：完整 MSTATE event replay 和 checkpoint 验证；
- `identity`：repetition、resumption、decision 投影与 digest；
- `transform`：坐标转换和已声明的等价性；
- `conversion`：MIFCONV 报告和已注册映射；
- `full`：suite 选定的全部 class。

仅凭本文 prose 不能测试任何 class。conformance 声明必须绑定后续 suite
digest 及其标识的可执行 corpus。

## 4.3 Fail-closed 规则

未知的无前缀语法、语义 event type、语义 extension、profile、obligation
cause 或标准 outcome reason 必须拒绝。未知语义内容绝不忽略或猜测。

# 5 通用 wire 约定

## 5.1 文本与 JSON

MFEN 和 MPK 只含 US-ASCII；字段之间恰好一个 U+0020 SPACE；没有前导或
尾随空白。传输 framing 不属于记录本身。

本合同中的每种 JSON 格式均为 UTF-8 I-JSON。不得输出 BOM。JSON escape
解码后 object name 必须唯一；未配对 surrogate 无效；parser 必须在转换为
map 之前检测重复 name。

规范 JSON 输出以及所有 JSON digest 输入均使用 RFC 8785 JCS。字符串不得
执行 Unicode normalization。

## 5.2 整数

精确整数范围为 0 到 9007199254740991（含端点）。文本整数使用无符号十进制；
除 `0` 外不得有前导零。

## 5.3 标识符

标识符由 1 至 63 个小写 ASCII 字母、数字、点或连字符组成，并以小写字母或
数字开头。`x-` 开头表示 private 或 provisional 标识符。

规则集引用为 `<identifier>@<positive-integer>`。

## 5.4 Digest

本合同中每个 digest 的 lexical form 为：

```text
sha256:<64 lowercase hexadecimal digits>
```

十六进制 payload 表示 32 个 SHA-256 字节。不同 digest 名称属于不同 domain；
即使算法字符串相同，也不能互换其输入。

## 5.5 JSON annotations 与 extensions

在允许的位置，`annotations` 是非语义 I-JSON object。规范输出省略空的
`annotations` object。

`extensions` 是 object 数组；每个 object 恰好包含 `profile` 和 `value`。
profile 唯一，并按 US-ASCII 升序排列。`value` 是该 profile 定义的任意
I-JSON 值。空数组省略。不支持 extension profile 的 consumer 必须拒绝包含
它的语义 object。

Annotations 不影响合法动作、replay、outcome、semantic digest、repetition、
decision identity 或 transform equivalence。Extensions 进入所有适用的语义
投影。

## 5.6 闭合 object

每个 JSON 成员表均为闭合。object 只能包含必需成员、表列出的可选成员，不得
包含其他成员。private 内容放入 `annotations` 或 `extensions`，不得增加未知
顶层名称。

# 6 `mill24-state-v1`

## 6.1 有序状态

状态字段依次为 board、side、phase、action、hands、obligations、
no-progress、primary-ply、outcome 和具名文本 extension。

board 是下列顺序的三个八字符 ring：

```text
a7 d7 g7 g4 g1 d1 a1 a4 /
b6 d6 f6 f4 f2 d2 b2 b4 /
c5 d5 e5 e4 e3 d3 c3 c4
```

board 字符为：

| 字符 | 含义 |
|---|---|
| `W`, `B` | White 或 Black 的 live piece |
| `w`, `b` | 保留原 owner 的 delayed-removal blocked token |
| `.` | 空的可用点 |

小写 token 占据点位，但不能移动、成 mill、被 remove、作为 destination 或计入
live material。

## 6.2 Side、phase 与 action

ongoing 状态的 `side` 为 `w` 或 `b`；terminal 状态为 `-`。Phase 为 `p`
（placing regime）、`m`（moving regime）或 `o`（game over）。Action 为
`p`（phase-p primary input）、`m`（moving input）、`r`（supplementary
removal）或 `o`。

Phase 与 action 是互相独立的权威字段。

## 6.3 Hands、counter 与 outcome

`hands` 包含当前 White 与 Black 尚未放置的 reserve，不从 placement history
派生。

`no-progress` 是当前 manifest counter。`primary-ply` 统计成功的 place 和
move event；remove event 不递增。

ongoing 时 outcome 为 `-`；terminal 时为 `w:<reason>`、`b:<reason>` 或
`d:<reason>`。

## 6.4 Obligation

Obligations 为 `-`，或以 `|` 分隔的 alternative branch。branch 内的顺序
obligation 以 `;` 分隔。

一个 obligation 为：

```text
actor:cause:zone:target-owner:remaining:targets:after
```

| 字段 | 值 |
|---|---|
| actor | `w`, `b` |
| cause | Annex A 注册的 cause |
| zone | board 为 `b`，hand 为 `h` |
| target-owner | `w`, `b` |
| remaining | 正整数 |
| targets | 六位小写 hex；hand 为 `-`；延后求 board target 为 `~` |
| after | `w`、`b`，或继续 branch 的 `q` |

所有 branch head 的 actor 相同；side 等于该 actor，action 为 `r`。board head
具有具体、非零 target set。后续 board record 在成为 head 前使用 `~`。hand
record 使用 `-`。`q` 要求其后还有 record；最终 record 指定下一个 primary
player。

Branch 先按 cause order、再按完整 US-ASCII serialization 排序。一个 remove
target 若匹配多个 head，选择第一个规范 branch。

## 6.5 文本 extension

标准 state extension 为：

| Key | Feature | 规范值 |
|---|---|---|
| `lm` | last mill | `W-from,W-to;B-from,B-to` |
| `pc` | placement count | `White-count,Black-count` |
| `ul` | used line IDs | `White-lines,Black-lines` |

必需的语义 extension 即使为零也必须出现。extension key 唯一，并按 US-ASCII
升序排列。

对 `lm`，每名玩家的值为 `from,to`；不存在的坐标以 `-` 代替；White 在前。
`pc` 为 White、Black 顺序的两个无符号整数。每个 `ul` 值为 Annex A line ID
的四位或五位小写十六进制 bit set；White 在前。`ul` 记录 line ID，而不是这些
line 的 point union。`pc` 只在成功 place 后递增，remove 不递减。

## 6.6 状态一致性

ongoing 状态的 side 为 `w` 或 `b`、phase 为 `p` 或 `m`、outcome 为 `-`。
terminal 状态的 side 为 `-`、phase/action 为 `o`、obligations 为 `-`，并有
terminal outcome。

无 obligation 时 action 与 phase 匹配。obligation 非空时 action 为 `r`，side
等于所有 branch-head actor。

对每名玩家，live piece、delayed token 与 hand 之和不超过 manifest initial
count。delayed token 要求 delayed placing effect。每个声明的 semantic state
extension 都存在。

独立 ongoing stable MFEN 必须已经是所有不需要 repetition history 即可求值的
确定性转移的 fixed point。MSTATE origin 例外，因为 replay 会执行 origin
stabilization。

# 7 MFEN/1.0 与 MPK/1.0

## 7.1 MFEN 用途与语法

MFEN 是依赖 caller 提供的 ruleset context 的紧凑即时状态。它不携带 ruleset
identity、digest、history、claim audit 或 provenance。它是 **context-bound**，
不得宣称为可独立分享的语义 object。

```text
MFEN/1.0 <state-profile> <board> <side> <phase> <action>
<hands> <obligations> <no-progress> <primary-ply> <outcome>
[<extension> ...]
```

显示仅为可读性换行；实际记录是一个 logical line。

规范输出使用 Annex A point order、小写十六进制、最短整数、无 obligation 和
ongoing outcome 的 `-`、规范 branch order 和已排序 extension key。

语义验证需要已解析的 `(id, version, semanticDigest)` context。无 context 的
parser 只能执行 lexical 与 state-profile 检查。

## 7.2 MPK 用途与语法

MPK 是有意不完整的结构键。它省略 no-progress、primary-ply、repetition、
claim、offer、outcome 和 provenance。不得将其用作 resumable-state 或
decision-state key。

```text
MPK/1.0 <state-profile> <ruleset-id@version> <semanticDigest>
<key-profile> <board24> <side> <phase> <hands>
[<key-extension> ...]
```

semantic digest 紧跟 ruleset reference。缺少 digest、与 containing envelope
不一致，或 resolved manifest 产生另一 semantic digest，均为无效。

输入仅在 ongoing、stable、无 obligations、action 为 `p` 或 `m`，且 key
profile 理解每个 semantic extension 时 eligible。不得静默省略未知 adjudication
state。

`structural-d4-v1` 应用 Annex A 的八个 D4 transform。
`structural-aut16-v1` 先应用这八个，再应用每个与 outer/inner ring exchange
的组合。Aut16 eligibility 还要求精确 semantic digest 与 transform profile 的
有效 MIFINV declaration。

对每个 transform，变换 board、`lm`、`ul` 以及每个已注册 coordinate/line
extension；保留 player-bound scalar；序列化完整 candidate；选取 US-ASCII
字节字典序最小者。相同值时选最低 transform ordinal。

# 8 公共 ruleset envelope 与 MIFPOS/1.0

## 8.1 Ruleset envelope

ruleset envelope 恰好具有以下公共成员：

| 成员 | 类型 | 要求 |
|---|---|---|
| `mode` | string | `portable` 或 `reference` |
| `id` | identifier | 必需 |
| `version` | 正整数 | 必需 |
| `semanticDigest` | digest | 必需 |
| `documentDigest` | digest | portable 必需；reference 可选 |
| `manifest` | MRS object | portable 必需；reference 禁止 |

portable validation 验证 manifest ID/version、semantic projection、semantic
digest、完整 JCS document digest 和 MRS validity。

reference resolution 使用 `(id, version, semanticDigest)`。若存在
`documentDigest`，resolved document 也必须匹配。resolver 由 caller 本地
提供；解析绝不自动访问网络。

## 8.2 MIFPOS 闭合 object

MIFPOS 恰好包含：

| 成员 | 类型 |
|---|---|
| `format` | `MIFPOS/1.0` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | `mill24-state-v1` |
| `position` | canonical MFEN string |
| `ruleset` | ruleset envelope |
| `annotations` | 可选非语义 object |
| `extensions` | 可选语义 extension array |

embedded profile 必须匹配 `stateProfile`。通用 export、copy、QR 与 share
操作默认 portable mode。reference mode 必须由 caller 显式选择。

MIFPOS 不包含 event history，也不替代 MSTATE、resumption state 或 decision
state。

# 9 MSTATE/1.0

## 9.1 顶层 object

MSTATE 恰好包含：

| 成员 | 类型 |
|---|---|
| `format` | `MSTATE/1.0` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | `mill24-state-v1` |
| `ruleset` | ruleset envelope |
| `origin` | canonical MFEN |
| `events` | ordered event array |
| `current` | canonical MFEN replay checkpoint |
| `repetitionHistory` | ordered active window |
| `preOriginClaims` | ordered claim-audit seed |
| `claims` | ordered claim/offer audit |
| `annotations` | 可选非语义 object |
| `extensions` | 可选语义 extension array |

训练数据、archive、save/export/share API 和跨项目交换默认 portable。
reference 是显式的存储优化。

MSTATE 既不包含 resumption/decision object，也不包含 resumptionDigest 或
decisionDigest cache member。这些身份按第 12 章派生；consumer 不需要在
embedded cache 与 replayed authority 之间选择。

## 9.2 Event

每个 event 包含 `seq`、`actor`、`type`、可选 `annotations`、可选
`extensions`，以及仅由该 type 允许的成员。sequence 是从 1 开始的连续整数，
array order 等于 sequence order。

标准 event 为：

| Type | Actor | 附加成员 |
|---|---|---|
| `place` | current side | `at`；可选非默认 `interventionLine` |
| `move` | current side | `from`、`to`；可选非默认 `interventionLine` |
| `remove` | obligation head actor | structured `target` |
| `offer-draw` | current side | 无 |
| `accept-draw` | non-offerer | `offerEventSeq` |
| `decline-draw` | non-offerer | `offerEventSeq` |
| `withdraw-draw` | offerer | `offerEventSeq` |
| `claim-draw` | current side | `reason`：`no-progress` 或 `repetition` |
| `resign` | `w` 或 `b` | 无 |
| `adjudicate` | `system` | `result`、`reason`、`authority` |

board remove target 恰好是
`{"zone":"board","at":<coordinate>}`。hand target 恰好是
`{"zone":"hand","player":"w|b"}`。

Place 与 move 在成功 mutation 后将 primary-ply 递增一次。每次 hand 或 board
removal 继续是独立 event。

Draw negotiation 不改变 gameplay state。最多一个 offer 处于 open。accept、
decline、withdraw 引用精确的 open event；pre-origin open offer 使用保留的
`offerEventSeq=0`。

`system` 只用于 adjudication。未知 semantic event extension 必须由 MRS 授权
且实现其 profile。

## 9.3 Repetition history

每个 entry 包含：

| 成员 | 要求 |
|---|---|
| `source` | `pre-origin`、`origin` 或 `event` |
| `eventSeq` | 仅 `event` 时必需 |
| `key` | `repetition-observation-v1` object |

开头的 pre-origin entry 按时间顺序排列，且位于 origin/event entry 之前。
只有所选 observation profile 适用时，origin stabilization 才增加 origin
observation。event observation 引用关闭该 primary sequence 的最后 event。

## 9.4 Claim audit

Pre-origin claim seed 包含 actor、`kind=draw-offer` 和 offer status。最多一个
seed 可为 open。

Audit record 包含 source、actor、event-sourced 时的 eventSeq、kind
`draw-offer` 或 `draw-claim`、status，以及后续 event 解决该 record 时的
resolvedEventSeq。Offer status 为 `open`、`accepted`、`declined`、
`withdrawn` 或 `expired`；有效 draw claim 为 `accepted`。

Event record 按 eventSeq 排序。Claim right 是派生状态，不是 audit event。

## 9.5 Replay

replayer 验证 JSON 和 ruleset，解析 origin，设置 pre-origin repetition 与
claim seed，执行 origin stabilization，应用每个 event 和确定性转移，然后
比较 canonical current、repetition history 与 claim audit。

mismatch code 为 `checkpoint-mismatch`、`repetition-history-mismatch` 和
`claims-mismatch`。conforming replay 绝不自动修复 mismatch。

# 10 MRS/1.0 与 digest domain

## 10.1 闭合 manifest

MRS 是 finite-mechanism manifest，不是通用规则语言。

必需成员为：

| 成员 | 类型 |
|---|---|
| `format` | `MRS/1.0` |
| `id` | identifier |
| `version` | 正整数 |
| `title` | string |
| `status` | `fixture`、`experimental`、`registered` 或 `deprecated` |
| `semanticsProfile` | `mif-finite-rules-v3` |
| `topology` | registered topology |
| `pieces` | material object |
| `turn` | initial/boundary object |
| `flying` | flying object |
| `placing` | placing-regime object |
| `mills` | mill object |
| `captures` | capture object |
| `boardFull` | board-full object |
| `stalemate` | stalemate object |
| `draw` | draw object |
| `semanticState` | sorted unique feature array |

可选成员为非空 `description`、`annotations` 和 `extensions`。未知成员无效。

`pieces`、`turn`、`flying`、`mills`、`captures`、`stalemate` 和
`semanticState` 保留以下有限形状和值含义。

## 10.2 Material、turn 与 placing

`topology` 为 `mill24-orthogonal-v1` 或 `mill24-diagonal-v1`。

`pieces` 包含正整数 `white`、`black`、`minimumLive`。`minimumLive` 不超过
任何一方的 initial count。

`turn` 包含 `initial`（`w` 或 `b`）与 `placingEndActivePlayer`（`w`、`b`
或 `retain`）。

`flying` 包含 Boolean `enabled` 和正整数 `maximumLive`。

启用 flying 时，phase-m 玩家在 live piece 不超过 `maximumLive` 时可移动到
任意空点。禁用时，MRS 文档仍要求 `maximumLive`，但它在语义上 inert，并由
10.7 semantic projection 去除。

`placing` 包含：

- Boolean `movementAllowed`；
- `earlyStop`，含 `emptyPoints` 和
  `boundary=after-unobligated-place-v1`；
- `noLegalPrimaryAction`，值为 `apply-board-full`、`loss` 或 `draw`。

early-stop point 为零时禁用 early stop。

`apply-board-full` 要求 `boardFull.action` 不是 `disabled`，并且在所选
extension profile 下，每个可达 trigger 都满足 full-board predicate。

## 10.3 Mills 与 captures

`mills` 包含：

- `placingEffect`：`remove-opponent-board`、
  `remove-opponent-hand-change`、`remove-opponent-hand-retain`、
  `opponent-remove-own-board`、`mark-opponent-board-until-moving` 或
  `remove-by-current-mill-count-at-placing-end`；
- `movingEffect=remove-opponent-board`；
- `removalMultiplicity`：`one-per-primary` 或 `one-per-new-line`；
- `targetProtection`：`outside-mill-first` 或 `all-opponent`；
- `lineReuse`：`unlimited` 或 `once-per-player`；
- `reverseReformation`：`allowed` 或 `prohibit-immediate`；
- `delayedClearBoundary=on-enter-moving-v1`。

`captures` 包含 `resolution=target-commits-v1` 和 `custodian`、
`intervention`、`leap`。每个 mechanism 包含 Boolean `enabled`；含 Boolean
`squareEdges`、`cross`、`diagonal` 的 `lines`；由 `placing` 或 `moving` 组成的
sorted unique `phases`；以及正整数或 null 的 `maximumOwnLivePieces`。

禁用 capture mechanism 在 MRS wire document 中仍保留这些成员，但除
`enabled` 外均语义 inert。对 custodian 和 intervention，
`maximumOwnLivePieces` 仅在 phase m 适用；对 leap，则在列出的每个 phase
适用。Null 表示无 material limit。在 `mill24-orthogonal-v1` 下，即使选择，
diagonal line family 仍为空。

## 10.4 Board-full 与 stalemate

`boardFull.action` 为：

- `disabled`；
- `white-loses`；
- `white-then-black-remove`；
- `black-then-white-remove`；
- `active-player-removes`；
- `draw`。

这些效果绑定固定颜色，不依赖 `turn.initial`。

`stalemate` 包含 `action` 和
`boardRemovalTargets=adjacent-opponent`。Action 为 `loss`、
`change-player`、`remove-and-retain`、`remove-and-change`、`draw` 或
`both-remove`。

## 10.5 Draw mechanism

`draw` 包含 `noProgress`、`repetition`、`offers` 和 `claimRights`。

`noProgress` 包含非负整数 `normalLimit`、`endgameLimit`，
`endgamePredicate`（`none` 或 `either-player-live-equals-3`），`mode`
（`automatic` 或 `claim`），sorted unique `countedPrimaryActions`，sorted
unique `resetEvents`，以及
`evaluationBoundary=stable-after-primary-sequence-v1`。

`countedPrimaryActions` 是 `move`、`place` 的子集。每个 `resetEvents` 数组是
`board-remove`、`hand-remove`、`mill-formation`、`place` 的子集。物理 event
reset 仅在 mutation 成功后发生。至少一个 usable new line 被检测到时发生
`mill-formation`，即使其 alternative obligation branch 最终未被选择。

`repetition` 包含：

- `count`，为零或至少 2；
- `mode`，`automatic` 或 `claim`；
- `observation`，`stable-moving-v1` 或
  `stable-primary-decision-v1`；
- `projection=repetition-observation-v1`；
- `summary=reset-count-smt-v1`；
- sorted unique `resetEvents`。

Count 为零时禁用 observation 与 decision repetition summary。

`offers.expiry` 为 `explicit-only` 或 `on-opponent-primary-action`。

`claimRights.profile` 为 `stable-claim-rights-v1`。

`draw` 及其每个 nested object 均为闭合。`offers` 只含 `expiry`；
`claimRights` 只含 `profile`。

## 10.6 Semantic state 与一致性

支持的 feature 为 `last-mill`→`lm`、`placement-count`→`pc`、
`used-lines`→`ul`。`once-per-player` 要求 used-lines；
`prohibit-immediate` 要求 last-mill。

Manifest set array 按 US-ASCII 排序且唯一。启用 capture mechanism 时至少选择
一个适用的非空 line family。禁用 repetition 时 count 为零。
`endgamePredicate=none` 要求 endgameLimit 为零。

完整 MRS set-array 分类为：

| 数组 | 含义 | 规范要求 |
|---|---|---|
| capture `phases` | set | unique，US-ASCII 升序 |
| no-progress `countedPrimaryActions` | set | unique，US-ASCII 升序 |
| no-progress/repetition `resetEvents` | set | unique，US-ASCII 升序 |
| `semanticState` | set | unique，US-ASCII 升序 |
| `extensions` | profile-keyed set | profile 唯一，按 profile US-ASCII 升序 |

启用 flying 时 `maximumLive >= minimumLive`。
`opponent-remove-own-board` 不得与 phase p 启用的 capture mechanism 组合。
delayed marking 要求 `on-enter-moving-v1`。启用 capture 时至少选择一个非空
line family。`apply-board-full` 必须满足 10.2 的 reachability condition。
这些是 manifest-consistency requirement，不是 runtime repair hint。

## 10.7 Semantic projection

`mrs-semantic-v1` 是闭合 JCS object，必需成员为
`profile=mrs-semantic-v1`。它包含 `semanticsProfile`、`topology`、
`pieces`、`turn`、`flying`、`placing`、`mills`、`captures`、
`boardFull`、`stalemate`、`draw` 与 `semanticState`。仅当 manifest 的
semantic extension array 非空时才包含 `extensions`。

它排除 format、id、version、title、status、description 与 annotations。

| MRS 成员 | Projection 处理 |
|---|---|
| synthetic `profile` | 包含为 `mrs-semantic-v1` |
| `format`, `id`, `version` | 排除 |
| `title`, `status`, `description`, `annotations` | 排除 |
| `semanticsProfile`, `topology`, `pieces`, `turn` | 原样包含 |
| `flying` | 包含，并按下文折叠禁用形态 |
| `placing` | 包含，并按下文折叠禁用 early stop |
| `mills` | 原样包含 |
| `captures` | 包含，并按下文折叠每个禁用 mechanism |
| `boardFull`, `stalemate` | 原样包含 |
| `draw` | 包含，并按下文折叠禁用 counter |
| `semanticState` | 包含 sorted unique array |
| `extensions` | 非空时包含 sorted array；未知 profile 拒绝 |

“原样包含”表示在 MRS validation 后复制完整闭合值；JCS 决定 object member
字节顺序，10.6 的 array classification 决定 set order。未列入本表的 MRS
member 不得进入 projection。

JCS 之前：

- 禁用 flying 恰好变为 `{"enabled":false}`；
- 禁用 early stop 恰好变为 `{"emptyPoints":0}`；
- 每个禁用 capture 恰好变为 `{"enabled":false}`；
- 两个 no-progress limit 均为零时恰好变为 `{"enabled":false}`；
- 禁用 repetition 恰好变为 `{"count":0}`；
- 所有启用 mechanism 保留每个语义成员及规范 array order。

projection 保留 `placing.noLegalPrimaryAction`、`draw.offers` 和
`draw.claimRights`；它们均不由其他 mechanism 禁用。projection 必须从上述
成员构造，不能从未知 MRS object 中删除 blacklist。未知 projection 或
extension profile 时，在产生 digest 前失败。

`semanticDigest` 是上述 JCS UTF-8 bytes 的 SHA-256。
`documentDigest` 是完整 MRS JCS bytes 的 SHA-256。任何 digest 成员都不插入
任一输入。

# 11 `mif-finite-rules-v3` 转移

## 11.1 初始状态与 primary validation

正常初始状态具有空 board、manifest hands、side 为 `turn.initial`、
phase/action 为 `p`、空 obligations、零 counter、ongoing outcome，以及归零的
必需 semantic state。

Place 要求 action `p`、actor hand 大于零且 target 为空。Move 要求 action
`m`，或 action `p` 且 movementAllowed；actor live source；空 destination；
除非 flying 或 leap 适用，否则要求 adjacency。成功 mutation 后
primary-ply 递增。

## 11.2 Trigger 与 branch order

primary action 后依次检测 leap、usable new mill、intervention、custodian。
legal leap branch 是 exclusive，但 mill formation 仍更新 semantic state 和
no-progress reset。

New mill 包含 destination，由 actor live piece 组成，且不被 used-line policy
排除。Mill multiplicity 为每个 primary 一次，或每个 usable new line 一次。

普通 `outside-mill-first` target：若存在不在完整 mill 中的 opponent live
piece，则仅选这些；否则选全部 opponent live piece。

Custodian 夹住 opponent middle piece。Intervention 占据两个 opponent endpoint
之间的 middle，并选择 event 显式命名的 candidate；未命名时选 line-ID 最小
candidate。Leap 从 endpoint 越过 opponent middle 移至另一 endpoint。

非空 branch 按 leap、intervention、custodian、mill 排序。第一个 remove target
提交到首个匹配 branch，丢弃其他 alternative branch。

## 11.3 Mill effect 与 obligation

board-removal count 以当前 target material 封顶。hand-first effect 创建显式
hand obligation，并可创建后续 board obligation。`opponent-remove-own-board`
把 actor 与 target owner 都改为 opponent。Delayed removal 将被选 live token
变为其 owner 的小写 marker。current-mill-count effect 等待 global placing
boundary。

解决 remove 时，丢弃未选择 branch，应用 mutation，递减 remaining，执行已
配置 reset 和立即 minimum material，重新计算 target，提升下一 obligation；
queue 为空时重新开始 stable processing。

## 11.4 Phase synchronization

global placing boundary 之前，有 hand piece 的 actor phase 为 `p`；没有 hand
piece 的 actor phase 为 `m`，即使 opponent 仍有 hand。MovementAllowed 还允许
action 为 `p` 时移动。

双方 hands 为零，或 early stop 将它们设为零时进入 global boundary。此时
phase 设为 `m`，清除所有 delayed token 为 empty，根据
placingEndActivePlayer 选择 side，并求值 deferred mill-count obligation。

## 11.5 Board-full、material 与 stalemate

每个 ongoing stable boundary 若无 empty point，均执行 board-full evaluation。
`white-loses` 使 Black 获胜。两个 fixed-colour removal action 按其名称生成
顺序：`white-then-black-remove` 后 White active，
`black-then-white-remove` 后 Black active。`active-player-removes` remove 一枚
opponent piece 后切换 side。

每次 removal 后和 stable boundary 都检查：某玩家 live+hand 低于 minimum 时
落败；双方同时不足则 draw。

phase-m stalemate 在 flying 之后求值。Loss/draw terminal。
change-player 重启一次；若第二名 moving player 也 stuck，则 draw。Removal
variant 使用 adjacent opponent target，不应用 mill protection。

## 11.6 Phase-p 无合法 primary action

在 ongoing stable phase-p boundary，判断 active player 是否有合法 place 或
允许的 move。若没有：

- `apply-board-full` 执行配置的 board-full effect；
- `loss` 使 opponent 以 `no-legal-primary-action` 获胜；
- `draw` 以该 reason 平局。

状态不得在没有合法 primary action 时保持 ongoing。

## 11.7 Repetition、no-progress 与 claim

No-progress 在 primary sequence 后更新，只在 stable 时求值。automatic mode
到达所选 limit 时终局；claim mode 派生 right。

Repetition 只观察其 observation profile 选择的 boundary。
`stable-moving-v1` 观察 ongoing stable phase/action `m`。
`stable-primary-decision-v1` 观察每个 ongoing stable phase-p 或 phase-m
primary boundary。pending obligation 不被观察。

某 observation occurrence 达 threshold 时，automatic mode 终局，claim mode
派生 claim right。

Claim right 仅在全部确定性处理到达 ongoing stable primary boundary 后产生。
它属于 side，包含按规范顺序排列、当前精确满足的 reason。只要 gameplay
boundary 不变，offer、decline、withdraw 不消耗它。

right 在任何成功 place、move 或 remove 之前立即失效。right 不进入 pending
removal。obligation pending 时 claim-draw 无效。有效 claim 消耗 right 并终局。

## 11.8 Stable-boundary 优先级

每当 obligation 清空，或 primary action 没有产生 obligation，按下列顺序
执行；遇到首个 terminal result 或 non-empty obligation 时停止或暂停：

1. 进入 global placing boundary 并清除 delayed token；
2. 生成 deferred mill-count obligation；
3. 求值 board full；
4. 求值双方 minimum material；
5. 求值 phase-p no-legal-primary-action；
6. 求值 phase-m stalemate；
7. 执行 repetition observation 与 automatic repetition；
8. 求值 automatic no-progress；
9. 派生 current claim rights；
10. 依据 phase finalize action。

Origin stabilization 在安装 history 和 claim seed 后使用同一 pipeline。

## 11.9 Terminal normalization

terminal state 将 phase/action 设为 `o`、side 和 obligations 设为 `-`；保留
post-event board、hands、counter、semantic state；除已接受 agreement 外令
open offer 过期；并设置恰好一个 registered outcome reason。

# 12 状态身份

## 12.1 Repetition observation

`repetition-observation-v1` object 恰好包含：

| 成员 | 类型或值 |
|---|---|
| `profile` | `repetition-observation-v1` |
| `stateProfile` | `mill24-state-v1` |
| `semanticDigest` | rules semantics digest |
| `board` | canonical MFEN board field |
| `side` | `w` 或 `b` |
| `phase` | `p` 或 `m` |
| `action` | 匹配的 primary action `p` 或 `m` |
| `hands` | `[white,black]` |
| `semantic` | 下述闭合 object |

`semantic` 将每个 MRS-declared semantic-state extension key 映射到其 canonical
MFEN string value，并包含所选 ruleset extension profile 要求的每个已注册
per-state semantic extension projection。未知的必需 state semantics 使
observation production fail closed。

它排除 no-progress、primary-ply、outcome、offer、claim、audit、ruleset
id/version 与 publication metadata。

observation digest 是其 JCS UTF-8 bytes 的 SHA-256。

## 12.2 Resumption state

`resumption-state-v1` object 恰好包含：

| 成员 | 含义 |
|---|---|
| `profile` | `resumption-state-v1` |
| `positionFormat` | `MFEN/1.0` |
| `stateProfile` | state profile |
| `semanticDigest` | rules semantics |
| `current` | 完整 canonical MFEN |
| `replayPrefixDigest` | 下文定义的 digest |
| `lastEventSeq` | 无 event 时为零，否则为最后 seq |
| `repetitionHistory` | 含 provenance 的完整有序 active window |
| `claims` | 完整 claim/offer audit |
| `openOffer` | raw source/actor/offerEventSeq object 或 null |
| `claimRights` | current rights object 或 null |
| `extensions` | 可选非空 resumption semantic extensions |

可选 `extensions` 遵循 5.5，空时省略。每个已实现 extension profile 定义其
精确 resumption projection。

replay-prefix object 不嵌入 resumption object。它恰好包含 `origin`、
`preOriginRepetition`、`preOriginClaims` 与 `events`。
`preOriginRepetition` 是从 MSTATE repetitionHistory 复制的开头
`source=pre-origin` prefix；其他值在不丢失 raw wire reference 的情况下复制。
`replayPrefixDigest` 是此 object JCS bytes 的 SHA-256。

非 null openOffer object 恰好包含 `source`、`actor`、`offerEventSeq`。source
为 sequence 0 的 `pre-origin`，或 positive sequence 的 `event`。Actor 是
offerer。非 null claimRights object 恰好包含 `actor` 与 `reasons`；reasons
非空、唯一，并按 `no-progress`、`repetition` 排序。

`resumptionDigest` 是 resumption object JCS bytes 的 SHA-256；它与 object
并列返回，不插入 object。无法确定完整 active repetition window、replay
prefix、claim audit 或 raw open-offer reference 的 producer 不得输出此
profile，并报告 `insufficient-resumption-history`。

## 12.3 Decision state

`decision-state-v1` object 恰好包含：

| 成员 | 含义 |
|---|---|
| `profile` | `decision-state-v1` |
| `stateProfile` | state profile |
| `semanticDigest` | rules semantics |
| `board` | canonical MFEN board field |
| `side` | current side |
| `phase`, `action` | current value |
| `hands` | `[white,black]` |
| `obligations` | canonical MFEN obligation field |
| `noProgress` | normalized integer 或 null |
| `outcome` | canonical MFEN outcome field |
| `semantic` | declared semantic state |
| `repetitionSummary` | summary object 或 null |
| `openOffer` | semantic operations 或 null |
| `claimRights` | current rights 或 null |
| `extensions` | 可选非空 decision semantic extensions |

它排除 primary-ply、event sequence value、history provenance、closed audit、
documentDigest、title、status、annotations 与 experiment limit。

两个 no-progress limit 均为零时，noProgress 为 null。否则：

```text
L = max({normalLimit if non-zero} union {endgameLimit if non-zero})
noProgress = min(current no-progress, L)
```

max 的输入集合非空。即使 endgame predicate 当前不成立，仍包含启用的
endgame limit：material 以后可能进入或离开该 predicate，因此封顶值保留所有
未来转移，同时合并大于等于最大 threshold 的值。

`semantic` 与 12.1 具有相同 base shape，并额外包含任何已注册、
decision-relevant state projection。可选 `extensions` 遵循 5.5；extension
profile 定义 decision projection，并可省略只与 resumption 有关的数据。

非 null openOffer 恰好包含 `offerer` 与 `available`。`available` 恰好包含三个
`{actor,action}` object：offerer 可 `withdraw`；另一方可 `accept` 或
`decline`。entry 先按 actor identity（`w`、`b`），再按 action order
`accept`、`decline`、`withdraw` 排序。它排除 raw offerEventSeq；adapter 将
所选 operation 映射回 current resumption reference。

非 null claimRights object 使用 12.2 的精确形状。terminal state 的 openOffer
和 claimRights 均为 null，并保留 normalized outcome。即使实现当前的 move
generator 不读取某成员，任何所列成员改变都改变 decision identity。

## 12.4 Sparse Merkle repetition summary

`reset-count-smt-v1` 是固定 256 层 sparse binary Merkle tree。
observation-digest bit 从 most-significant 到 least-significant 选择 left=0 或
right=1。

以下 SHA-256 输入均为 raw octet：

- empty leaf：`SHA256(0x00)`；
- populated leaf：
  `SHA256(0x01 || observationDigest32 || uint64be(cappedCount))`；
- branch：`SHA256(0x02 || left32 || right32)`。

定义 `E[0]=SHA256(0x00)`，并对 h 从 0 到 255 定义
`E[h+1]=SHA256(0x02 || E[h] || E[h])`。`E[256]` 是 canonical empty root。
populated observation leaf 在 256-bit path 上替换 `E[0]`，其 ancestor 由
每层 sibling hash 自底向上重新计算。

map entry 仅在 occurrence count 为正时存在。uint64 big-endian encoding 之前，
count 以 manifest repetition threshold 封顶。append observation 将其旧 count
递增；已配置 repetition reset 丢弃全部 entry 并选择 `E[256]`。两个不相等的
canonical observation 若产生相同 observation digest，是 integrity failure，
不得合并为同一 entry。

decision member 恰好为
`{"profile":"reset-count-smt-v1","root":<digest>}`。禁用 repetition 时为
null。materialized map 只能出现在被排除的 diagnostic annotations 中。`root`
使用 5.4 lexical digest form，其 hexadecimal payload 是 raw 32-byte tree root。

`decisionDigest` 是 decision-state JCS bytes 的 SHA-256，并与 object 并列返回。
更新一个 repetition key 只改变固定 256 个 branch，不重新 hash ordered
history。

## 12.5 Experiment identity

max ply、rollout limit、truncation policy 等训练限制编码在应用定义、已版本化的
I-JSON experiment object 中。`experimentDigest` 是其 JCS SHA-256。training
identity 绑定 suite、semantic、experiment 与 decision digest。

# 13 辅助 JSON wire 格式

## 13.1 MIFDIAG/1.0

envelope 是闭合 object：

| 成员 | 要求 |
|---|---|
| `format` | 必需 `MIFDIAG/1.0` |
| `errors` | 必需的非空 ordered error array |
| `annotations` | 可选非语义 object |

每个 error 均为闭合，包含必需 string `category` 与 identifier `code`，并可
包含：

- `instancePath`，RFC 6901 JSON Pointer；
- `textOffset`，一个闭合 object，含非负整数 `start`（inclusive）和 `end`
  （exclusive）UTF-8 byte offset，且 start 不大于 end；
- 非负整数 `eventSeq`；
- 有界 I-JSON `expected` 与 `actual`；
- `resourceLimit`，一个闭合 object，含 string `name`、非负整数 `limit` 和
  非负整数 `actual`；
- 非规范性 `message`。

Error 按 16.1 的 validation phase 排序。同一 phase 内按 `instancePath`、text
start、eventSeq、code 排序；无 location 排在有 location 之后。consumer 使用
category/code，绝不解析 message。

Category 为 `syntax`、`canonical`、`unsupported`、`integrity`、
`inconsistent`、`ineligible`、`replay`、`conversion`、`resource` 与
`unreachable`。

## 13.2 MIFCAP/1.0

MIFCAP 闭合并包含：

| 成员 | 形状 |
|---|---|
| `format` | 必需 `MIFCAP/1.0` |
| `implementation` | 必需 `{name,version}` 非空 string |
| `suites` | 必需 sorted unique digest array |
| `classes` | 必需 sorted `{id,level}` array |
| `formats` | 必需 sorted `{id,read,write}` array |
| `profiles` | 必需的下述闭合 profile-array object |
| `rulesets` | 必需 sorted ruleset support array |
| `invarianceDeclarations` | 必需 sorted invariance support array |
| `conversions` | 必需 sorted conversion support array |
| `resourceLimits` | 必需 sorted `{name,limit}` array |
| `testedCorpora` | 必需 sorted corpus evidence array |
| `annotations` | 可选非语义 object |

Support level 为 `none`、`experimental`、`implemented` 或 `tested`。read 与
write 使用独立 support level；class entry 使用同一组 level。Profiles 恰好
包含以下 sorted unique array：`semantics`、`semanticProjection`、`state`、`key`、
`repetitionProjection`、`observation`、`repetitionSummary`、`resumption`、
`decision`、`claimLifecycle`、`mpkBinding`、`transform`、`logicalTurn` 与
`placingLiveness`。

ruleset record 恰好包含 `id`、`version`、`semanticDigest`、可选
`documentDigest` 和 `level`。invariance record 恰好包含 `semanticDigest`、
`transformProfile`、`documentDigest` 和 `level`。conversion record 恰好包含
`sourceFormat`、`targetFormat` 和按 13.3 status order 排列的非空 `statuses`
array。tested-corpus record 恰好包含 `digest` 和 sorted unique `classes`
array。

数组按其自然第一 identity 排序：id；profile string；ruleset
`(id,version,semanticDigest)`；invariance
`(semanticDigest,transformProfile)`；conversion
`(sourceFormat,targetFormat)`；resource name；或 corpus digest。空数组仍须
存在，因为 absence 会使 capability scope 不明确。capability 是声明，不是
证明。

## 13.3 MIFCONV/1.0

MIFCONV 闭合，包含必需 `format=MIFCONV/1.0`、`sourceFormat`、
`targetFormat`、`status` 与 `omitted`；允许可选 `output`、`diagnostics`、
`annotations`。source/target format 是精确 format signature。Output 是 target
wire value。Diagnostics 是完整 MIFDIAG/1.0 object。

`omitted` 是闭合 `{instancePath,reason}` object 的 ordered array。
`instancePath` 是指向 JSON source 的 JSON Pointer；非 JSON source 的整体使用
empty string。reason 是 identifier。entry 先按 instancePath、再按 reason
排序。

Status 恰好为 `lossless`、`lossy-history`、`lossy-semantic-state`、
`requires-ruleset-resolution` 或 `unrepresentable-under-profile`。

`lossless` 要求 output 和空 omitted array。两个 lossy status 要求 output、
caller 显式接受、非空 omitted array。requires/unrepresentable 两个 status
禁止 output。失败转换必须有 diagnostics；成功转换可在其中带 warning。

## 13.4 MIFINV/1.0

MIFINV 闭合并包含：

| 成员 | 要求 |
|---|---|
| `format` | `MIFINV/1.0` |
| `profile` | `transform-invariance-v1` |
| `semanticDigest` | 精确 MRS semantic digest |
| `stateProfile` | 精确 state profile |
| `transformProfile` | 精确 transform profile |
| `transforms` | 按 Annex A ordinal order 的非空 unique transform ID |
| `extensionTreatments` | 下述 sorted closed record |
| `documentDigest` | declaration document digest |
| `annotations` | 可选非语义 object |

每个 extension-treatment record 恰好包含 `profile` 与 `treatmentProfile`，二者
均为 identifier，并按 profile 排序。treatment profile 完整定义 forward 与
inverse transform；未知 treatment fail closed。document digest 是移除且仅
移除 documentDigest member 后 JCS 的 SHA-256，因此 annotations 也进入。
declaration 只证明其精确 `(semanticDigest, transformProfile)` pair 与列出的
transform ID。

## 13.5 MIFTURN/1.0

MIFTURN 闭合，包含必需 `format=MIFTURN/1.0`、`profile=logical-turn-v1`、
`sourceResumptionDigest`、ordered `fragments` 与可选 annotations。fragment
均为闭合。

Fragment kind 为 `logical-turn`、`origin-obligation` 或
`origin-stabilization`。每个 fragment 包含 `kind`、ordered unique
`removeEventSeqs` 和 `status`（`complete` 或 `truncated`）。logical-turn
fragment 额外要求正整数 `primaryEventSeq`；origin kind 禁止该成员。sequence
array 保持 replay order。

obligation-free origin 确定性生成 board-full、stalemate 或 mill-count
obligation 时使用 origin-stabilization。不虚构 primary event。MSTATE 不增加
`causedBySeq`。

## 13.6 MIFSUITE/1.0 形状

未来 suite object 闭合并恰好包含：

| 成员 | 形状 |
|---|---|
| `format` | `MIFSUITE/1.0` |
| `id` | identifier |
| `components` | 下述闭合 component object |
| `profiles` | 下述闭合 profile selection object |
| `specifications` | 非空 sorted artifact record |
| `artifacts` | 下述闭合 artifact-category object |
| `rulesets` | sorted unique semantic-digest array |
| `invarianceDeclarations` | sorted unique MIFINV document-digest array |
| `compatibilityPolicy` | identifier |
| `mediaTypes` | sorted closed `{format,value}` record |
| `fileExtensions` | sorted closed `{format,value}` record |
| `releaseManifest` | 非空 string identifier 或 location |

Components 恰好包含 `mfen`、`mpk`、`mifpos`、`mstate`、`mrs`、
`diagnostics`、`capabilities`、`conversion`、`invariance` 与 `logicalTurn`，
每个值为其精确 format signature。Profiles 恰好包含 `semantics`、
`semanticProjection`、`state`、`key`、`repetitionProjection`、`observation`、
`repetitionSummary`、`resumption`、`decision`、`claimLifecycle`、
`mpkBinding`、`transform` 与 `logicalTurn`；每个值是非空 sorted unique
identifier array，但 singular `semantics`、`semanticProjection`、`state`、
`repetitionProjection`、`repetitionSummary`、`resumption`、`decision`、
`claimLifecycle`、`mpkBinding`、`transform`、`logicalTurn` 是 identifier
string。

每个 specification/artifact record 恰好包含 `id`、`sha256` 与可选
`commit`；specification record 要求 commit。`sha256` 使用 digest lexical form
并散列 raw file bytes。specification 按 id 排序。Artifacts 恰好包含名为
`registries`、`corpora`、`schemas`、`abnf`、`conversions`、`runners`、
`adapters` 的 array；每个 array 非空，且 adapters 至少包含两个独立实现的
entry。各数组按 artifact id 排序。media-type/extension record 按 format、
value 排序。

suite digest 是 suite JCS bytes 的 SHA-256，在 object 外部发布，不插入。
本合同不发布实际 suite object。

# 14 Full-state transform 与 logical turn

## 14.1 坐标转换

`mill24-full-state-v1` 变换 MFEN、MIFPOS、MSTATE、event、obligation、
repetition observation、resumption/decision state、logical turn、action、
principal variation、`lm`、`ul` 与 semantic extension 中每个
coordinate-bearing 或 line-bearing value。

player-bound scalar、counter、event seq、offer reference 保持含义。变换后的
MSTATE 在同一 semantic digest 下 replay 到变换后的 current。

非 null decision repetition root 不能仅凭 root 执行 coordinate transform。
transformer 必须取得对应 observation/count map；该 map 来自 source MSTATE、
resumption history 或已通过 integrity check 的 backing store。transformer 变换
每个 observation，合并相同 transformed digest，封顶 count，再重建 root。
没有这些 material 时，报告 `insufficient-transform-history`，且不输出变换后的
decision state。

## 14.2 等价性门槛

当每个 value 均有 registered transform 时可执行 coordinate conversion。
decision normalization、training/PUCT/tablebase merging 和 equivalent MPK
normalization 声明，额外要求精确 semantic digest 与 transform profile 的有效
MIFINV。

没有 declaration 时，geometry 本身不能建立 rules equivalence。

## 14.3 Logical-turn projection

按顺序 replay origin 与 event。place/move 开始 logical turn。将解决该 primary
sequence 因果生成 obligation 的每个后续 remove 与其关联，包括 stable-boundary
obligation。全部此类 obligation 与确定性处理完成后关闭。由该 primary
sequence 导致的 terminal result 仍是 complete logical turn。只有 source 在
consequent obligation 未解决时结束，或 independent terminal event 中断该
sequence，才标记 `truncated`。

origin 已有 obligation 时生成 origin-obligation fragment。obligation-free
origin 在 stabilization 时生成 obligation，则生成 origin-stabilization
fragment。Draw negotiation 保留在 MSTATE 中，不转换为 primary/removal
action。

# 15 规范性 0.4-to-1.0 转换

## 15.1 通则

转换在输出 1.0 前验证完整 0.4 source 与 ruleset。不得原地重新解释 source
bytes。repair 和 policy selection 必须是显式 MIFCONV result。

## 15.2 必需映射

| 0.4 construct | 1.0 行为 |
|---|---|
| `first-player-loses` | `white-loses` |
| `first-then-second-remove` | `white-then-black-remove` |
| `second-then-first-remove` | `black-then-white-remove` |
| `legal-state-v1` | resolved `repetition-observation-v1` |
| full-manifest digest | 仅 source document identity；重新计算两个 target digest |
| 含 manifest 的 MSTATE | portable envelope |
| 不含 manifest 的 MSTATE | reference envelope，或解析后 portable export |
| 无 resolvable manifest 的 MPK | `requires-ruleset-resolution` |

可达 placing state 可能无合法 primary action 的 0.4 manifest，需要显式 1.0
liveness policy。没有 policy 时为 `unrepresentable-under-profile`。选择
loss/draw/board-full，而 0.4 会保持 stuck 时，为 `lossy-semantic-state`。

`stable-moving-v1` 保留 moving-only 含义。改为
`stable-primary-decision-v1` 会改变 repetition semantics，要求显式 target
ruleset version。

## 15.3 强制拒绝

不得静默升级：

- 0.4 removal obligation pending 时执行的 claim-draw；
- 未知 semantic extension；
- ownerless delayed material；
- 缺失 per-player used-line history；
- MPK 或 identity 所需 ruleset semantics 缺失；
- 无 MIFINV 的 transform equivalence。

# 16 解析、错误、安全与 lifecycle

## 16.1 Validation order

依次验证 byte/resource limit、grammar/I-JSON、duplicate name、signature 与
canonical form、profile support、ruleset/digest、structural consistency、
semantic consistency、replay/checkpoint、可选 reachability。

后续 validation 不得重新解释前一阶段的 invalid token。

## 16.2 标准 error code

必需 code 包括：

`duplicate-member-after-unescape`、`duplicate-extension`、
`extension-order`、`integer-out-of-range`、`unsupported-profile`、
`manifest-missing`、
`manifest-conflict`、`semantic-digest-mismatch`、
`document-digest-mismatch`、`mpk-semantic-digest-missing`、
`transform-invariance-undeclared`、
`required-semantic-state-missing`、`remove-without-obligation`、
`side-obligation-actor-mismatch`、`obligation-target-mismatch`、
`claim-right-unavailable`、`claim-during-obligation`、
`insufficient-resumption-history`、`insufficient-transform-history`、
`repetition-observation-digest-collision`、
`no-legal-primary-action-policy-invalid`、`checkpoint-mismatch`、
`repetition-history-mismatch`、`claims-mismatch`、
`automatic-terminal-ongoing` 与 `unstabilized-boundary`。

## 16.3 安全与限制

解析绝不执行代码、加载库、打开 input 指定的 path、访问网络、安装 plugin 或
建立 publisher trust。

实现通过 MIFCAP 发布 limit。超过 limit 时产生 resource diagnostic，绝不产生
截断的 semantic state。

建议通用限制为：MFEN/MPK 4 KiB，MRS/MIFPOS 1 MiB，MSTATE 8 MiB，JSON
depth 64，100000 events，100000 repetition entries，256 text extensions。

## 16.4 1.x lifecycle

仅 metadata 的 MRS 变化产生新 documentDigest，不改变 semanticDigest。
gameplay 变化要求新 ruleset version 和 semantic digest。仅当现有 bytes 保持
含义时，additive syntax 才使用另行标识的 1.x signature/profile。

改变现有 canonical form、digest projection、required member、default
meaning、fail-closed behaviour 或 token meaning，必须升级到 2.0。

本 wire contract 不分配 media type、official extension、license grant 或
signature mechanism。最终 suite 绑定这些 release choice。

# Annex A（规范性）：topology 与 registry

## A.1 Point order

| Index | Coordinate | Index | Coordinate | Index | Coordinate |
|---:|---|---:|---|---:|---|
| 0 | a7 | 8 | b6 | 16 | c5 |
| 1 | d7 | 9 | d6 | 17 | d5 |
| 2 | g7 | 10 | f6 | 18 | e5 |
| 3 | g4 | 11 | f4 | 19 | e4 |
| 4 | g1 | 12 | f2 | 20 | e3 |
| 5 | d1 | 13 | d2 | 21 | d3 |
| 6 | a1 | 14 | b2 | 22 | c3 |
| 7 | a4 | 15 | b4 | 23 | c4 |

ring neighbour wrap。Orthogonal cross-ring edge 为
`d7-d6 d6-d5 g4-f4 f4-e4 d1-d2 d2-d3 a4-b4 b4-c4`。
diagonal topology 还包含
`a7-b6 b6-c5 g7-f6 f6-e5 g1-f2 f2-e3 a1-b2 b2-c3`。

## A.2 Line ID

| ID | Triple | ID | Triple |
|---:|---|---:|---|
| 0 | a7,d7,g7 | 10 | e3,d3,c3 |
| 1 | g7,g4,g1 | 11 | c3,c4,c5 |
| 2 | g1,d1,a1 | 12 | d7,d6,d5 |
| 3 | a1,a4,a7 | 13 | g4,f4,e4 |
| 4 | b6,d6,f6 | 14 | d1,d2,d3 |
| 5 | f6,f4,f2 | 15 | a4,b4,c4 |
| 6 | f2,d2,b2 | 16 | a7,b6,c5 |
| 7 | b2,b4,b6 | 17 | g7,f6,e5 |
| 8 | c5,d5,e5 | 18 | g1,f2,e3 |
| 9 | e5,e4,e3 | 19 | a1,b2,c3 |

orthogonal 使用 0–15；diagonal 使用 0–19。

## A.3 Transform order

| Ordinal | ID | Mapping |
|---:|---|---|
| 0 | i | (x,y)→(x,y) |
| 1 | r90ccw | (x,y)→(-y,x) |
| 2 | r180 | (x,y)→(-x,-y) |
| 3 | r90cw | (x,y)→(y,-x) |
| 4 | mirror-v | (x,y)→(-x,y) |
| 5 | mirror-h | (x,y)→(x,-y) |
| 6 | mirror-main | (x,y)→(y,x) |
| 7 | mirror-anti | (x,y)→(-y,-x) |

file a..g 映射到 -3..3，rank 1..7 映射到 -3..3。

outer/inner exchange pair 为
`a7-c5 d7-d5 g7-e5 g4-e4 g1-e3 d1-d3 a1-c3 a4-c4`；middle point 固定。

## A.4 Cause 与 outcome registry

Cause order 为 leap、intervention、custodian、mill、mill-count、stalemate、
board-full。

标准 outcome reason 为：

- `fewer-than-minimum`：win 或 draw；
- `no-legal-move`：win 或 draw；
- `no-legal-primary-action`：win 或 draw；
- `board-full`：win 或 draw；
- `no-progress`、`repetition`、`agreement`：draw；
- `resignation`：win；
- `adjudication`：win 或 draw。

# Annex B（规范性）：内联 ABNF

```abnf
mfen = %s"MFEN/1.0" SP state-profile SP board SP side
       SP phase SP action SP hands SP obligations SP no-progress
       SP primary-ply SP outcome *(SP extension)

mpk = %s"MPK/1.0" SP state-profile SP ruleset SP digest
      SP key-profile SP mpk-board SP player SP active-phase SP hands
      *(SP key-extension)

state-profile = identifier
key-profile = identifier
ruleset = identifier %s"@" positive-integer
digest = %s"sha256:" 64lc-hex

identifier = id-start *62id-character
id-start = lc-alpha / DIGIT
id-character = lc-alpha / DIGIT / %s"." / %s"-"
private-identifier = %s"x-" id-start *60id-character

board = ring %s"/" ring %s"/" ring
ring = 8piece
mpk-board = 24piece
piece = %s"W" / %s"B" / %s"." / %s"w" / %s"b"

side = player / %s"-"
player = %s"w" / %s"b"
phase = active-phase / %s"o"
active-phase = %s"p" / %s"m"
action = %s"p" / %s"m" / %s"r" / %s"o"

hands = uint %s"," uint
no-progress = uint
primary-ply = uint

obligations = %s"-" / obligation-branches
obligation-branches = obligation-branch *(%s"|" obligation-branch)
obligation-branch = obligation *(%s";" obligation)
obligation = player %s":" cause %s":" target-zone %s":" player
             %s":" positive-integer %s":" target-spec %s":" after

cause = %s"leap" / %s"intervention" / %s"custodian" /
        %s"mill" / %s"mill-count" / %s"stalemate" /
        %s"board-full"
target-zone = %s"b" / %s"h"
target-spec = hex24 / %s"-" / %s"~"
after = player / %s"q"

outcome = %s"-" / result %s":" reason
result = %s"w" / %s"b" / %s"d"
reason = standard-reason / private-identifier
standard-reason = %s"fewer-than-minimum" / %s"no-legal-move" /
                  %s"no-legal-primary-action" / %s"board-full" /
                  %s"no-progress" / %s"repetition" /
                  %s"agreement" / %s"resignation" /
                  %s"adjudication"

extension = extension-key %s"=" *value-character
key-extension = extension
extension-key = standard-extension-key / private-identifier
standard-extension-key = %s"lm" / %s"pc" / %s"ul"
value-character = %x21-3C / %x3E-7E

; Registered extension-value subgrammars. Semantic validation binds each
; standard key to its corresponding grammar.
lm-value = coord-or-dash %s"," coord-or-dash %s";"
           coord-or-dash %s"," coord-or-dash
pc-value = uint %s"," uint
ul-value = line-bitset %s"," line-bitset
line-bitset = 4lc-hex / 5lc-hex

hex24 = 6lc-hex
coord-or-dash = coord / %s"-"
coord = %s"a7" / %s"d7" / %s"g7" / %s"g4" /
        %s"g1" / %s"d1" / %s"a1" / %s"a4" /
        %s"b6" / %s"d6" / %s"f6" / %s"f4" /
        %s"f2" / %s"d2" / %s"b2" / %s"b4" /
        %s"c5" / %s"d5" / %s"e5" / %s"e4" /
        %s"e3" / %s"d3" / %s"c3" / %s"c4"

uint = %s"0" / positive-integer
positive-integer = nonzero-digit *DIGIT
nonzero-digit = %x31-39
lc-hex = DIGIT / %x61-66
lc-alpha = %x61-7A
```

# Annex C（规范性）：冻结示例

## C.1 初始玩家

C.2 manifest 的 `turn.initial` 为 `b`，其 canonical empty origin 为：

```text
MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -
```

仅将 `turn.initial` 改为 `w`，side field 改为 `w`；player identity 不会重命名。
在 `white-loses` 下，无论哪个 origin，后续 full-board terminal result 均为
`b:board-full`。

## C.2 Digest domain

以下是 fixture document D1 的完整 JCS form：

```json
{"boardFull":{"action":"disabled"},"captures":{"custodian":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"intervention":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"leap":{"enabled":false,"lines":{"cross":false,"diagonal":false,"squareEdges":false},"maximumOwnLivePieces":null,"phases":["moving"]},"resolution":"target-commits-v1"},"draw":{"claimRights":{"profile":"stable-claim-rights-v1"},"noProgress":{"countedPrimaryActions":["move"],"endgameLimit":0,"endgamePredicate":"none","evaluationBoundary":"stable-after-primary-sequence-v1","mode":"automatic","normalLimit":0,"resetEvents":["board-remove"]},"offers":{"expiry":"explicit-only"},"repetition":{"count":3,"mode":"claim","observation":"stable-primary-decision-v1","projection":"repetition-observation-v1","resetEvents":["board-remove"],"summary":"reset-count-smt-v1"}},"flying":{"enabled":true,"maximumLive":3},"format":"MRS/1.0","id":"example-morris","mills":{"delayedClearBoundary":"on-enter-moving-v1","lineReuse":"unlimited","movingEffect":"remove-opponent-board","placingEffect":"remove-opponent-board","removalMultiplicity":"one-per-primary","reverseReformation":"allowed","targetProtection":"outside-mill-first"},"pieces":{"black":9,"minimumLive":3,"white":9},"placing":{"earlyStop":{"boundary":"after-unobligated-place-v1","emptyPoints":0},"movementAllowed":false,"noLegalPrimaryAction":"loss"},"semanticState":[],"semanticsProfile":"mif-finite-rules-v3","stalemate":{"action":"loss","boardRemovalTargets":"adjacent-opponent"},"status":"fixture","title":"Example Morris","topology":"mill24-orthogonal-v1","turn":{"initial":"b","placingEndActivePlayer":"retain"},"version":1}
```

其完整 `mrs-semantic-v1` JCS projection 为：

```json
{"boardFull":{"action":"disabled"},"captures":{"custodian":{"enabled":false},"intervention":{"enabled":false},"leap":{"enabled":false},"resolution":"target-commits-v1"},"draw":{"claimRights":{"profile":"stable-claim-rights-v1"},"noProgress":{"enabled":false},"offers":{"expiry":"explicit-only"},"repetition":{"count":3,"mode":"claim","observation":"stable-primary-decision-v1","projection":"repetition-observation-v1","resetEvents":["board-remove"],"summary":"reset-count-smt-v1"}},"flying":{"enabled":true,"maximumLive":3},"mills":{"delayedClearBoundary":"on-enter-moving-v1","lineReuse":"unlimited","movingEffect":"remove-opponent-board","placingEffect":"remove-opponent-board","removalMultiplicity":"one-per-primary","reverseReformation":"allowed","targetProtection":"outside-mill-first"},"pieces":{"black":9,"minimumLive":3,"white":9},"placing":{"earlyStop":{"emptyPoints":0},"movementAllowed":false,"noLegalPrimaryAction":"loss"},"profile":"mrs-semantic-v1","semanticState":[],"semanticsProfile":"mif-finite-rules-v3","stalemate":{"action":"loss","boardRemovalTargets":"adjacent-opponent"},"topology":"mill24-orthogonal-v1","turn":{"initial":"b","placingEndActivePlayer":"retain"}}
```

预期 digest 为：

```text
semanticDigest = sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393
documentDigest(D1) = sha256:62479b6f40efb8ab478bab3d2b725647213604fcd3cc9cd4c1f69357535ae257
```

D2 是将 D1 中的 `"title":"Example Morris"` 精确替换为
`"title":"Example Morris (retitled)"`。D2 的 semanticDigest 不变，且：

```text
documentDigest(D2) = sha256:60b8f91214e2273a0f7eb411794ce3b133c61653b2199763ab555d90f042e6e4
```

改变 `placing.noLegalPrimaryAction` 会改变两个 digest。增加未知 semantic
extension 会产生 unsupported-profile error，不产生 digest。

## C.3 Decision 与 resumption

对 C.2 semantics 和 C.1 origin，origin observation digest、canonical empty
tree root 与 one-occurrence tree root 为：

```text
observationDigest = sha256:6adc3718c5b16999b2a75b444728656e9901b003b8ff641813d73b2cdcba1e4e
emptyRoot = sha256:e9fbf966ccdff764594a5e199e6aea0cc36034b46c8057cc3df88a088c20101a
oneOccurrenceRoot = sha256:3a08cdfcc2a0be8a7fd9277649ff0a2e2b30cb20b98d808f825594c9a31aa885
```

Black 打开 draw offer 后，decision object JCS 为：

```json
{"action":"p","board":"......../......../........","claimRights":null,"hands":[9,9],"noProgress":null,"obligations":"-","openOffer":{"available":[{"action":"accept","actor":"w"},{"action":"decline","actor":"w"},{"action":"withdraw","actor":"b"}],"offerer":"b"},"outcome":"-","phase":"p","profile":"decision-state-v1","repetitionSummary":{"profile":"reset-count-smt-v1","root":"sha256:3a08cdfcc2a0be8a7fd9277649ff0a2e2b30cb20b98d808f825594c9a31aa885"},"semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"}
```

其 decisionDigest 为
`sha256:f25cfb5dae617feba90fc1cbd48fb5d526727c8a3fad65910400a72a03657d19`。

History R1 在 sequence 1 只有一个 `offer-draw` event。History R2 有
`offer-draw(1)`、`withdraw-draw(2, offerEventSeq=1)`、`offer-draw(3)`。
二者 gameplay position、active repetition count 与 semantic offer operation
相同。其 resumption-object JCS 为：

```json
{"claimRights":null,"claims":[{"actor":"b","eventSeq":1,"kind":"draw-offer","source":"event","status":"open"}],"current":"MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -","lastEventSeq":1,"openOffer":{"actor":"b","offerEventSeq":1,"source":"event"},"positionFormat":"MFEN/1.0","profile":"resumption-state-v1","repetitionHistory":[{"key":{"action":"p","board":"......../......../........","hands":[9,9],"phase":"p","profile":"repetition-observation-v1","semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"},"source":"origin"}],"replayPrefixDigest":"sha256:0c3c604aa2b0f9e3407ddaca90e411755f5689066e68faf9f0e709a58857c151","semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","stateProfile":"mill24-state-v1"}
```

```json
{"claimRights":null,"claims":[{"actor":"b","eventSeq":1,"kind":"draw-offer","resolvedEventSeq":2,"source":"event","status":"withdrawn"},{"actor":"b","eventSeq":3,"kind":"draw-offer","source":"event","status":"open"}],"current":"MFEN/1.0 mill24-state-v1 ......../......../........ b p p 9,9 - 0 0 -","lastEventSeq":3,"openOffer":{"actor":"b","offerEventSeq":3,"source":"event"},"positionFormat":"MFEN/1.0","profile":"resumption-state-v1","repetitionHistory":[{"key":{"action":"p","board":"......../......../........","hands":[9,9],"phase":"p","profile":"repetition-observation-v1","semantic":{},"semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","side":"b","stateProfile":"mill24-state-v1"},"source":"origin"}],"replayPrefixDigest":"sha256:d8a8d2e595c1d37ed7f69bd9dee19039d52a346fbf7a1a28076ccf00b14e791a","semanticDigest":"sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393","stateProfile":"mill24-state-v1"}
```

二者 resumption digest 分别为
`sha256:1abb022db99a0959d00c90ca5ba6a946b99d183c8a811e01f242ef081bf5d5b3`
与
`sha256:2f2188fe6beb34042bcf201644f262d25552a5a6263d2ba0de024aa917a83657`。
因此 decisionDigest 相等，而 resumptionDigest 不等。

改变 side、合法 removal target、claim right、repetition root、相关
no-progress 或 outcome，均改变 decision state。

## C.4 MPK binding

C.1 position 的有效 structural key 为：

```text
MPK/1.0 mill24-state-v1 example-morris@1 sha256:224f7e368e322a4cc8c1225a025fb548d5b41eb096d34b7ae0543182d1aa9393 structural-d4-v1 ........................ b p 9,9
```

删除 digest 产生 `mpk-semantic-digest-missing`。将其替换为
`sha256:0000000000000000000000000000000000000000000000000000000000000000`
并解析 D1 时产生 `semantic-digest-mismatch`。即使在 semantic resolution
之前，修改后的 record 也不是同一个 textual key。

## C.5 Transform gate

在 Annex A `r90ccw` 下，`a7` 映射到 `a1`。一个 value 指定 absolute reward
point `a7` 的 registered semantic extension 因此可 coordinate-convert 为
`a1`。没有精确 C.2 semanticDigest 与 transform profile 的 MIFINV declaration
时，这两个 state 不适合 decision、training、PUCT、tablebase 或 Aut16
equivalence merging。

## C.6 Placing liveness

初始 material 为双方各 13、boardFull disabled、active White 时，下列 stable
input 没有合法 phase-p primary action：

```text
MFEN/1.0 mill24-state-v1 WBWBWBWB/BWBWBWBW/WBWBWBWB w p p 1,1 - 0 0 -
```

Policy loss 产生：

```text
MFEN/1.0 mill24-state-v1 WBWBWBWB/BWBWBWBW/WBWBWBWB - o o 1,1 - 0 0 b:no-legal-primary-action
```

Policy draw 改为产生 `d:no-legal-primary-action`。`apply-board-full` 与
boardFull disabled 组合是 manifest error。没有 policy 会原样输出 ongoing
input。

## C.7 Repetition scope

movementAllowed 为 true 时，从 board `W......./B......./........`、side/action
`w p`、双方 non-zero hands 开始。legal cycle `w:a7-a4`、`b:b6-b4`、
`w:a4-a7`、`b:b4-b6` 返回相同 phase-p decision observation。
`stable-primary-decision-v1` 统计这些 stable boundary；
`stable-moving-v1` 因 phase 始终为 p 而一个也不统计。Capability output 指明
所选 scope。

## C.8 Claim lifecycle

在具有 `{actor:"b",reasons:["repetition"]}` 的 stable boundary，event sequence
`offer-draw(1,b)`、`decline-draw(2,w,offerEventSeq=1)` 保持该 right 不变。
后续成功 place 或 move 在 mutation 前立即使其失效。若 action 产生 removal
obligation，则每个 remove 期间 claimRights 为 null；下一个 stable boundary
依据当时 counter 与 repetition root 派生新 object。obligation 期间的 claim
event 为 `claim-during-obligation`。

## C.9 Origin stabilization

obligation-free origin 确定性创建一个 obligation，且其 remove event 为 1 与 2
时，精确 fragment 为：

```json
{"kind":"origin-stabilization","removeEventSeqs":[1,2],"status":"complete"}
```

它没有 primaryEventSeq。origin 已携带 obligation 时使用
`origin-obligation`；两种情况均不虚构 primary event 或 `causedBySeq`。
