import os
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
import re
import time
from datetime import datetime


@dataclass
class FileInfo:
    path: str
    filename: str
    word_count: int
    simhash: int
    file_size: int
    processed: bool = False


class SimHash:
    def __init__(self, hash_bits: int = 64):
        self.hash_bits = hash_bits
        self.weight_dict = {}
    
    def _tokenize(self, text: str) -> List[str]:
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', text)
        english_words = re.findall(r'[a-zA-Z]+', text)
        return chinese_words + english_words
    
    def _hash_string(self, token: str) -> int:
        return int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16) >> (128 - self.hash_bits)
    
    def compute(self, text: str) -> int:
        tokens = self._tokenize(text)
        token_counts = defaultdict(int)
        
        for token in tokens:
            token_counts[token] += 1
        
        v = [0] * self.hash_bits
        
        for token, count in token_counts.items():
            h = self._hash_string(token)
            for i in range(self.hash_bits):
                if h & (1 << i):
                    v[i] += count
                else:
                    v[i] -= count
        
        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] >= 0:
                fingerprint |= (1 << i)
        
        return fingerprint & ((1 << self.hash_bits) - 1)
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int, hash_bits: int = 64) -> int:
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance


class TextDeduplicationDB:
    def __init__(self, db_path: str = "text_deduplication.db", logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                file_size INTEGER NOT NULL,
                simhash TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                keep BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_simhash ON files(simhash)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed ON files(processed)
        """)
        
        self.conn.commit()
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def insert_file(self, file_info: FileInfo) -> bool:
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO files 
                (path, filename, word_count, file_size, simhash, processed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_info.path, file_info.filename, file_info.word_count, 
                  file_info.file_size, str(file_info.simhash), file_info.processed))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error inserting file {file_info.path}: {e}")
            return False
    
    def get_all_files(self) -> List[FileInfo]:
        cursor = self.conn.execute("""
            SELECT path, filename, word_count, file_size, simhash, processed
            FROM files
        """)
        
        files = []
        for row in cursor.fetchall():
            files.append(FileInfo(
                path=row[0],
                filename=row[1],
                word_count=row[2],
                file_size=row[3],
                simhash=int(row[4]),
                processed=row[5]
            ))
        return files
    
    def get_unprocessed_files(self) -> List[FileInfo]:
        cursor = self.conn.execute("""
            SELECT path, filename, word_count, file_size, simhash, processed
            FROM files
            WHERE processed = 0
        """)
        
        files = []
        for row in cursor.fetchall():
            files.append(FileInfo(
                path=row[0],
                filename=row[1],
                word_count=row[2],
                file_size=row[3],
                simhash=int(row[4]),
                processed=row[5]
            ))
        return files
    
    def mark_as_processed(self, file_path: str):
        self.conn.execute("""
            UPDATE files SET processed = 1 WHERE path = ?
        """, (file_path,))
        self.conn.commit()
    
    def mark_for_deletion(self, file_path: str):
        self.conn.execute("""
            UPDATE files SET keep = 0 WHERE path = ?
        """, (file_path,))
        self.conn.commit()
    
    def get_files_to_keep(self) -> List[str]:
        cursor = self.conn.execute("""
            SELECT path FROM files WHERE keep = 1
        """)
        return [row[0] for row in cursor.fetchall()]
    
    def get_files_to_delete(self) -> List[str]:
        cursor = self.conn.execute("""
            SELECT path FROM files WHERE keep = 0
        """)
        return [row[0] for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, int]:
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_files,
                SUM(CASE WHEN keep = 1 THEN 1 ELSE 0 END) as files_to_keep,
                SUM(CASE WHEN keep = 0 THEN 1 ELSE 0 END) as files_to_delete,
                SUM(word_count) as total_words,
                SUM(file_size) as total_size
            FROM files
        """)
        
        row = cursor.fetchone()
        return {
            'total_files': row[0] or 0,
            'files_to_keep': row[1] or 0,
            'files_to_delete': row[2] or 0,
            'total_words': row[3] or 0,
            'total_size': row[4] or 0
        }
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")


class ProgressTracker:
    def __init__(self, total: int, description: str = "Processing", logger: Optional[logging.Logger] = None):
        self.total = total
        self.current = 0
        self.description = description
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = time.time()
        self.last_update = 0
    
    def update(self, increment: int = 1, item: str = ""):
        self.current += increment
        current_time = time.time()
        
        if current_time - self.last_update >= 1.0 or self.current >= self.total:
            progress = (self.current / self.total) * 100
            elapsed = current_time - self.start_time
            
            if self.current > 0:
                eta = (elapsed / self.current) * (self.total - self.current)
            else:
                eta = 0
            
            self.logger.info(
                f"{self.description}: {self.current}/{self.total} ({progress:.1f}%) "
                f"Elapsed: {self._format_time(elapsed)} ETA: {self._format_time(eta)}"
            )
            
            if item:
                self.logger.debug(f"  Processing: {item}")
            
            self.last_update = current_time
    
    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def complete(self):
        elapsed = time.time() - self.start_time
        self.logger.info(f"{self.description} completed in {self._format_time(elapsed)}")


class TextDeduplicator:
    def __init__(self, root_dir: str, db_path: str = "text_deduplication.db", 
                 similarity_threshold: int = 3, log_level: str = "INFO"):
        self.root_dir = Path(root_dir)
        self._setup_logging(log_level)
        self.db = TextDeduplicationDB(db_path, self.logger)
        self.simhash = SimHash()
        self.similarity_threshold = similarity_threshold
        
        self.logger.info(f"TextDeduplicator initialized with threshold={similarity_threshold}")
    
    def _setup_logging(self, log_level: str):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler('text_deduplication.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def count_words(self, text: str) -> int:
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words
    
    def process_file(self, file_path: Path) -> Optional[FileInfo]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            word_count = self.count_words(content)
            file_size = file_path.stat().st_size
            simhash_value = self.simhash.compute(content)
            
            self.logger.debug(f"Processed {file_path.name}: {word_count} words, {file_size} bytes")
            
            return FileInfo(
                path=str(file_path),
                filename=file_path.name,
                word_count=word_count,
                simhash=simhash_value,
                file_size=file_size
            )
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return None
    
    def scan_directory(self, recursive: bool = True) -> List[Path]:
        if recursive:
            files = list(self.root_dir.rglob("*.txt"))
        else:
            files = list(self.root_dir.glob("*.txt"))
        
        self.logger.info(f"Found {len(files)} TXT files in {self.root_dir}")
        return files
    
    def index_files(self, recursive: bool = True):
        txt_files = self.scan_directory(recursive)
        total_files = len(txt_files)
        
        if total_files == 0:
            self.logger.warning("No TXT files found!")
            return
        
        progress = ProgressTracker(total_files, "Indexing files", self.logger)
        
        for idx, file_path in enumerate(txt_files):
            file_info = self.process_file(file_path)
            if file_info:
                self.db.insert_file(file_info)
            
            progress.update(1, file_path.name)
        
        progress.complete()
    
    def find_duplicate_groups(self) -> List[List[FileInfo]]:
        all_files = self.db.get_all_files()
        processed = set()
        duplicate_groups = []
        
        self.logger.info(f"Finding duplicates among {len(all_files)} files...")
        
        progress = ProgressTracker(len(all_files), "Finding duplicates", self.logger)
        
        for i, file1 in enumerate(all_files):
            if file1.path in processed:
                progress.update(1)
                continue
            
            similar_group = [file1]
            
            for j, file2 in enumerate(all_files):
                if i >= j:
                    continue
                
                if file2.path in processed:
                    continue
                
                distance = SimHash.hamming_distance(file1.simhash, file2.simhash)
                if distance <= self.similarity_threshold:
                    similar_group.append(file2)
            
            if len(similar_group) > 1:
                duplicate_groups.append(similar_group)
                for file_info in similar_group:
                    processed.add(file_info.path)
                    self.logger.debug(f"Found duplicate group: {[f.filename for f in similar_group]}")
            
            progress.update(1)
        
        progress.complete()
        self.logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        
        return duplicate_groups
    
    def select_best_files(self, duplicate_groups: List[List[FileInfo]]) -> Dict[str, List[str]]:
        keep_files = set()
        delete_files = []
        
        self.logger.info(f"Processing {len(duplicate_groups)} duplicate groups...")
        
        progress = ProgressTracker(len(duplicate_groups), "Selecting best files", self.logger)
        
        for group in duplicate_groups:
            sorted_group = sorted(group, key=lambda x: x.word_count, reverse=True)
            
            best_file = sorted_group[0]
            keep_files.add(best_file.path)
            
            self.logger.info(
                f"Keeping: {best_file.filename} ({best_file.word_count:,} words) "
                f"- Deleting {len(sorted_group)-1} duplicates"
            )
            
            for file_info in sorted_group[1:]:
                delete_files.append(file_info.path)
                self.db.mark_for_deletion(file_info.path)
                self.logger.debug(f"  Marked for deletion: {file_info.filename} ({file_info.word_count:,} words)")
            
            progress.update(1)
        
        unique_files = self.db.get_all_files()
        for file_info in unique_files:
            if file_info.path not in keep_files and file_info.path not in delete_files:
                keep_files.add(file_info.path)
        
        progress.complete()
        
        return {
            'keep': list(keep_files),
            'delete': delete_files
        }
    
    def delete_duplicate_files(self, dry_run: bool = True) -> List[str]:
        files_to_delete = self.db.get_files_to_delete()
        deleted_files = []
        
        if not files_to_delete:
            self.logger.info("No files to delete")
            return deleted_files
        
        action = "Would delete" if dry_run else "Deleting"
        self.logger.info(f"{action} {len(files_to_delete)} duplicate files...")
        
        progress = ProgressTracker(len(files_to_delete), f"{'Dry run: ' if dry_run else ''}Deleting files", self.logger)
        
        for file_path in files_to_delete:
            try:
                if not dry_run:
                    os.remove(file_path)
                deleted_files.append(file_path)
                progress.update(1, Path(file_path).name)
            except Exception as e:
                self.logger.error(f"Error deleting {file_path}: {e}")
        
        progress.complete()
        
        return deleted_files
    
    def generate_report(self, result: Dict[str, List[str]]) -> str:
        stats = self.db.get_statistics()
        
        report = []
        report.append("=" * 70)
        report.append("TEXT DEDUPLICATION REPORT")
        report.append("=" * 70)
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("SUMMARY:")
        report.append(f"  Total files processed: {stats['total_files']:,}")
        report.append(f"  Files to keep: {stats['files_to_keep']:,}")
        report.append(f"  Files to delete: {stats['files_to_delete']:,}")
        report.append(f"  Total words: {stats['total_words']:,}")
        report.append(f"  Total size: {stats['total_size'] / (1024*1024):.2f} MB")
        report.append("")
        report.append("DUPLICATE FILES TO DELETE:")
        
        for file_path in result['delete'][:20]:
            file_info = next((f for f in self.db.get_all_files() if f.path == file_path), None)
            if file_info:
                report.append(f"  - {file_info.filename} ({file_info.word_count:,} words)")
        
        if len(result['delete']) > 20:
            report.append(f"  ... and {len(result['delete']) - 20} more files")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def run_deduplication(self, recursive: bool = True, dry_run: bool = True):
        self.logger.info("=" * 70)
        self.logger.info("TEXT DEDUPLICATION PROCESS STARTED")
        self.logger.info("=" * 70)
        
        self.logger.info(f"Configuration:")
        self.logger.info(f"  Root directory: {self.root_dir}")
        self.logger.info(f"  Recursive search: {recursive}")
        self.logger.info(f"  Similarity threshold: {self.similarity_threshold}")
        self.logger.info(f"  Dry run: {dry_run}")
        
        self.logger.info("\nStep 1: Indexing files...")
        self.index_files(recursive)
        
        self.logger.info("\nStep 2: Finding duplicate groups...")
        duplicate_groups = self.find_duplicate_groups()
        
        self.logger.info("\nStep 3: Selecting best files...")
        result = self.select_best_files(duplicate_groups)
        
        self.logger.info("\nStep 4: Deleting duplicates...")
        deleted = self.delete_duplicate_files(dry_run)
        
        report = self.generate_report(result)
        self.logger.info("\n" + report)
        
        with open('deduplication_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info("\nDetailed report saved to: deduplication_report.txt")
        self.logger.info("=" * 70)
        self.logger.info("DEDUPLICATION PROCESS COMPLETED")
        self.logger.info("=" * 70)
        
        return result
    
    def close(self):
        self.db.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deduplicate text files based on content similarity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default) - just show what would be deleted
  python text_deduplication_advanced.py /path/to/books
  
  # Actually delete duplicate files
  python text_deduplication_advanced.py /path/to/books --execute
  
  # Use custom similarity threshold (lower = more strict)
  python text_deduplication_advanced.py /path/to/books --threshold 2
  
  # Non-recursive search (only top-level directory)
  python text_deduplication_advanced.py /path/to/books --no-recursive
  
  # Verbose logging
  python text_deduplication_advanced.py /path/to/books --log-level DEBUG
        """
    )
    
    parser.add_argument('directory', help='Directory containing TXT files')
    parser.add_argument('--db', default='text_deduplication.db', help='SQLite database path (default: text_deduplication.db)')
    parser.add_argument('--threshold', type=int, default=3, help='Similarity threshold (hamming distance, default: 3)')
    parser.add_argument('--no-recursive', action='store_true', help='Do not search recursively')
    parser.add_argument('--execute', action='store_true', help='Actually delete files (default is dry run)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    deduplicator = TextDeduplicator(
        root_dir=args.directory,
        db_path=args.db,
        similarity_threshold=args.threshold,
        log_level=args.log_level
    )
    
    try:
        result = deduplicator.run_deduplication(
            recursive=not args.no_recursive,
            dry_run=not args.execute
        )
        
        if not args.execute:
            print("\n" + "=" * 70)
            print("DRY RUN COMPLETED - No files were deleted")
            print("To actually delete files, run with --execute flag")
            print("=" * 70)
    finally:
        deduplicator.close()


if __name__ == "__main__":
    main()
