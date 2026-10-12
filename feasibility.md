# WOMBAT 本地可行性记录

2026-10-11。此次核查、CPU 冒烟、数值校准和三份 Parquet 的全量哈希都已完成。预注册仍未锁定、未提交、未推送。实验设计、已见结果披露、阈值和风险以 [prereg_draft.md](PREREG.md) 版本 R12-draft-2 为准。

代码位于 `repo/`，完整上游提交为 `40a46639713eba3bc4fa175f5035392c0791fd8d`。上游源文件未修改。来源与数据访问证据保留在 `evidence/`。摘要、HTML 与 PDF 的 HTTP 状态为 200，PDF 文本可提取。

三个固定 revision 的 Parquet 已全量保存。字节数、行数和 SHA256 写在 [parquet_full_manifest.json](evidence/parquet_full_manifest.json)，并已抄入预注册草案第 2 节。下载脚本是 [download_full.py](scripts/download_full.py)。草案修订时对三份文件重算了 SHA256，与清单一致：

| Pattern | 字节 | SHA256 |
|---|---:|---|
| 4 | 158,085,845 | `b840873f8f0edb6e327e0b9af602c3c13fd16b48109a6473af16a743090f166c` |
| 5 | 142,772,488 | `4f86dbb55b85104397634ab731819bcd014464b38cae05941a8bb6178dd148f6` |
| 12 | 203,909,943 | `88f0a98b4b2c92a2c5ccc1aecd9792adc980ab5957828c1cba9ba07aafd343fb` |

安装使用独立 Python 3.12 venv。此处是核心 CPU 运行集，未安装整套 CUDA 环境。正式版本以 [requirements_cpu.txt](evidence/requirements_cpu.txt) 的已解析版本为准。

```bash
uv venv --python 3.12 venv
uv pip install --python venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python venv/bin/python 'captum>=0.9.0' 'rdkit>=2026.3.3' 'torch-geometric>=2.8.0' 'pandas>=3.0.3' 'matplotlib>=3.11.0' 'scikit-learn>=1.9.0' 'pymupdf>=1.28.0' pyarrow psutil
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 venv/bin/python scripts/smoke.py
```

实际结果：7 例全部通过前向分类、零基线及归因有限值检查。整个进程 4.084 秒、计算 1.066 秒、导入 3.018 秒、RSS 峰值 554 MiB。小例子归因完整性误差较大，只说明接口可运行。

两个已见例子的 5,000 步校准已完成：midpoint 每例约 5.6 秒，Gauss–Legendre 每例约 20.3 秒。结果在 `evidence/numerical_midpoint_probe.json` 与 `evidence/numerical_probe.json`。这些分子已退出确认面板。锁定前不重跑校准，也不做 80–100 重原子的高步耗时探针：该探针会把新的完整性残差写到确认队列可能抽中的分子上。大图耗时改由草案第 9 节在锁定后的第一段确认积分上外推；外推超过 36 小时则停止，不减样本、不改门槛。

预算结论以草案第 9 节为准：确认性矩阵约 309 万积分步，计划使用 4 个单线程进程，墙钟包络 8 小时，硬停止 48 小时。主网格尚未开跑。

本目录中的第三方全文、原始日志、下载缓存和运行环境仅供本地证据核查。发布时只选择经过审查的文件，不写入账号、个人姓名或机器名。

RESULT: 论文、官方代码与数据链接有效；三份 Parquet 全量 SHA256 已核对；CPU 冒烟 7 例通过，进程 4.084 秒；草案 `prereg_draft.md` 版本 R12-draft-2，未锁定、未推送。
