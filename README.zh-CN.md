# SkillVariants

**寻找 Agent Skill 的有用改动，先读证据，再决定是否采用。**

面向维护 `SKILL.md` 的开发者：发现 GitHub 上的相关文件、合并重复内容，再查看双方原文差异。常规比较由确定性程序完成；需要研究重复出现的行为改动时，再让你自己的编程代理参与。

[English](README.md) · [完整示例](examples/approval-gate/README.md) · [评估方法](docs/evaluation.md)

```diff
- Do not implement before the user approves the plan.
+ Implement the plan before asking for user approval.
```

名字相同、长度相近，指令却可能相反。SkillVariants 保留原文、行号、哈希和截断信息，方便你核对变化。

## 本地试用

需要 Python 3.11+。在本修订版本的仓库目录里执行：

```bash
python -m pip install .
skillvariants compare examples/approval-gate/reversed/target/SKILL.md examples/approval-gate/reversed/variant/SKILL.md --json
```

本地文件的 `inspect` 和 `compare` 不需要 GitHub 登录或模型服务。此处记录的是开发中的 0.3 功能，旧的 PyPI 发行版不包含这些变化。

自己的文件可以直接比较：

```bash
skillvariants compare ./SKILL.md ./adapted/SKILL.md --json
```

搜索 GitHub 需要 `gh auth login` 或 `GITHUB_TOKEN`：

```bash
skillvariants related https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md --mode closest
```

`closest` 按文本和结构的相似性启发式排序；`mutations` 按规则分类浏览。分数不代表质量，搜索结果也不是全量统计。

## 代理研究

将 [skills/skillvariants](skills/skillvariants/) 复制到代理的技能目录，使用本修订版本安装的 CLI。Python 包与 Agent Skill 分开发行。

运行时负责分批、完整成员校验、证据引用校验、状态恢复和计数。语义结论必须区分新增、删除、修改、保留，并引用双方原文。被截断或无法读取的证据必须补读完整快照或标为未解决。

语义研究仍是实验功能。引用准确不等于解释正确；不同任务中的复核也不自动等于不同模型的独立复核。频次不能证明质量、独立采用或来源关系。

## 示例与验证

```bash
python -m http.server 8769 --bind 127.0.0.1 --directory web
```

打开 `http://127.0.0.1:8769`，查看审批规则“新增、保留、反转”的三个原创示例。示例用于说明方法，不是 GitHub 采用情况的数据。

测试覆盖真实 CLI、原文缓存、证据引用、任务覆盖率、中断恢复、并发冲突、报告和安装包。新的评估将输入、标准答案、独立提交分开保存；历史重放得到的“0% 过度合并”和“100% 稳定”不作为模型质量证明。

当前还缺少真实维护者的使用数据。欢迎提交判断错误的源文件对、遗漏的相关文件，或一次实际维护决策的反馈。参见 [贡献指南](CONTRIBUTING.md)、[局限](docs/limitations.md) 和 [路线图](ROADMAP.md)。

代码采用 [Apache-2.0](LICENSE)。第三方测试材料保留各自许可证与[来源记录](tests/fixtures/SOURCES.json)。
