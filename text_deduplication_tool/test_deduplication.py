"""
文本去重工具测试脚本
用于验证SimHash算法和去重功能的正确性
"""

import os
import tempfile
import shutil
from pathlib import Path
from text_deduplication import TextDeduplicator, SimHash


def create_test_files(test_dir: Path):
    """创建测试用的TXT文件"""
    test_files = {}
    
    # 文件1: 原始文件
    test_files["original.txt"] = """
    这是一个测试文件，用于验证文本去重功能。
    这个文件包含一些中文内容，用于测试SimHash算法。
    文本去重是一个重要的功能，可以帮助我们清理重复的文件。
    """
    
    # 文件2: 完全相同的文件（应该被删除）
    test_files["duplicate1.txt"] = """
    这是一个测试文件，用于验证文本去重功能。
    这个文件包含一些中文内容，用于测试SimHash算法。
    文本去重是一个重要的功能，可以帮助我们清理重复的文件。
    """
    
    # 文件3: 几乎相同的文件（有少量差异）
    test_files["duplicate2.txt"] = """
    这是一个测试文件，用于验证文本去重功能。
    这个文件包含一些中文内容，用于测试SimHash算法。
    文本去重是一个重要的功能，可以帮助我们清理重复的文件。
    这里添加了一点点差异。
    """
    
    # 文件4: 较长的版本（应该被保留）
    test_files["longer_version.txt"] = """
    这是一个测试文件，用于验证文本去重功能。
    这个文件包含一些中文内容，用于测试SimHash算法。
    文本去重是一个重要的功能，可以帮助我们清理重复的文件。
    这里添加了一点点差异。
    这是额外的内容，使这个文件更长。
    通过增加更多内容，我们确保这个文件会被保留。
    """
    
    # 文件5: 完全不同的文件（应该被保留）
    test_files["different.txt"] = """
    这是一个完全不同的文件，内容与前面的文件完全不同。
    它包含一些不同的词汇和句子结构。
    这个文件不应该被识别为重复文件。
    """
    
    # 创建文件
    for filename, content in test_files.items():
        file_path = test_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
    
    return test_files


def test_simhash():
    """测试SimHash算法"""
    print("=" * 60)
    print("测试 SimHash 算法")
    print("=" * 60)
    
    simhash = SimHash()
    
    text1 = "这是一个测试文本"
    text2 = "这是一个测试文本"
    text3 = "这是一个不同的文本"
    
    hash1 = simhash.compute(text1)
    hash2 = simhash.compute(text2)
    hash3 = simhash.compute(text3)
    
    print(f"文本1的SimHash: {hash1}")
    print(f"文本2的SimHash: {hash2}")
    print(f"文本3的SimHash: {hash3}")
    
    distance12 = SimHash.hamming_distance(hash1, hash2)
    distance13 = SimHash.hamming_distance(hash1, hash3)
    
    print(f"\n文本1和文本2的海明距离: {distance12}")
    print(f"文本1和文本3的海明距离: {distance13}")
    
    assert distance12 == 0, "相同文本的海明距离应该为0"
    assert distance13 > 3, "不同文本的海明距离应该大于3"
    
    print("✓ SimHash算法测试通过")
    print()


def test_deduplication():
    """测试去重功能"""
    print("=" * 60)
    print("测试文本去重功能")
    print("=" * 60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_books"
        test_dir.mkdir()
        
        # 创建测试文件
        print(f"\n创建测试文件在: {test_dir}")
        test_files = create_test_files(test_dir)
        print(f"创建了 {len(test_files)} 个测试文件")
        
        # 创建去重器
        db_path = test_dir / "test_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3
        )
        
        # 执行去重（dry run）
        print("\n执行去重（dry run）...")
        result = deduplicator.run_deduplication(
            recursive=True,
            dry_run=True
        )
        
        print(f"\n结果:")
        print(f"  保留文件数: {len(result['keep'])}")
        print(f"  删除文件数: {len(result['delete'])}")
        
        # 验证结果
        keep_files = [Path(f).name for f in result['keep']]
        delete_files = [Path(f).name for f in result['delete']]
        
        print(f"\n保留的文件: {keep_files}")
        print(f"删除的文件: {delete_files}")
        
        # 检查是否正确识别了重复文件
        # 由于SimHash的特性，完全相同的文件会被识别为重复
        # 但有少量差异的文件可能不会被识别，这取决于阈值
        assert len(result['delete']) >= 1, "应该至少删除1个重复文件"
        assert "longer_version.txt" in keep_files, "应该保留最长的版本"
        assert "different.txt" in keep_files, "应该保留完全不同的文件"
        
        # 验证文件确实还存在（dry run）
        for filename in test_files.keys():
            file_path = test_dir / filename
            assert file_path.exists(), f"Dry run模式下文件不应该被删除: {filename}"
        
        print("\n✓ Dry run测试通过")
        
        # 真正执行删除
        print("\n执行真正的删除...")
        result = deduplicator.run_deduplication(
            recursive=True,
            dry_run=False
        )
        
        # 验证文件被正确删除
        for filename in delete_files:
            file_path = test_dir / filename
            assert not file_path.exists(), f"文件应该被删除: {filename}"
        
        # 验证保留的文件还存在
        for filename in keep_files:
            file_path = test_dir / filename
            assert file_path.exists(), f"文件应该被保留: {filename}"
        
        print("✓ 真正删除测试通过")
        
        # 关闭连接
        deduplicator.close()
        
        # 等待一下，确保数据库文件释放
        import time
        time.sleep(1.0)
        
        # 显式关闭WAL连接
        import sqlite3
        try:
            wal_conn = sqlite3.connect(str(db_path))
            wal_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            wal_conn.close()
        except:
            pass
        
        time.sleep(0.5)
    
    print("\n✓ 去重功能测试通过")
    print()


def test_performance():
    """测试性能"""
    print("=" * 60)
    print("性能测试")
    print("=" * 60)
    
    import time
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "performance_test"
        test_dir.mkdir()
        
        # 创建大量测试文件
        num_files = 100
        print(f"\n创建 {num_files} 个测试文件...")
        
        base_content = """
        这是一个性能测试文件，用于验证去重工具在处理大量文件时的性能。
        SimHash算法应该能够快速计算文本指纹。
        文本去重工具应该能够高效地处理成千上万个文件。
        """
        
        for i in range(num_files):
            content = base_content
            if i % 10 == 0:  # 每10个文件添加一些差异
                content += f"\n这是文件 {i} 的独特内容。"
            
            file_path = test_dir / f"file_{i:04d}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 测试索引性能
        db_path = test_dir / "perf_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3
        )
        
        print("开始索引文件...")
        start_time = time.time()
        deduplicator.index_files(recursive=True)
        index_time = time.time() - start_time
        print(f"索引完成，耗时: {index_time:.2f} 秒")
        print(f"平均每个文件: {index_time/num_files*1000:.2f} 毫秒")
        
        # 测试去重性能
        print("\n开始去重...")
        start_time = time.time()
        result = deduplicator.run_deduplication(recursive=True, dry_run=True)
        dedup_time = time.time() - start_time
        print(f"去重完成，耗时: {dedup_time:.2f} 秒")
        
        print(f"\n处理结果:")
        print(f"  总文件数: {num_files}")
        print(f"  保留文件数: {len(result['keep'])}")
        print(f"  删除文件数: {len(result['delete'])}")
        
        deduplicator.close()
    
    print("\n✓ 性能测试完成")
    print()


def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("边界情况测试")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "edge_cases"
        test_dir.mkdir()
        
        # 空文件
        empty_file = test_dir / "empty.txt"
        empty_file.write_text("", encoding='utf-8')
        
        # 非常短的文件
        short_file = test_dir / "short.txt"
        short_file.write_text("短", encoding='utf-8')
        
        # 包含特殊字符的文件
        special_file = test_dir / "special.txt"
        special_file.write_text("特殊字符：@#$%^&*()_+-=[]{}|;':\",./<>?", encoding='utf-8')
        
        # 包含多种语言的文件
        multi_lang_file = test_dir / "multilang.txt"
        multi_lang_file.write_text("中文 English 日本語 한국어 Español Français", encoding='utf-8')
        
        # 测试处理
        db_path = test_dir / "edge_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(test_dir),
            db_path=str(db_path),
            similarity_threshold=3
        )
        
        print("\n处理边界情况文件...")
        result = deduplicator.run_deduplication(recursive=True, dry_run=True)
        
        print(f"\n处理结果:")
        print(f"  总文件数: {len(result['keep']) + len(result['delete'])}")
        print(f"  保留文件数: {len(result['keep'])}")
        print(f"  删除文件数: {len(result['delete'])}")
        
        # 所有文件都应该被保留（没有重复）
        assert len(result['delete']) == 0, "边界情况文件不应该被误判为重复"
        assert len(result['keep']) == 4, "所有边界情况文件都应该被保留"
        
        deduplicator.close()
    
    print("\n✓ 边界情况测试通过")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("文本去重工具测试套件")
    print("=" * 60)
    print()
    
    try:
        test_simhash()
        test_deduplication()
        test_performance()
        test_edge_cases()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
        print()
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        raise


if __name__ == "__main__":
    main()
