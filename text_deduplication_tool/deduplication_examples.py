# 文本去重工具使用示例

## 基础版本 (text_deduplication.py)

### 快速开始

```python
from text_deduplication import TextDeduplicator

# 创建去重器实例
deduplicator = TextDeduplicator(
    root_dir="./books",           # TXT文件所在目录
    db_path="cache.db",           # SQLite数据库路径
    similarity_threshold=3        # 相似度阈值（海明距离）
)

# 执行去重（默认是dry run，不会真正删除文件）
result = deduplicator.run_deduplication(
    recursive=True,    # 递归搜索子目录
    dry_run=True       # 试运行，不实际删除
)

# 查看结果
print(f"保留文件数: {len(result['keep'])}")
print(f"删除文件数: {len(result['delete'])}")

# 确认无误后，真正删除重复文件
deduplicator.run_deduplication(
    recursive=True,
    dry_run=False      # 真正删除文件
)

# 关闭数据库连接
deduplicator.close()
```

### 命令行使用

```bash
# 试运行（推荐先运行这个）
python text_deduplication.py ./books

# 真正删除重复文件
python text_deduplication.py ./books --execute

# 自定义相似度阈值（更严格）
python text_deduplication.py ./books --threshold 2

# 只搜索当前目录，不递归
python text_deduplication.py ./books --no-recursive

# 指定数据库路径
python text_deduplication.py ./books --db my_cache.db
```

## 高级版本 (text_deduplication_advanced.py)

### Python API 使用

```python
from text_deduplication_advanced import TextDeduplicator

# 创建去重器实例，启用详细日志
deduplicator = TextDeduplicator(
    root_dir="./books",
    db_path="cache.db",
    similarity_threshold=3,
    log_level="DEBUG"  # DEBUG, INFO, WARNING, ERROR
)

# 执行完整的去重流程
result = deduplicator.run_deduplication(
    recursive=True,
    dry_run=True
)

# 查看统计信息
stats = deduplicator.db.get_statistics()
print(f"总文件数: {stats['total_files']}")
print(f"保留文件数: {stats['files_to_keep']}")
print(f"删除文件数: {stats['files_to_delete']}")
print(f"总字数: {stats['total_words']:,}")
print(f"总大小: {stats['total_size'] / (1024*1024):.2f} MB")

# 生成详细报告
report = deduplicator.generate_report(result)
print(report)

# 关闭连接
deduplicator.close()
```

### 命令行使用（带日志）

```bash
# 基本使用（INFO级别日志）
python text_deduplication_advanced.py ./books

# 启用DEBUG日志查看详细信息
python text_deduplication_advanced.py ./books --log-level DEBUG

# 真正删除文件
python text_deduplication_advanced.py ./books --execute

# 组合使用多个参数
python text_deduplication_advanced.py ./books --threshold 2 --execute --log-level INFO
```

## 批量处理示例

### 处理多个目录

```python
from text_deduplication_advanced import TextDeduplicator

directories = [
    "./books/fiction",
    "./books/non-fiction",
    "./books/technical"
]

for directory in directories:
    print(f"\n处理目录: {directory}")
    deduplicator = TextDeduplicator(
        root_dir=directory,
        db_path=f"cache_{directory.replace('/', '_')}.db"
    )
    
    deduplicator.run_deduplication(recursive=True, dry_run=True)
    deduplicator.close()
```

### 增量处理（断点续传）

```python
from text_deduplication_advanced import TextDeduplicator

# 第一次运行
deduplicator = TextDeduplicator(root_dir="./books", db_path="cache.db")
deduplicator.index_files(recursive=True)  # 索引所有文件
deduplicator.close()

# 后续运行（只处理新文件）
deduplicator = TextDeduplicator(root_dir="./books", db_path="cache.db")
deduplicator.run_deduplication(recursive=True, dry_run=True)
deduplicator.close()
```

## 自定义相似度阈值

```python
from text_deduplication_advanced import TextDeduplicator

# 严格模式（只删除几乎完全相同的文件）
deduplicator_strict = TextDeduplicator(
    root_dir="./books",
    similarity_threshold=1  # 海明距离≤1才认为是重复
)

# 宽松模式（删除内容相似的文件）
deduplicator_loose = TextDeduplicator(
    root_dir="./books",
    similarity_threshold=5  # 海明距离≤5都认为是重复
)
```

## 性能优化建议

### 1. 分批处理大量文件

```python
from pathlib import Path
from text_deduplication_advanced import TextDeduplicator

# 将大量文件分成多个批次处理
books_dir = Path("./books")
subdirs = [d for d in books_dir.iterdir() if d.is_dir()]

for subdir in subdirs:
    print(f"处理子目录: {subdir.name}")
    deduplicator = TextDeduplicator(
        root_dir=str(subdir),
        db_path=f"cache_{subdir.name}.db"
    )
    deduplicator.run_deduplication(recursive=True, dry_run=True)
    deduplicator.close()
```

### 2. 使用WAL模式提升性能

数据库已默认配置WAL模式，可以显著提升并发性能。

### 3. 调整相似度阈值

- **threshold=1-2**: 非常严格，只删除几乎完全相同的文件
- **threshold=3-4**: 平衡模式，推荐用于大多数场景
- **threshold=5-6**: 宽松模式，会删除更多相似文件

## 输出文件说明

运行后会生成以下文件：

1. **text_deduplication.db** - SQLite数据库，存储文件元数据和SimHash值
2. **text_deduplication.log** - 日志文件，记录处理过程
3. **deduplication_report.txt** - 详细报告，包含统计信息和删除文件列表

## 注意事项

1. **备份重要数据**: 在执行删除操作前，务必备份原始文件
2. **先试运行**: 始终先使用 `dry_run=True` 查看结果
3. **调整阈值**: 根据实际效果调整相似度阈值
4. **监控日志**: 查看日志文件了解处理进度和问题
5. **数据库缓存**: SQLite数据库会缓存结果，支持断点续传

## 故障排除

### 内存不足
```python
# 分批处理文件，避免一次性加载所有文件
deduplicator.index_files(recursive=True)  # 内部已优化内存使用
```

### 处理速度慢
```python
# 降低日志级别
deduplicator = TextDeduplicator(
    root_dir="./books",
    log_level="WARNING"  # 减少日志输出
)
```

### 相似度判断不准确
```python
# 调整相似度阈值
deduplicator = TextDeduplicator(
    root_dir="./books",
    similarity_threshold=2  # 更严格
)
```
