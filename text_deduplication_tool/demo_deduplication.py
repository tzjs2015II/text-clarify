"""
文本去重工具演示脚本
展示工具的实际使用效果
"""

import os
import tempfile
import shutil
from pathlib import Path
from text_deduplication_advanced import TextDeduplicator


def create_demo_files(demo_dir: Path):
    """创建演示用的TXT文件"""
    print("创建演示文件...")
    
    demo_files = {}
    
    # 原始文件
    demo_files["三体.txt"] = """
    三体
    刘慈欣
    
    第一章：科学边界
    
    2007年，地球。
    
    汪淼觉得，来找他的这两个人有点儿奇怪。其实并不奇怪，他只是觉得他们像是一对儿。
    
    男的四十多岁，穿着一身做工考究的西装，戴着金丝眼镜，头发梳得一丝不苟。
    女的三十多岁，穿着职业装，长发披肩，化着淡妆。
    
    他们自我介绍说是国家科学委员会的，要请汪淼去参加一个会议。
    
    "什么会议？"汪淼问。
    
    "关于基础科学问题的会议。"男的说。
    
    "基础科学？"汪淼笑了，"我是个搞纳米材料的，跟基础科学不搭界啊。"
    
    "汪教授，您谦虚了。"女的说，"您在纳米材料领域的研究，对基础科学也有重要意义。"
    
    汪淼摇摇头："你们找错人了吧？"
    
    "不会错的。"男的说，"我们调查过您的背景。"
    
    汪淼心里一动："调查我？"
    
    "是的。"女的说，"我们调查过所有相关领域的专家。"
    
    汪淼沉默了一会儿："好吧，我去。"
    
    "太好了！"男的说，"会议明天开始，地点在市郊的一个宾馆。"
    
    "好的。"汪淼说。
    
    两人起身告辞。
    
    汪淼看着他们的背影，心里有种奇怪的感觉。
    """
    
    # 重复文件1（完全相同）
    demo_files["三体_副本.txt"] = """
    三体
    刘慈欣
    
    第一章：科学边界
    
    2007年，地球。
    
    汪淼觉得，来找他的这两个人有点儿奇怪。其实并不奇怪，他只是觉得他们像是一对儿。
    
    男的四十多岁，穿着一身做工考究的西装，戴着金丝眼镜，头发梳得一丝不苟。
    女的三十多岁，穿着职业装，长发披肩，化着淡妆。
    
    他们自我介绍说是国家科学委员会的，要请汪淼去参加一个会议。
    
    "什么会议？"汪淼问。
    
    "关于基础科学问题的会议。"男的说。
    
    "基础科学？"汪淼笑了，"我是个搞纳米材料的，跟基础科学不搭界啊。"
    
    "汪教授，您谦虚了。"女的说，"您在纳米材料领域的研究，对基础科学也有重要意义。"
    
    汪淼摇摇头："你们找错人了吧？"
    
    "不会错的。"男的说，"我们调查过您的背景。"
    
    汪淼心里一动："调查我？"
    
    "是的。"女的说，"我们调查过所有相关领域的专家。"
    
    汪淼沉默了一会儿："好吧，我去。"
    
    "太好了！"男的说，"会议明天开始，地点在市郊的一个宾馆。"
    
    "好的。"汪淼说。
    
    两人起身告辞。
    
    汪淼看着他们的背影，心里有种奇怪的感觉。
    """
    
    # 重复文件2（有少量差异）
    demo_files["三体_精校版.txt"] = """
    三体
    刘慈欣
    
    第一章：科学边界
    
    2007年，地球。
    
    汪淼觉得，来找他的这两个人有点儿奇怪。其实并不奇怪，他只是觉得他们像是一对儿。
    
    男的四十多岁，穿着一身做工考究的西装，戴着金丝眼镜，头发梳得一丝不苟。
    女的三十多岁，穿着职业装，长发披肩，化着淡妆。
    
    他们自我介绍说是国家科学委员会的，要请汪淼去参加一个会议。
    
    "什么会议？"汪淼问。
    
    "关于基础科学问题的会议。"男的说。
    
    "基础科学？"汪淼笑了，"我是个搞纳米材料的，跟基础科学不搭界啊。"
    
    "汪教授，您谦虚了。"女的说，"您在纳米材料领域的研究，对基础科学也有重要意义。"
    
    汪淼摇摇头："你们找错人了吧？"
    
    "不会错的。"男的说，"我们调查过您的背景。"
    
    汪淼心里一动："调查我？"
    
    "是的。"女的说，"我们调查过所有相关领域的专家。"
    
    汪淼沉默了一会儿："好吧，我去。"
    
    "太好了！"男的说，"会议明天开始，地点在市郊的一个宾馆。"
    
    "好的。"汪淼说。
    
    两人起身告辞。
    
    汪淼看着他们的背影，心里有种奇怪的感觉。
    
    （精校版，修正了部分标点符号）
    """
    
    # 不同文件
    demo_files["流浪地球.txt"] = """
    流浪地球
    刘慈欣
    
    第一章：刹车时代
    
    我没见过黑夜，我没见过星星，我没见过春天、秋天和冬天。
    
    我出生在刹车时代结束的时候，那时地球刚刚停止转动。
    
    地球啊，我的流浪地球……
    
    啊，地球，我的流浪地球……
    
    在这个时代，死亡是司空见惯的事情。
    
    我记得，在我很小的时候，爷爷就死了。
    
    那是第一次，我看到了死亡。
    
    爷爷躺在那里，一动不动，就像睡着了一样。
    
    但是，我知道，他再也不会醒来了。
    
    妈妈哭了，爸爸也哭了。
    
    我不知道他们为什么哭，但我也哭了。
    
    那是我第一次哭，也是我第一次明白，死亡是什么。
    
    死亡，就是永远地离开。
    
    """
    
    # 不同文件2
    demo_files["乡村教师.txt"] = """
    乡村教师
    刘慈欣
    
    第一章：烛光
    
    在这个偏僻的小山村里，有一所小小的学校。
    
    学校里只有一个老师，就是王老师。
    
    王老师已经五十多岁了，头发花白，脸上布满了皱纹。
    
    但是，他的眼睛依然明亮，充满了智慧和慈爱。
    
    他教孩子们读书、写字、算术。
    
    虽然条件艰苦，但他从不抱怨。
    
    他说，知识是改变命运的唯一途径。
    
    孩子们都很喜欢他，尊敬他。
    
    在他们心中，王老师就像一盏明灯，照亮了他们的未来。
    
    """
    
    # 创建文件
    for filename, content in demo_files.items():
        file_path = demo_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
    
    print(f"创建了 {len(demo_files)} 个演示文件")
    return demo_files


def demo_basic_usage():
    """演示基础使用"""
    print("\n" + "=" * 70)
    print("演示1: 基础使用")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir) / "demo_books"
        demo_dir.mkdir()
        
        # 创建演示文件
        create_demo_files(demo_dir)
        
        # 创建去重器
        db_path = demo_dir / "demo_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(demo_dir),
            db_path=str(db_path),
            similarity_threshold=3,
            log_level="INFO"
        )
        
        # 执行去重（dry run）
        print("\n执行去重（dry run）...")
        result = deduplicator.run_deduplication(
            recursive=True,
            dry_run=True
        )
        
        # 显示结果
        print("\n去重结果:")
        print(f"  保留文件数: {len(result['keep'])}")
        print(f"  删除文件数: {len(result['delete'])}")
        
        print("\n保留的文件:")
        for file_path in result['keep']:
            print(f"  - {Path(file_path).name}")
        
        print("\n删除的文件:")
        for file_path in result['delete']:
            print(f"  - {Path(file_path).name}")
        
        # 关闭连接
        deduplicator.close()


def demo_different_thresholds():
    """演示不同阈值的效果"""
    print("\n" + "=" * 70)
    print("演示2: 不同相似度阈值的效果")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir) / "demo_thresholds"
        demo_dir.mkdir()
        
        # 创建演示文件
        create_demo_files(demo_dir)
        
        # 测试不同阈值
        thresholds = [1, 2, 3, 4]
        
        for threshold in thresholds:
            print(f"\n使用阈值 {threshold}:")
            
            db_path = demo_dir / f"cache_threshold_{threshold}.db"
            deduplicator = TextDeduplicator(
                root_dir=str(demo_dir),
                db_path=str(db_path),
                similarity_threshold=threshold,
                log_level="WARNING"  # 减少日志输出
            )
            
            result = deduplicator.run_deduplication(
                recursive=True,
                dry_run=True
            )
            
            print(f"  保留: {len(result['keep'])}, 删除: {len(result['delete'])}")
            
            deduplicator.close()


def demo_statistics():
    """演示统计功能"""
    print("\n" + "=" * 70)
    print("演示3: 统计功能")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_dir = Path(temp_dir) / "demo_stats"
        demo_dir.mkdir()
        
        # 创建演示文件
        create_demo_files(demo_dir)
        
        # 创建去重器
        db_path = demo_dir / "demo_stats_cache.db"
        deduplicator = TextDeduplicator(
            root_dir=str(demo_dir),
            db_path=str(db_path),
            similarity_threshold=3,
            log_level="WARNING"
        )
        
        # 执行去重
        result = deduplicator.run_deduplication(
            recursive=True,
            dry_run=True
        )
        
        # 显示统计信息
        stats = deduplicator.db.get_statistics()
        
        print("\n统计信息:")
        print(f"  总文件数: {stats['total_files']}")
        print(f"  保留文件数: {stats['files_to_keep']}")
        print(f"  删除文件数: {stats['files_to_delete']}")
        print(f"  总字数: {stats['total_words']:,}")
        print(f"  总大小: {stats['total_size'] / 1024:.2f} KB")
        
        # 生成报告
        report = deduplicator.generate_report(result)
        print("\n报告预览:")
        print(report[:500] + "...")
        
        deduplicator.close()


def demo_batch_processing():
    """演示批量处理"""
    print("\n" + "=" * 70)
    print("演示4: 批量处理多个目录")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir) / "demo_batch"
        base_dir.mkdir()
        
        # 创建多个子目录
        categories = ["科幻", "文学", "历史"]
        for category in categories:
            category_dir = base_dir / category
            category_dir.mkdir()
            create_demo_files(category_dir)
        
        print(f"创建了 {len(categories)} 个分类目录")
        
        # 批量处理
        for category in categories:
            print(f"\n处理分类: {category}")
            
            category_dir = base_dir / category
            db_path = base_dir / f"cache_{category}.db"
            
            deduplicator = TextDeduplicator(
                root_dir=str(category_dir),
                db_path=str(db_path),
                similarity_threshold=3,
                log_level="WARNING"
            )
            
            result = deduplicator.run_deduplication(
                recursive=True,
                dry_run=True
            )
            
            print(f"  保留: {len(result['keep'])}, 删除: {len(result['delete'])}")
            
            deduplicator.close()


def main():
    """运行所有演示"""
    print("\n" + "=" * 70)
    print("文本去重工具演示")
    print("=" * 70)
    
    try:
        demo_basic_usage()
        demo_different_thresholds()
        demo_statistics()
        demo_batch_processing()
        
        print("\n" + "=" * 70)
        print("演示完成！")
        print("=" * 70)
        print("\n提示:")
        print("  1. 查看完整文档: README_deduplication.md")
        print("  2. 快速开始: QUICKSTART.md")
        print("  3. 使用示例: deduplication_examples.py")
        print("  4. 运行测试: python test_deduplication.py")
        print()
        
    except Exception as e:
        print(f"\n演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
