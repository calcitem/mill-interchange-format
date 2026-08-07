# MIF Suite 1.0 独立适配器最终 pin 通知

状态：`ready-for-independent-adapter-pin`

本通知的机器可读依据为
[`release/mif-1.0-adapter-finalization.json`](../../release/mif-1.0-adapter-finalization.json)。
它启动 Sanmill 与 NMM_LLM 的最终 suite pin 和独立复测，但不等于已经发布
`MIF Suite 1.0`。

## 共同基线

- MIF 仓库提交：`3ee7e57c7d4c7208be91f62914f344a587fb0f70`
- 远端 CI：`MIF verification` run `31139940388`，结论 `success`
- wire 提交：`7e45d5a3fa970a535ed6a8a8ff5981aba4b9c978`
- suite JCS SHA-256：
  `sha256:81a5feabc281bfc4f830addabc2c6846d1f191bbbcf04e548f04b35dd358ae6f`
- suite raw-file SHA-256：
  `sha256:088ca33234289b06d9276aa4c430758222aa85d61621dee7bef4bfc6dcc069a4`
- 许可证：全仓 `Apache-2.0`

两项目必须同时 pin MIF commit、suite 的 JCS digest 与 raw-file digest，以及两个
ruleset `semanticDigest`。只 pin `id@version`、分支名或文件路径不构成发布证据。

## 两项目现在执行

Sanmill 在 `master`、NMM_LLM 在 `dev` 独立完成以下工作：

1. 将适配器与 capability 声明绑定到共同基线和 suite digest；不得导入 MIF
   reference runner 的玩法实现。
2. 将 `MIFCAP/1.0` 的 `suites` 与被测 conformance class 更新为实际结果；不得声称
   `full`，也不要求两个直接实施 1.0 的项目声称 `conversion`。
3. 运行 58 个 deterministic cases，结果必须为 `58/58`。
4. 运行 10 个 seeded differential runs 与 5 个 mutation families，结果必须分别为
   `10/10` 与 `5/5`。
5. 运行各项目既有聚焦测试、静态检查和全仓回归。
6. 生成 `MIF-SUITE-ADAPTER-EVIDENCE/1` 证据，至少包含启动包列出的
   `requiredFields`；`suiteConformance` 只能表示已声明、已测试的 domain。
7. 原子提交并推送，回传实现 commit、evidence commit、capability/report raw SHA-256
   及未解释差异数。

本次发布要求的 class 是 `identity`、`key`、`position`、`replay`、`ruleset` 和
`transform`。预期结论为 `exact-for-tested-domain`，未解释差异必须为零。

## MIF 收口步骤

收到两份已推送的 suite-bound evidence 后，MIF 维护者将：

1. 独立核验提交、所有 raw hash、capability 和测试报告；
2. 固化三方 byte/state/replay 对比证据；
3. 把 release manifest 从 `awaiting-adapter-suite-pin` 改为 `ready-for-tag`；
4. 重新运行全部本地和远端 gate；
5. 创建不可变标签 `mif-suite-1.0`，由 GitHub OIDC/Sigstore workflow 对 suite 与
   release manifest 生成 attestation；
6. 验证 attestation 后发布正式 Suite 1.0。

## 训练门槛

NMM_LLM 现在可以使用已 pin 的 candidate suite 与独立 `experimentDigest` 做工程烟测。
正式长周期、可归档或对外引用的训练仍未放行；它必须等待不可变标签、签名
attestation，以及 Sanmill 和 NMM_LLM 两份 suite-bound evidence 全部闭合。MIF
维护者完成上述步骤后会明确发出“可以开始正式训练”的通知。
