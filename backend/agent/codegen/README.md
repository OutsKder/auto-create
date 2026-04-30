# Codegen 模块

这个模块提供代码生成链路的基础骨架，包含代码生成器（Code Generator / CodeExecutor）、测试生成器（SDET）、补丁应用器（Patcher）和运行器（Runner）。

结构说明：

- `models.py`：定义 `Patch`、`DiffBundle`、`TestBundle`、`SandboxResult` 等 Pydantic 数据模型。
- `patcher.py`：按 Search/Replace 协议原子性应用补丁。
- `runner.py`：在本地或 Docker 容器中执行命令，优先保证可控与安全。
- `code_generator.py`：`CodeGeneratorAgent` 骨架，负责组织 LLM 生成的补丁并汇总为 Diff Bundle。
- `sdet.py`：`SDETAgent` 骨架，负责根据代码变更和验收标准生成测试计划与测试命令。
- `validators.py`：提供基础语法校验工具。
- `utils.py`：提供原子写入、读取文件等通用工具。

说明：

- 这些文件目前是实现骨架，后续需要和项目现有的 `BaseAgent` 与 LLM Provider 继续对接。
- `Runner` 的 Docker 执行路径是尽力实现，使用前需要环境里可用 `docker`。
- `Patcher` 遵循设计文档中的 Search/Replace 协议，优先保证安全性、原子写入和修改范围可控。
