# Availability Audits

本目录记录 v0.5 起的在线可用性审计。检查方式限于 metadata/API/HEAD/`git ls-remote`，不得在本目录或本仓库中保存下载的数据文件、第三方源码、模型权重或预测结果。

| file | purpose |
|:---|:---|
| `link_availability_matrix_v0.5.csv` | 方法仓库、数据记录页、API、文件 HEAD 和本地文献卡的可达性快照 |
| `data_access_manifest_v0.5.csv` | 候选数据集是否可用于后续服务器下载/校准/目标集构建的决策表 |

`available` 或 `ok` 只表示入口可达或 metadata 可读，不表示数据已经下载、schema 已经审查或 benchmark target 已经冻结。
