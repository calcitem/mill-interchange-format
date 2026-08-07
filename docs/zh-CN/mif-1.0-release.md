# MIF Suite 1.0 发布政策

本文说明冻结 wire contract 之外的发布层，不改变任何 MIF wire signature 或
profile。英文 `release/README.md` 是发布流程的权威版本。

在规范仓库出现规范 `mif-suite-1.0` tag，且 release manifest 通过 GitHub
artifact attestation 验证之前，`mif-suite-1.0.json` 只是供两个独立 adapter
进行最终 pin 的 release candidate，不是已经发布的 conformance target。

## 兼容与治理

`mif-1x-strict-v1` 执行 MIF 1.0 第 16.4 节和 `GOVERNANCE.md`：未知语义
fail closed；已发布 suite bytes 和 identifier 不可变；玩法变化必须使用新
ruleset version 与 `semanticDigest`；重解释既有 wire value 必须升级 2.0。

## Media type 与扩展名

Suite 1.0 使用已有的通用 media type，不声称已经取得 MIF 专用 IANA 注册：

- MFEN、MPK：`text/plain; charset=us-ascii`，扩展名 `.mfen`、`.mpk`；
- 其余 JSON envelope：`application/json`，推荐使用
  `.mifpos.json`、`.mstate.json`、`.mrs.json`、`.mifdiag.json`、
  `.mifcap.json`、`.mifconv.json`、`.mifinv.json`、`.mifturn.json` 和
  `.mifsuite.json`。

内嵌 format signature 始终具有权威性；media type 或扩展名不能补足缺失的
ruleset identity 或 semantic digest。

## 签名与发布 gate

`release/mif-1.0-release-manifest.json` 和 `mif-suite-1.0.json` 分别由
`.github/workflows/release.yml` 使用 GitHub OIDC/Sigstore attestation 签署。
发布后用以下命令验证：

```text
gh attestation verify release/mif-1.0-release-manifest.json -R calcitem/mill-interchange-format
gh attestation verify mif-suite-1.0.json -R calcitem/mill-interchange-format
```

正式 tag 前必须完成：本地全部 gate、suite digest 冻结、Sanmill 与 NMM_LLM
绑定该 digest 的独立复跑、release manifest 绑定结果。任何 suite bytes 变化都
要求两个 adapter 重新 pin 与复测。tag 创建后 workflow 才能生成签名并发布
release assets。

## NMM_LLM 训练门槛

candidate suite 可以用于记录了精确 digest 的工程 smoke run。需要长期复现或
归档的训练必须等待已签名 tag，并同时绑定 released suite digest、每个 ruleset
`semanticDigest` 和独立的实验配置 digest。
