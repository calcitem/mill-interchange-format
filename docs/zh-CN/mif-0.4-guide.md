# MIF Community Working Draft 0.4 中文导读与讨论提要

**2026 年 7 月 26 日**

> 本文是英文规范的中文导读，不是独立的规范性文本。发生歧义时，以
> 仓库根目录 `mif-0.4.md` 的英文条文和 `conformance/`
> 机器可读语料为准。

## 1. 文档定位

0.4 在不可变的 0.3 基线
（`3f1ffc30ab8c838eaeae54102c37e20bdaa00c7a`）之后闭合状态机、replay
seed 和规范性语料冲突。签名仍是实验性的：

```text
MFEN/0.4
MPK/0.4
MSTATE/0.4
MRS/0.4
```

它是独立社区工作稿，不是 ISO、IEC、CEN、WMD 或任何赛事组织发布、
批准或认证的标准。

相对 0.3，0.4 的要点包括：

- 增加独立 `preOriginClaims`，不再用最终 `claims` 反向充当 replay seed；
- obligation 完成和 `change-player` 后统一同步新 actor 的 phase；
- pipeline 生成 obligation 时立即暂停，完成后从第 1 步重新执行；
- 为 mill-count、full-board、stalemate 的零目标定义封闭结果；
- stalemate 先于 repetition，重复观察只提交最终稳定状态；
- 普通 multiple removal 使用整个序列容量，而不是初始 target 快照；
- full-board 在 placing 阶段也可确定性处理；
- 双方同时低于 minimum 时判和；
- 独立 MFEN 必须是 deterministic fixed point；
- 任意非 accept-draw 的终局都会关闭 open offer。

## 2. 总体架构

0.4 继续保留 0.1/0.2/0.3 最重要的成果：不再用一种“Mill FEN”承担所有用途。

| 层次 | 解决的问题 | 不承担的职责 |
|---|---|---|
| MFEN | 当前这一刻的精确规则状态是什么 | 完整事件历史、重复历史 |
| MPK | 稳定局面应归入哪个结构分析键 | 无损存档、所有和棋权利 |
| MSTATE | 对局如何重放、恢复、核验声明 | 搜索引擎热路径键 |
| MRS | 同一规则集到底如何确定性执行 | 任意规则脚本或通用 DSL |

数据库键不等于无损存档；无损存档也不等于搜索键。这个边界在 0.2/0.3
中落实为三个独立 profile：

```text
ruleset       = 游戏规则语义
state-profile = 状态字段及其编码
key-profile   = MPK 投影和对称归一化
```

因此，将 D4 改成完整 16 个拓扑自同构，不需要把游戏规则从
`nmm@1` 升成 `nmm@2`。

## 3. MFEN/0.4 的核心形式

```text
MFEN/0.4 <state-profile> <ruleset> <board> <side> <phase> <action>
<hands> <obligations> <no-progress> <primary-ply> <outcome>
[<extension> ...]
```

推荐的公共状态 profile 是：

```text
mill24-state-v1
```

与 0.1 相比，最大的变化是：

- 删除 `ready` phase；
- 删除两个扁平 pending 计数；
- 删除无法关联上下文的全局 flags；
- 用结构化 obligation 分支直接保存执行者、原因、区域、目标所有者、
  剩余次数、目标集合和完成后的控制权。

## 4. 公共棋盘顺序

公共顺序固定为外圈—中圈—内圈：

```text
a7 d7 g7 g4 g1 d1 a1 a4 /
b6 d6 f6 f4 f2 d2 b2 b4 /
c5 d5 e5 e4 e3 d3 c3 c4
```

每圈从左上角开始顺时针，连续八个字符。它吸收了 NMM_LLM 已投入数据库
和训练流程的优点。

但规范明确声明：

- 这是 MIF 的互操作约定；
- WMD 资料支持 `a` 至 `g`、`1` 至 `7` 的坐标命名；
- 目前没有证据表明某个国际联合会或欧洲锦标赛规定了这一 0—23
  线性顺序。

因此不能把它包装成“国际联合会官方索引”。坐标资料入口见
[WMD 棋盘记法参考](https://muehlespieler.de/x_uebungen/index.php?page=begriffe_notation)。

## 5. 是否影响位运算和性能

不会要求引擎更改内部编号。

Sanmill 可以继续使用适合其 Rust/TGF 热路径的 inner/middle/outer
节点和 bitboard；NMM_LLM 可以继续使用自己的数组及 2-bit 打包。
序列化边界只做一次 24 项置换：

```text
公共顺序 <-> 引擎内部顺序
```

该转换不进入：

- 着法生成；
- 局面评估；
- Zobrist 更新；
- 递归搜索；或
- 引擎内部数据库二进制布局。

因此需要“转换层”，但转换层只位于文本、API 或数据库边界，不会损害
核心位运算性能。

## 6. 棋子和延迟标记

| 字符 | 含义 |
|---|---|
| `W` | White 活棋子 |
| `B` | Black 活棋子 |
| `.` | 真正的空点 |
| `w` | 原属 White、已移除但尚未清除的阻塞标记 |
| `b` | 原属 Black、已移除但尚未清除的阻塞标记 |

小写标记：

- 不计为活棋；
- 不能移动；
- 不组成磨坊；
- 不能再次被吃；
- 该点暂时不能落子或移入；
- 保留原所有者；
- 只在规则定义的确定边界清除。

`mif-finite-rules-v2` 将清除边界固定为：

```text
on-enter-moving-v1
```

也就是全局进入走子阶段时，把全部 `w`、`b` 确定性地变为 `.`。
这不是玩家动作，所以 MSTATE 不记录额外的 `clear-mark` 事件。

Sanmill 旧格式的单个 `X` 不携带所有者。转换器必须从其他权威状态取得
所有者，否则应报告有损，不能随意猜成 `w` 或 `b`。

## 7. 为什么 phase、action 和 hands 都保留

### 7.1 phase 不能总是推导

复杂规则可能出现：

- 最后一枚手中棋子刚落下，但随后的吃子尚未完成；
- 一方的手中棋子被提前吃掉，轮到该方时已经开始走子，而对手仍可落子；
- Lasker 类规则允许落子阶段移动；
- 提前停止落子后直接进入走子阶段。

所以 phase 是直接状态，不是缓存。

0.2 只保留：

```text
p = placing
m = moving
o = game over
```

正常初始局面直接使用 `phase=p, primary-ply=0`，不再引入含义不充分的
`ready`。

### 7.2 action 无损删除不了

同一个 phase 内，下一输入可能是 primary action，也可能是 supplementary
removal。

```text
p = placing regime 的 primary input
m = moving regime 的 primary input
r = removal input
o = no gameplay input
```

例如最后一次落子形成磨坊后，可以同时是：

```text
phase  = p
action = r
hand   = 0
```

把 action 去掉，就必须靠隐藏推断恢复这一中间状态，无法保证无损。

### 7.3 hands 必须是直接值

标准不使用通式：

```text
hand = initial - placed
```

若规则能从手中吃子，该公式立即失效。0.2 的 `hands` 保存“现在实际还能
落下几枚”。

历史落子数也不再被错误列为派生值。只有规则明确声明
`placement-count` 具有语义时，才使用：

```text
pc=<White 历史落子数>,<Black 历史落子数>
```

吃手中或盘上棋子都不减少 `pc`。

## 8. obligation 分支模型

单个 obligation 的线格式为：

```text
actor:cause:zone:target-owner:remaining:targets:after
```

例如 White 因磨坊要吃一个 Black 盘上棋子：

```text
w:mill:b:b:1:004040:b
```

含义依次是：

```text
执行者 White
原因 mill
区域 board
目标所有者 Black
剩余 1 次
合法目标集合 0x004040
完成后 Black 进行下一个 primary action
```

从 Black 手中吃一枚：

```text
w:mill:h:b:1:-:b
```

### 8.1 顺序和选择

`;` 连接同一分支中必须依次完成的 obligation：

```text
White obligation ; Black obligation
```

`|` 分隔由第一个移除目标选择的完整候选分支：

```text
intervention branch | custodian branch | mill branch
```

第一个 remove target 命中哪个分支，就提交到该分支并丢弃其他分支。
若同一点同时命中多个分支，按规范固定的 cause 顺序决定：

```text
leap
intervention
custodian
mill
mill-count
stalemate
board-full
```

这样能够表达 Sanmill 中“第一个吃子目标决定采用磨坊还是特殊 capture
上下文”的行为，而不再把多个异质上下文压成全局 pending 数和 flags。

### 8.2 双方都有 obligation

满盘、双方僵局移除、按磨坊数移除等情况可直接写成一个有序分支。
前一项的 `after=q` 表示继续该分支；最后一项的 `after=w` 或 `after=b`
决定随后的 primary player。

后续 board obligation 的合法目标可能被前面的移除改变，因此不得提前
伪造 bitset。非队首 board obligation 使用：

```text
targets=~
```

`~` 表示“按规范确定性延迟计算”，不是未知数据。它晋升为队首时必须先
替换为具体的六位十六进制 target bitset，队首本身永远不能使用 `~`。
hand obligation 仍使用 `targets=-`。

### 8.3 为什么目标集合也直接保存

target bitset 不只是 UI 高亮。intervention 可能先选定一条线，再进行
磨坊保护过滤；第一次移除后还可能只剩配对端点。若只保存 remaining，
不同实现可能重建出不同目标。

因此 MFEN 直接保存当前权威 target set，同时消费者仍要根据规则检查其
一致性；不一致时拒绝，不用重算值静默覆盖。只有尚未成为当前动作的后续
board obligation 才使用上述显式 `~` 延迟标记。

## 9. 按磨坊线保存历史

0.1 的 `fm` 使用 24 点并集，不能无损表达“每位玩家每条线只能触发一次”。

0.2 为每条磨坊线规定 ID：

- 正交拓扑：0—15；
- 带对角线拓扑：0—19。

并使用：

```text
ul=<White line bitset>,<Black line bitset>
```

正交拓扑每方 4 个十六进制字符，带对角线拓扑每方 5 个字符。

这是“线集合”，不是“线上点的并集”。外/内环交换和 D4 变换也对 line ID
进行置换，`conformance/vectors/transforms.json` 给出了全部规范向量。

Sanmill 当前的 per-player formed-point union 与 global used-line union
并不总能恢复 per-player line set。遇到歧义时转换器必须报告有损。

## 10. MPK 的两个明确 profile

0.2 不再把“完整 automorphism”与“只做视觉 D4”混为一谈。

### 10.1 `structural-d4-v1`

包含：

- 4 个旋转；
- 4 个镜像。

它兼容 NMM_LLM 的现有 D4 归一化思路。

### 10.2 `structural-aut16-v1`

包含上述 8 个变换，以及各自与外环/内环交换的组合。

环交换为：

```text
a7 <-> c5    d7 <-> d5    g7 <-> e5    g4 <-> e4
g1 <-> e3    d1 <-> d3    a1 <-> c3    a4 <-> c4
```

中圈保持不变。

同一个 `d7` 单 White 棋子：

- D4 profile 归一化到 `a4`，即索引 7；
- Aut16 profile 进一步归一化到 `c4`，即索引 23。

所以两个 profile 的数据库主键有意不同，数据库必须明确记录使用哪一个。

### 10.3 完整候选一起比较

MPK 不能只变换棋盘后比较。以下字段若有语义，也必须同步变换：

- `lm` 坐标；
- `ul` 线 bitset；
- 私有坐标或集合扩展。

对完整候选线做 US-ASCII 字典序最小选择；并保留选中的 transform，以便
把规范化空间中的着法逆变换回原棋盘。

### 10.4 MPK 不是所有 tablebase 的完整状态

结构 profile 省略：

- no-progress；
- repetition history；
- claims；
- 最终结果；
- primary-ply。

只有当数据集的等价关系确实由该 profile 完整覆盖时，MPK 才能作为
tablebase-like 主键。

## 11. MSTATE 的事件修订

### 11.1 去除歧义的 remove target

盘上移除：

```json
{
  "seq": 6,
  "actor": "w",
  "type": "remove",
  "target": {
    "zone": "board",
    "at": "b6"
  }
}
```

手中移除：

```json
{
  "seq": 6,
  "actor": "w",
  "type": "remove",
  "target": {
    "zone": "hand",
    "player": "b"
  }
}
```

从手中吃子不再藏在 place 的自动副作用中。place 创建 hand obligation，
remove 事件真正减少 hand。

### 11.2 intervention 选线属于 primary event

Sanmill 的 preferred removal target 是在执行造成 intervention 的 place
或 move 时消耗的上下文，不是跨回合持续存在的合法局面状态。转换器先
把它解析成 Annex A 的候选线 ID；MSTATE 在造成该上下文的 primary
event 上使用：

```json
"interventionLine": 12
```

未提供时按规范中的磨坊线顺序选择第一条候选线；提供时必须命中该事件
产生的非默认原始 intervention 线；重复指定默认线不是规范形式，未命中
任何候选线则事件无效。使用 line ID 而不是端点坐标，还避免了同一条线
因两个端点产生两种等价编码。进入 pending removal 后，MFEN 的完整
obligation 分支已经直接保存所需上下文，不再需要 `pref` 扩展。

### 11.3 mark-and-delay

- 玩家仍执行普通 board remove 事件；
- 规则效果把 `B` 变为 `b`，或把 `W` 变为 `w`；
- 进入走子阶段时确定性清除；
- 没有独立 `mark` 或 `clear` 事件。

### 11.4 draw 和 system

标准事件包括：

```text
offer-draw
accept-draw
decline-draw
withdraw-draw
claim-draw
resign
adjudicate
```

`system` 只能执行 `adjudicate`，不能 place、move、remove、offer、
claim 或 resign。

未知 `x-` gameplay event 不能按普通私有字段忽略。只有外部语义规范明确
标识、规则集授权且消费者实现时，才能重放。

### 11.5 MSTATE 与 MFEN 版本解耦

MSTATE 顶层增加：

```json
"positionFormat": "MFEN/0.4"
```

不再一边声称版本独立，一边把 MFEN 版本隐式写死。

### 11.6 私有规则集 envelope

私有 MSTATE 必须携带：

```json
{
  "id": "x-...",
  "version": 2,
  "digest": "sha256:...",
  "manifest": { }
}
```

单独 MFEN/MPK 使用 `rh=sha256:...`，通过调用方提供的本地 resolver
按 `(id, version, digest)` 查找。解析器禁止自动联网。

错误区分：

```text
manifest-missing
manifest-conflict
manifest-digest-mismatch
```

## 12. repetition 和 claims 已闭合

`repetitionHistory` 不再只是一串实现 hash，而是有明确定义的
`legal-state-v1` 对象。它包含：

- state profile；
- ruleset；
- board；
- side；
- phase；
- action；
- hands；
- 所有 `semanticState` 字段。

它明确排除 no-progress、primary-ply、outcome 和 claims。

`stable-moving-v1` 规定：

1. 先完成 through-stalemate 的非 repetition 确定性转换；
2. pending removal 中间状态不观察；
3. 只有最终仍 ongoing 的稳定 moving 状态才观察；
4. reset event 先清除当前窗口；
5. repetition 自动终局或允许 claim 由 manifest 明确选择；
6. repetition 导致的终局不再追加第二次观察。

`preOriginClaims` 保存 origin 时的 seed；`claims` 只保存 replay 后的最终
审计。两者一一对应，因此 pre-origin open offer 可以在事件中被处理，也可以
在 origin automatic terminal 中过期，而无需从最终状态倒推 seed。

## 13. MRS 选择有限机制，不再假装是任意规则语言

0.2 选择评审建议的“路线 A”：

> MRS 只能选择本规范已经完整定义的有限机制。

它不允许两个实现仅凭一组 Boolean 各自猜测状态转移。

`mif-finite-rules-v2` 明确规定：

- primary action 前置条件；
- mill、leap、intervention、custodian 检测顺序；
- leap 的排他优先级；
- target-commit 分支语义；
- placing 和 moving 的磨坊后果；
- 双磨坊移除次数；
- mark token 的清除边界；
- 提前停止落子的判断时点；
- 双方 obligation 的顺序；
- full-board 和 stalemate 后果；
- minimum material 的即时判断；
- no-progress 增加、重置和判断边界；
- repetition 观察；
- 所有终局条件的优先级。

稳定边界的固定顺序为：

```text
进入 moving 并清除 delayed token
-> 生成按当前磨坊数的 deferred obligation
-> full board
-> simultaneous minimum material
-> stalemate
-> repetition
-> no-progress
-> 同步下一 action
```

移除动作后的 minimum material 检查更早执行，而且落子阶段也适用：

```text
live board pieces + hand pieces < minimumLive
```

时立即失败，不必等待双方 hand 归零。

## 14. JSON、I-JSON、JCS 和数组规范化

MSTATE 与 MRS 必须是 UTF-8 I-JSON：

- JSON escape 解码后重名也算 duplicate；
- 精确整数范围为 `0 .. 9007199254740991`；
- 拒绝 unpaired surrogate；
- 不做 Unicode normalization；
- manifest digest 使用 RFC 8785 JCS 的 UTF-8 字节。

JCS 不会排序数组，所以规范逐项说明：

- manifest 中的 phases、resetEvents、semanticState 等是去重并按
  US-ASCII 排序的集合；
- events、repetitionHistory、claims 是有语义的历史顺序。

这避免语义相同的 manifest 因数组排列不同而生成不同 digest。

## 15. ABNF 已闭合

文本语法直接采用 RFC 5234 和 RFC 7405，所有大小写敏感字面量使用
`%s"..."`。

完整文法同时位于：

```text
英文规范 Annex C
conformance/mif-0.4.abnf
```

它定义了此前缺失的：

- signature；
- identifier；
- reason；
- obligation；
- 24 点 bitset；
- line bitset；
- coord；
- coord-or-dash；
- extension key/value；
- `lm`、`pc`、`rh`、`ul`。

扩展值语法允许空值，因此 `x-note=` 与文法不再冲突。

## 16. 机器可运行的一致性语料

`conformance/` 现在包含：

```text
mif-0.4.abnf
七份 provisional manifest
MFEN 正反向量
MPK D4/Aut16 向量
MSTATE replay、phase 同步、动态移除与 leap 语义向量
I-JSON/JCS/SHA-256 向量与自动完整性校验
全部 16 个 transform 的点和线置换
Sanmill/NMM_LLM 固定版本映射
```

其中 fixture digest 为：

| Fixture | SHA-256 |
|---|---|
| `x-mif-fixture-nmm@2` | `eeb1e3495e02a004b0d9589ab43ee25455613dda6b024e25a8296c3c3f727913` |
| `x-mif-fixture-dooz@2` | `8abe001b123ddee3ff88e4da8ef6970f2f847ace68bbb695927ab4a0d68872b6` |
| `x-mif-fixture-delay@2` | `59f08e0ec2317973f8ff7bf56a9ab6f699cd550ef8f065be7356dedfc88f5c3e` |
| `x-mif-fixture-stateful@2` | `ff9ddf44f2d0335b34021f161ccc2550f6b5bf820df59445ffe9049c13bf14c6` |
| `x-mif-fixture-nmm-claim@2` | `e56e246b150a046ba605701b0459f1de5aa8913aaf329dba7719bfedf1f8b3a0` |
| `x-mif-fixture-stalemate-change@2` | `70cbff2f7140dbb66718ce01f0fedc5d43f475b3cff8f58f97b15834175386ae` |
| `x-mif-fixture-mill-multi@2` | `244157e6946614090259133893fe2519f0330917d3dc7bcef6c705a3d160ae88` |

fixture 全部使用 `x-`，不会提前占用未来正式的 `nmm@1` 或 `dooz@1`。

## 17. 固定实现版本

NMM_LLM：

```text
repository: https://github.com/benmarkbrandwood-blip/NMM_LLM
commit:     234f542c9d3e7c3ebddd97f4d80edbbdb5f00991
```

Sanmill：

```text
repository: https://github.com/calcitem/Sanmill
commit:     aa6b0c99ee3fca13b0d34e6f929257959ed51414
```

相关文件和精确映射写入英文 Annex E 及
`conformance/vectors/implementation-mappings.json`。今后仓库继续演进也
不会改变本次观察的可复现基线。

## 18. 专家 P0 意见关闭情况

| 复核项 | 0.2 处理 |
|---|---|
| MRS 语义未闭合 | 选择有限机制路线，增加完整状态转移和固定优先级 |
| MSTATE 不能表示 hand removal | remove 改为结构化 board/hand target |
| `fm` 点并集有碰撞 | 改为 per-player line-ID bitset `ul` |
| D4 与 16 automorphism 未决 | 同时注册两个独立 key profile |
| placed 被错误称为派生 | 从派生列表删除；需要时用 `pc` |
| 文法不闭合 | RFC 5234 + RFC 7405 完整 ABNF |
| JCS 不足以规范语义对象 | 增加 I-JSON、数组唯一性和排序 |
| 一致性向量不足 | 增加规范性机器语料和 digest |

其他意见也已处理：

- 删除 ready；
- obligation 与上下文关联；
- 不再声称支持未编码的“其他 supplementary action”；
- 定义 repetition observation；
- 增加 positionFormat；
- 分离 ruleset/state/key profile；
- 定义私有 manifest resolver；
- 固定两个实现的 commit；
- fixture 全部改用 `x-`；
- 限定 MPK 的 tablebase 适用范围；
- 改用 Community Working Draft 标题。

## 19. 仍不应冻结稳定版的原因

0.4 已经把已知状态机和线格式歧义关掉，但仍应先完成：

- 两个独立实现通过同一语料；
- 至少两种复杂规则集的跨语言 replay；
- 更长的 automatic/claim draw 向量；
- transform 后着法逆变换交叉测试；
- parser fuzzing；
- legacy conversion loss report；
- registry 治理和媒体类型评估。

在这些条件完成前，继续使用 `0.x` 比直接宣布 `MFEN/2` 或 `MPK/1`
成熟更稳妥。

## 20. 建议双方会议按此顺序确认

1. 是否同意继续坚持 MFEN、MPK、MSTATE 三层分离；
2. 是否同意 MRS 采用有限机制路线，而不是立即设计通用规则 DSL；
3. 是否接受 obligation 的“候选完整分支”模型；
4. 是否接受 hand removal 必须是独立 MSTATE remove 事件；
5. 是否接受 `w`、`b` 及 `on-enter-moving-v1`；
6. 是否接受 per-player line-ID bitset `ul`；
7. 是否同时保留 D4 与 Aut16 两个 key profile；
8. 是否接受 `legal-state-v1` repetition 投影和观察边界；
9. 是否接受 provisional fixture 全部使用 `x-`；
10. 由谁实现第二个 parser/replayer 并共同维护 corpus。

建议会议不要先讨论“正式叫 MFEN/2 还是别的编号”。先让两个实现对同一批
输入产生完全相同的状态、事件和键，再冻结版本号。
