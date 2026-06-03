# Benchmark Workspace

本目录是 Pep_design 后续 Benchmark 的工作层。当前阶段只定义协议、schema、审计表和 smoke-test 计划，不下载大模型权重、不运行 GPU 设计任务、不声称本地复现。

## Directory Map

| path | purpose |
|:---|:---|
| `protocols/` | run.csv、任务协议和评分输出 schema |
| `smoke_tests/` | 每个候选方法的最小运行计划 |
| `input_sets/` | 后续标准输入集合说明和小型示例 |
| `availability/` | 方法仓库和数据入口的 metadata/API/HEAD 可用性审计 |
| `deployment/` | 后续服务器部署、外部目录和许可证准备清单 |
| `scoring/` | 评分协议和后续评分脚本位置 |
| `results/` | 后续小型示例输出或结果索引；真实大结果不进入 git |

## Source Boundary

`de_novo_binder_scoring` 只作为评分管线经验来源，不作为本项目依赖。后续如需使用其脚本，应另行记录版本、license、输入输出适配和引用。

v0.5 availability audits only record reachability and metadata. They do not imply that code is installed, datasets are downloaded, or methods are locally reproduced.
