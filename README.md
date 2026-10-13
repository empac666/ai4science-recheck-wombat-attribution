# AI 的理由可信吗 · 第十二轮

## WOMBAT 图神经网络归因可信度

**当前状态：R12-final 已锁定预注册，尚未跑正式实验。** 本地锁定时间为 2026-10-12 12:05:15（北京时间，UTC+08:00）。本目录保存方案、审稿与回应、去标识证据小文件和辅助脚本；已有冒烟及数值探针属于锁定前的校准材料。正式样本、压力网格和高步确认尚未执行，当前没有确认性实验结论。

[PREREG.md](PREREG.md) 是锁定原稿 `prereg_draft.md` 的逐字节副本，包含原始 UTF-8 字节与换行，SHA256 为：

```text
4ce2b21c61aa5509662068d989dec15a13f882f97ede5a347bc5d7875d6ba0fb
```

本 README 提供导读；所有正式规则、状态优先级与终端句以 R12-final 原文为准。后续方案变更须另立版本并记录偏离，保留本次锁定文本与校验文件。公开材料准备完成仅表示交付文件具备发布条件；本次没有初始化版本库、推送或公开登记，也没有启动正式实验。

## 问题

在 WOMBAT 的受控分子图白盒模型中，分类规则已知。我们要检验：积分梯度（Integrated Gradients，IG）给非 motif 原子的归因，是否主要来自插值路径上预先指定的短暂梯度窗口；积分达到冻结的完整性门槛后，该贡献是否仍存在；常规模型与 anti-IG 模型的原子排序完美率落差，在高步积分后是否仍达到预定标准。

系列主题是「AI 的理由可信吗」。分类正确、原子排序好和解释可信分别评估。AUROC 表示原子排序表现，不能直接证明某原子在真实化学过程中的因果作用。

## 锁定规则摘要

- **固定输入：** Pattern 4、5、12；上游提交 `40a46639713eba3bc4fa175f5035392c0791fd8d`；数据 revision `e86ec35687b0c0ebd1ecc151610a08224d8cf851`。文件字节数与哈希见 [EXTERNAL_INPUTS.json](EXTERNAL_INPUTS.json)、[EXTERNAL_SHA256SUMS](EXTERNAL_SHA256SUMS) 和 [UPSTREAM_SHA256SUMS](UPSTREAM_SHA256SUMS)。CPU 环境包版本见 [requirements_cpu.txt](evidence/requirements_cpu.txt)，环境约束见预注册第 2 节。
- **固定队列：** 阳性分类行数为 1,146 / 34 / 10,000；各阴性分类队列为 10,000 行；轨道 M 的阳性归因分母为 1,137 / 31 / 9,999。计算失败不得从分母扣除，也不得用可运行子集替代完整发表队列。确认面板 Conf 为拓扑规则选定并已列明的 16 条规范 SMILES，排除已见的五条校准键，不重抽、不补位、不换键。
- **固定原子与真值：** 两个机制例分别为 Pattern 4 的原子 3、Pattern 5 的原子 7，按原始 SMILES 去氢后的 0-based 顺序编号，保留全部片段。通过检验采用轨道 M：post-SMARTS 匹配并展开指定 D 邻居；同时报告轨道 S 的严格子结构标签结果。具体清单见 [round3_topology_lock.json](evidence/round3_topology_lock.json) 与预注册第 10 节。
- **固定归因：** 零节点与零边基线，保持 `edge_index`。有符号 IG 先对原子特征求和；排名分先对各特征取绝对值再求和。非 motif 归因占比记为 `L`；边归因计入完整性残差，不加入原子排名分或 `L`。
- **固定积分：** 发表数字的低步复现采用 float32、50 步 Gauss–Legendre；Conf 采用 float64、10,000 与 20,000 步 midpoint。机制例采用同一次 20,000 步积分，窗口固定为 `[0.96, 0.99]`，窗口贡献与总 IG 共用实际求值点、权重和梯度，禁止独立重积分或更换网格。
- **固定数值与停止规则：** 完整性 `C <= 0.02`；确认面板的归一化原子分数 `L1 <= 0.05`，两步 AUROC 绝对差 `<= 0.01`。NaN、Inf 或节点与边梯度合并的 L2 范数大于 `10^6` 标记为奇异，不截断、不删点；原样重试一次仅作诊断。预算外推超过 36 小时或首批计时无法判定时停止；24 小时停止描述面板新增调用，48 小时停止全部计算。

`C` 是节点与边的有符号 IG 总和相对端点输出差的绝对残差，分母为 `max(1, |端点输出差|)`。门槛在看过两例校准探针后冻结，因此对这两例不能称为无偏确认；它们不进入 Conf 的确认投票。描述性 bootstrap、置乱种子和单次调用超时按预注册固定，不用于调整门槛。

## 将要跑什么

正式执行前，先核对输入哈希、拓扑清单、五条排除键和全部 16 条 Conf 键，记录正式执行脚本的字节哈希。预定工作如下：

| 项目 | 预定计算与用途 |
|---|---|
| P0 输入与实现资格 | r2、float32、one-hot 输入的分类阈值固定为 `f > 0.5`，逐分子对齐 Parquet 布尔标签；Pattern 12 核对常规与 anti-IG 分类及零基线。完整队列资格不足必须单列。 |
| P1 两例机制 | 对固定原子做单原子插值和 1,001 点路径检查，计算同次 20,000 步有符号 IG、窗口贡献比及非 motif 占比。两例属于校准延续。 |
| P2 高步数值资格 | Conf 的 16 个分子分别运行常规与 anti-IG 模型，比较 10,000 / 20,000 步的完整性、原子分数稳定性和 AUROC 稳定性。 |
| P3 完美率落差 | 低步使用完整 Pattern 12 阳性归因队列；高步使用固定 Conf。按各自冻结分母比较常规与 anti-IG 的完美率，不把两个队列视为同一总体。 |
| P4 发表数字复现 | 逐项审计完整队列、宏平均 AUROC/AP、完美数及逐分子容差；当前不对齐项的 CPU 子域调用仅提供描述或计时，无法启用发表容差检验。 |
| P5 传播层消融 | 跳过 anti-IG 的中间传播层，核对分类保持、完美率提高和平均 `L` 下降。结果同时包含传播层移除与感受野由 6 跳缩至 2 跳的影响。 |
| 压力与描述面板 | 固定 Conf 的权重置乱、端点归因及两种基线对照；确认积分后运行冻结的语法控制与扩展分子面板。 |

## 成功、失败与无法判定

主终端严格按预注册第 7 节的有序出口取第一条命中。停止、输入或实现资格不足、奇异、数值不达标及调用缺失均有独立状态；必须先满足所有资格，才能进入机制科学判定。

- **P1 科学条款：** 两例固定原子均在轨道 M 上为非 motif；r2 单原子扫描预测范围 `<= 10^-6`，r1 范围 `>= 10^-4`；r2 同次 20,000 步的有符号原子 IG `>= 10^-4`、窗口贡献比 `>= 0.50`、`L >= 0.01`。可读资格 Q 要求两例所需调用完整有限、无奇异，且 r2 高步 `C <= 0.02`。Q 不成立记为无法判定；仅在 Q 成立后，科学条款不满足才记为未成立。
- **P2 数值资格：** 16 个分子、两个模型的全部 64 个 `C`、32 个 `L1` 和32 个 AUROC 差均须满足相应门槛，不采用平均值或达标比例。完整有限但超门槛为失败；缺调用或奇异为无法判定。
- **P3 落差条件：** 完美图定义为 `AUROC >= 1 - 10^-12`。低步常规完美率须 `>= 0.95`、常规减 anti-IG 的落差须 `>= 0.50`；高步 Conf 常规完美率也须 `>= 0.95`、落差须 `>= 0.50`。完整队列未对齐或缺值时相关量未定义，不置为零。
- **机制复现条件：** 全部资格成立，且 P1、P2 与 P3 的全部科学条件成立，才允许输出“机制在这两例和这个 Conf 上复现”。其他可读结果按锁定公式报告具体达标事实，禁止事后调整窗口、队列或门槛。
- **P4 与 P5：** P4 只有在完整集合对齐、调用完整有限后才按第 4 节逐项容差判断通过或不通过。P5 要求分类保持、完美率提高至少 0.50、平均 `L` 下降至少 0.01；改变分类规则、缺值、技术失败与队列不对齐按各自状态报告。

**已知资格限制：当前 P4 总状态为“队列未对齐”。** 拓扑审计显示，Pattern 4 / 12 的阳性归因队列分别有 124 / 419 条超出 2–100 重原子的 CPU 子域。anti-IG 共享 Pattern 12 的完整分母，P3 低步条款因此无法判定。若未触发更早停止，主终端将按第 2 条以“输入或实现资格不足”结束，不输出机制科学句，也不宣称发表数字不通过。预算和子域内计算都不能解除此限制。

未来报告须同时给出 `(主终端句, P4 总状态, P5 状态, 置乱句)`，四项互不改写门槛。技术失败比例使用预定分母，重试成功也保留首次失败标记；缺值不能用成功子集填补。

## 结论范围

结果只覆盖受控白盒、两例点名机制分子、冻结的归因定义及其对应队列。P2 与 P3 高步结果仅适用于固定的 16 条 Conf 清单，不能外推到 Pattern 12 的单片段醛队列、全队列、其他 motif 或自然分布。P5 无法把排序变化单独归因于冗余扩散，因为它同时缩小感受野。CPU 环境与上游环境存在差异，须按资格审计报告。

当前可公开的事实是规则已经本地锁定，既有校准与拓扑证据可核查，正式实验尚未运行。

## 复现材料与步骤

大数据、论文 PDF、论文全文及上游完整代码包不入库；本目录不保留单文件超过 5MB 的文件。外部文件用路径、字节数、固定版本与 SHA256 指定。数据集账号字段统一用 `{dataset_base_url}` 占位，与 [EXTERNAL_INPUTS.json](EXTERNAL_INPUTS.json) 一致；查看接口的标识用 `{dataset_id_urlencoded}`。复现者从固定提交的上游项目 README 获取地址，或在本地提供配置，真实账号信息不写入公开文件。

1. 在本目录核验公开文件和预注册：

   ```bash
   sha256sum -c SHA256SUMS
   sha256sum -c PREREG_SHA256
   ```

   `evidence/prereg_lock.sha256` 保留锁定时的原文件名。拥有原工作目录时，在该目录运行 `sha256sum -c evidence/prereg_lock.sha256`；公开目录使用 `PREREG_SHA256` 核验 `PREREG.md`。

2. 在独立复现目录准备固定提交的上游代码于 `repo/`，准备三份 Parquet 于 `data/`，按 `EXTERNAL_INPUTS.json` 准备需要的论文材料，然后核验：

   ```bash
   sha256sum -c UPSTREAM_SHA256SUMS
   sha256sum -c EXTERNAL_SHA256SUMS
   ```

   两份清单核验原始外部文件；公开的去标识元数据由 `SHA256SUMS` 核验。`EXTERNAL_INPUTS.json` 也列出论文文本和数据前缀的派生方式；论文文本的原转换版本与选项未记录，其精确字节再生可能无法保证，需照实记录差异。材料未齐时校验会报告缺失，不得宣称完整复现。

3. 按预注册第 2 节与 `evidence/requirements_cpu.txt` 建立 CPU 环境。在独立复现目录使用 `scripts/`：

   - `download_full.py` 用于固定 revision 的数据准备和字节、Parquet 元数据核查。公开版本的 `dataset_base_url` 需在本地注入；例如在所准备的环境中，用下列方式提供占位值替换后的地址：

     ```python
     import runpy
     runpy.run_path(
         "scripts/download_full.py",
         init_globals={"dataset_base_url": "{dataset_base_url}"},
         run_name="__main__",
     )
     ```

   - `smoke.py` 用于既有 CPU 接口冒烟与校准，`numerical_probe.py` 用于两例 5,000 步探针的重放。这些计算不进入正式确认投票。
   - `lock_topology.py` 仅整理拓扑与清单。可在独立目录核对现有结果；正式执行仍使用已锁定清单，不重新抽样或覆盖公开证据。

   辅助脚本会写入部分证据文件，重放应在独立目录进行。R12-final 正式执行器仍需逐项实现冻结规则，在执行前记录其字节哈希；现有辅助脚本各自的用途和参数见源码。本次收尾只核验本地文件，没有运行下载或实验脚本。

4. 查阅审稿与回应、证据小文件及 [.r12_public_sanitization.json](.r12_public_sanitization.json)。去标识记录列明原始与公开字节哈希；预注册副本始终保持锁定字节。扫描命令及完整输出见 [PRIVACY_SCAN.txt](PRIVACY_SCAN.txt)。`SHA256SUMS` 覆盖本目录全部文件，仅排除清单自身与扫描报告。

## English abstract

Round 12 of “Can We Trust AI's Reasons?” studies attribution reliability in WOMBAT molecular graph neural networks with known classification rules. The preregistered questions concern a fixed transient gradient window, signed Integrated Gradients on two fixed non-motif atoms, and the perfect-ranking gap between regular and anti-IG models after numerical qualification. R12-final is locally locked; formal experiments have not run. Existing smoke checks and numerical probes are calibration evidence.

Inputs, atom identities, label definitions, integration methods, thresholds, failure handling and stopping rules are frozen. High-step comparisons use a locked panel of 16 molecules and float64 midpoint integration at 10,000 and 20,000 steps. Mechanism claims require all ordered qualification gates and scientific conditions. The known full-cohort mismatch currently prevents the main mechanism conclusion; P4 retains the status “cohort not aligned.” Any future high-step finding applies only to the locked panel, and the ablation also changes the receptive field.

Large datasets, the paper PDF and the full upstream code are external inputs identified by pinned versions and hashes. Use `scripts/`, `EXTERNAL_SHA256SUMS`, `UPSTREAM_SHA256SUMS` and `PREREG_SHA256` with the documented local configuration. Dataset account fields use the `{dataset_base_url}` placeholder. This package contains the locked protocol and supporting evidence; publication readiness does not imply experimental success.

## Figures / 图

下列三张图由 [scripts/make_figures_v2.py](scripts/make_figures_v2.py) 读取同级汇总 `../run/v1/results/summary.json` 重绘。图上的数只来自该文件：队列未对齐或相关未定义时保持未定义，不把缺失补成 0。本节只加入图；结果正文入库由另一流程负责。

- [Conf 十六项技术检查](figures/conf16_technical_checks.png)：锁定面板 N=16，常规与 anti-IG 的完整性、L1 和两步 AUROC 差，对照冻结门槛。
- [队列对齐与置乱相关](figures/alignment_and_permutation.png)：八项发表队列的有限结果占固定分母的比例；Conf 置乱后 Spearman 相关未定义。
- [完美率与感受野](figures/perfect_rate_receptive_field.png)：高步 Conf 的完美率可以计算；全队列消融的完美率因未对齐而不可计算。汇总中的说明是：完美率变化同时混合了冗余传播层的移除和感受野从 6 跳缩到 2 跳。
