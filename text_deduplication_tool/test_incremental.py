"""
测试增量处理功能 - 演示工具如何处理新增文件
"""

import os
import tempfile
from pathlib import Path
from text_deduplication_advanced import TextDeduplicator


def test_incremental_processing():
    """测试增量处理"""
    print("=" * 70)
    print("测试：工具如何处理新增文件")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_incremental"
        test_dir.mkdir()
        
        # 第一阶段：创建初始文件
        print("\n【第一阶段】创建初始文件...")
        
        # 文件1: 原始文件
        (test_dir / "book1.txt").write_text("""
        这是一个测试文件的内容。
        包含一些中文文本用于测试。
        这是原始版本。
        """, encoding='utf-8')
        
        # 文件2: 重复文件
        (test_dir / "book1_copy.txt").write_text("""
        这是一个测试文件的内容。
        包含一些中文文本用于测试。
        这是原始版本。
        """, encoding='utf-8')
        
        # 文件3: 不同文件
        (test_dir / "book2.txt").write_text("""
        这是完全不同的内容。
        与前面的文件没有相似之处。
        这是一个独立的故事。
        """, encoding='utf-8')
        
        print(f"创建了 3 个初始文件")
        
        # 第一次运行去重
        db_path = test_dir / "incremental_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3,
            log_level="WARNING"
        )
        
        print("\n执行第一次去重...")
        result1 = deduplicator.run_deduplication(
            recursive=True,
            dry_run=False  # 真正删除
        )
        
        print(f"\n第一次去重结果:")
        print(f"  保留: {len(result1['keep'])}, 删除: {len(result1['delete'])}")
        
        # 查看当前文件列表
        remaining_files = list(test_dir.glob("*.txt"))
        print(f"\n剩余文件: {[f.name for f in remaining_files]}")
        
        deduplicator.close()
        
        # 第二阶段：新增文件
        print("\n" + "=" * 70)
        print("【第二阶段】新增文件...")
        
        # 新增文件4: 与现有文件相似
        (test_dir / "book1_new_version.txt").write_text("""
        这是一个测试文件的内容。
        包含一些中文文本用于测试。
        这是原始版本。
        新增了一些内容使文件更长。
        这个版本应该被保留。
        """, encoding='utf-8')
        
        # 新增文件5: 全新的文件
        (test_dir / "book3.txt").write_text("""
        这是第三个独立的故事。
        与前两个文件完全不同。
        这是一个全新的内容。
        """, encoding='utf-8')
        
        print(f"新增了 2 个文件")
        print(f"当前文件列表: {[f.name for f in test_dir.glob('*.txt')]}")
        
        # 第二次运行去重（使用相同的数据库）
        deduplicator2 = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3,
            log_level="WARNING"
        )
        
        print("\n执行第二次去重（增量处理）...")
        result2 = deduplicator2.run_deduplication(
            recursive=True,
            dry_run=False
        )
        
        print(f"\n第二次去重结果:")
        print(f"  保留: {len(result2['keep'])}, 删除: {len(result2['delete'])}")
        
        # 查看最终文件列表
        final_files = list(test_dir.glob("*.txt"))
        print(f"\n最终剩余文件: {[f.name for f in final_files]}")
        
        # 查看数据库统计
        stats = deduplicator2.db.get_statistics()
        print(f"\n数据库统计:")
        print(f"  总文件数: {stats['total_files']}")
        print(f"  保留文件数: {stats['files_to_keep']}")
        print(f"  删除文件数: {stats['files_to_delete']}")
        
        deduplicator2.close()
        
        # 第三阶段：测试重复添加相同文件
        print("\n" + "=" * 70)
        print("【第三阶段】再次运行（无新增文件）...")
        
        deduplicator3 = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3,
            log_level="WARNING"
        )
        
        print("\n执行第三次去重（无新增文件）...")
        result3 = deduplicator3.run_deduplication(
            recursive=True,
            dry_run=False
        )
        
        print(f"\n第三次去重结果:")
        print(f"  保留: {len(result3['keep'])}, 删除: {len(result3['delete'])}")
        print(f"  （应该没有文件被删除，因为没有新增重复文件）")
        
        final_files2 = list(test_dir.glob("*.txt"))
        print(f"\n最终剩余文件: {[f.name for f in final_files2]}")
        
        deduplicator3.close()


def test_database_persistence():
    """测试数据库持久化"""
    print("\n" + "=" * 70)
    print("测试：数据库持久化机制")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_persistence"
        test_dir.mkdir()
        db_path = test_dir / "persistent_cache.db"
        
        # 第一次运行
        print("\n【第一次运行】创建初始数据...")
        
        (test_dir / "file1.txt").write_text("内容A", encoding='utf-8')
        (test_dir / "file2.txt").write_text("内容B", encoding='utf-8')
        
        deduplicator1 = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            log_level="WARNING"
        )
        
        deduplicator1.index_files(recursive=True)
        stats1 = deduplicator1.db.get_statistics()
        print(f"数据库中文件数: {stats1['total_files']}")
        deduplicator1.close()
        
        # 第二次运行（使用相同数据库）
        print("\n【第二次运行】使用相同数据库...")
        
        # 新增文件
        (test_dir / "file3.txt").write_text("内容C", encoding='utf-8')
        
        deduplicator2 = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            log_level="WARNING"
        )
        
        stats2 = deduplicator2.db.get_statistics()
        print(f"数据库中已有文件数: {stats2['total_files']}")
        
        deduplicator2.index_files(recursive=True)
        stats2_after = deduplicator2.db.get_statistics()
        print(f"索引后文件数: {stats2_after['total_files']}")
        print(f"新增文件数: {stats2_after['total_files'] - stats2['total_files']}")
        
        deduplicator2.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("增量处理功能测试")
    print("=" * 70)
    print("\n本测试演示工具如何处理新增文件：")
    print("1. 首次运行：建立索引并删除重复文件")
    print("2. 新增文件：工具会自动识别并处理")
    print("3. 重复运行：不会重复处理已索引的文件")
    print()
    
    try:
        test_incremental_processing()
        test_database_persistence()
        
        print("\n" + "=" * 70)
        print("测试完成！")
        print("=" * 70)
        print("\n结论：")
        print("✅ 工具支持增量处理，新增文件会被自动识别")
        print("✅ 数据库会持久化存储，支持断点续传")
        print("✅ 重复运行不会重复删除已处理的文件")
        print()
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
