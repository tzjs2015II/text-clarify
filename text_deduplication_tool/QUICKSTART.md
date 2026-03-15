# 文本去重工具 - 快速开始

## 5分钟快速上手

### 第一步：准备环境

```bash
# 确保已安装Python 3.7+
python --version

# 无需安装额外依赖，使用Python标准库
```

### 第二步：准备文件

将需要去重的TXT文件放在一个目录中，例如：

```
./books/
    ├── book1.txt
    ├── book2.txt
    ├── book3.txt
    └── ...
```

### 第三步：试运行（推荐）

```bash
# 先试运行，查看结果
python text_deduplication.py ./books
```

### 第四步：查看结果

查看生成的报告文件：

```bash
cat deduplication_report.txt
```

### 第五步：真正删除

确认无误后，执行真正的删除：

```bash
python text_deduplication.py ./books --execute
```

## 常用命令

### 基础命令

```bash
# 试运行（不删除文件）
python text_deduplication.py ./books

# 真正删除重复文件
python text_deduplication.py ./books --execute

# 只搜索当前目录（不递归）
python text_deduplication.py ./books --no-recursive

# 使用自定义数据库路径
python text_deduplication.py ./books --db my_cache.db
```

### 高级命令

```bash
# 使用详细日志
python text_deduplication_advanced.py ./books --log-level DEBUG

# 调整相似度阈值（更严格）
python text_deduplication_advanced.py ./books --threshold 2

# 调整相似度阈值（更宽松）
python text_deduplication_advanced.py ./books --threshold 4

# 组合使用
python text_deduplication_advanced.py ./books --threshold 3 --execute --log-level INFO
```

## Python API 快速示例

### 基础使用

```python
from text_deduplication import TextDeduplicator

# 创建去重器
deduplicator = TextDeduplicator(
    root_dir="./books",
    db_path="cache.db",
    similarity_threshold=3
)

# 执行去重
result = deduplicator.run_deduplication(
    recursive=True,
    dry_run=True
)

# 查看结果
print(f"保留: {len(result['keep'])}, 删除: {len(result['delete'])}")

# 关闭连接
deduplicator.close()
```

### 高级使用

```python
from text_deduplication_advanced import TextDeduplicator

# 创建去重器（带日志）
deduplicator = TextDeduplicator(
    root_dir="./books",
    db_path="cache.db",
    similarity_threshold=3,
    log_level="INFO"
)

# 执行去重
result = deduplicator.run_deduplication(
    recursive=True,
    dry_run=True
)

# 查看统计信息
stats = deduplicator.db.get_statistics()
print(f"总文件: {stats['total_files']}")
print(f"保留: {stats['files_to_keep']}")
print(f"删除: {stats['files_to_delete']}")

# 生成报告
report = deduplicator.generate_report(result)
print(report)

# 关闭连接
deduplicator.close()
```

## 相似度阈值选择

| 场景 | 推荐阈值 | 说明 |
|------|---------|------|
| 精确去重 | 1-2 | 只删除几乎完全相同的文件 |
| 通用场景 | 3 | 删除内容相似的文件（推荐） |
| 激进去重 | 4-5 | 删除更多相似文件 |

**建议**: 从默认值3开始，根据效果调整。

## 输出文件说明

运行后会生成以下文件：

1. **text_deduplication.db** - 数据库缓存文件
2. **text_deduplication.log** - 日志文件（高级版本）
3. **deduplication_report.txt** - 去重报告

## 常见问题

### Q: 如何恢复被删除的文件？

A: 工具不会自动备份。建议在执行删除前手动备份：

```bash
# 备份原始文件
cp -r ./books ./books_backup

# 执行去重
python text_deduplication.py ./books --execute
```

### Q: 处理速度太慢怎么办？

A: 可以尝试以下方法：

1. 降低日志级别：`--log-level WARNING`
2. 调整相似度阈值：`--threshold 2`
3. 分批处理大目录

### Q: 如何判断去重效果？

A: 查看报告文件：

```bash
cat deduplication_report.txt
```

报告会显示：
- 总文件数
- 保留文件数
- 删除文件数
- 删除文件列表

### Q: 可以处理其他格式的文件吗？

A: 当前版本只支持TXT文件。如需支持其他格式，需要修改代码。

## 下一步

- 阅读完整文档：[README_deduplication.md](README_deduplication.md)
- 查看使用示例：[deduplication_examples.py](deduplication_examples.py)
- 运行测试：`python test_deduplication.py`
- 自定义配置：编辑 [config_deduplication.py](config_deduplication.py)

## 获取帮助

```bash
# 查看帮助信息
python text_deduplication.py --help
python text_deduplication_advanced.py --help
```

## 提示

1. **先试运行**：始终先使用dry run模式查看结果
2. **备份数据**：在执行删除前备份重要文件
3. **调整阈值**：根据实际效果调整相似度阈值
4. **查看日志**：通过日志了解处理进度和问题
5. **分批处理**：对于大量文件，建议分批处理

## 示例工作流程

```bash
# 1. 备份原始文件
cp -r ./books ./books_backup

# 2. 试运行（使用默认阈值3）
python text_deduplication.py ./books

# 3. 查看报告
cat deduplication_report.txt

# 4. 如果效果不理想，调整阈值重新试运行
python text_deduplication.py ./books --threshold 2

# 5. 确认无误后，真正删除
python text_deduplication.py ./books --threshold 2 --execute

# 6. 验证结果
ls -lh ./books
```

祝你使用愉快！🎉
