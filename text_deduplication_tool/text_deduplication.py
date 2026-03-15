import os
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import re


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
        hash_value = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        return hash_value >> (128 - self.hash_bits)
    
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
    def __init__(self, db_path: str = "text_deduplication.db"):
        self.db_path = db_path
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
            print(f"Error inserting file: {e}")
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
    
    def find_similar_files(self, simhash: int, threshold: int = 3) -> List[FileInfo]:
        cursor = self.conn.execute("""
            SELECT path, filename, word_count, file_size, simhash, processed
            FROM files
        """)
        
        similar_files = []
        for row in cursor.fetchall():
            file_simhash = int(row[4])
            distance = SimHash.hamming_distance(simhash, file_simhash)
            if distance <= threshold:
                similar_files.append(FileInfo(
                    path=row[0],
                    filename=row[1],
                    word_count=row[2],
                    file_size=row[3],
                    simhash=int(row[4]),
                    processed=row[5]
                ))
        
        return similar_files
    
    def close(self):
        if self.conn:
            self.conn.close()


class TextDeduplicator:
    def __init__(self, root_dir: str, db_path: str = "text_deduplication.db", 
                 similarity_threshold: int = 3):
        self.root_dir = Path(root_dir)
        self.db = TextDeduplicationDB(db_path)
        self.simhash = SimHash()
        self.similarity_threshold = similarity_threshold
    
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
            
            return FileInfo(
                path=str(file_path),
                filename=file_path.name,
                word_count=word_count,
                simhash=simhash_value,
                file_size=file_size
            )
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return None
    
    def scan_directory(self, recursive: bool = True) -> List[Path]:
        if recursive:
            return list(self.root_dir.rglob("*.txt"))
        else:
            return list(self.root_dir.glob("*.txt"))
    
    def index_files(self, recursive: bool = True, progress_callback=None):
        txt_files = self.scan_directory(recursive)
        total_files = len(txt_files)
        
        print(f"Found {total_files} TXT files to index...")
        
        for idx, file_path in enumerate(txt_files):
            if progress_callback:
                progress_callback(idx + 1, total_files, file_path)
            
            file_info = self.process_file(file_path)
            if file_info:
                self.db.insert_file(file_info)
        
        print(f"Indexing complete: {total_files} files processed")
    
    def find_duplicate_groups(self) -> List[List[FileInfo]]:
        all_files = self.db.get_all_files()
        processed = set()
        duplicate_groups = []
        
        print(f"Finding duplicates among {len(all_files)} files...")
        
        for i, file1 in enumerate(all_files):
            if file1.path in processed:
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
        
        return duplicate_groups
    
    def select_best_files(self, duplicate_groups: List[List[FileInfo]]) -> Dict[str, List[str]]:
        keep_files = set()
        delete_files = []
        
        print(f"Processing {len(duplicate_groups)} duplicate groups...")
        
        for group in duplicate_groups:
            sorted_group = sorted(group, key=lambda x: x.word_count, reverse=True)
            
            best_file = sorted_group[0]
            keep_files.add(best_file.path)
            
            for file_info in sorted_group[1:]:
                delete_files.append(file_info.path)
                self.db.mark_for_deletion(file_info.path)
        
        unique_files = self.db.get_all_files()
        for file_info in unique_files:
            if file_info.path not in keep_files and file_info.path not in delete_files:
                keep_files.add(file_info.path)
        
        return {
            'keep': list(keep_files),
            'delete': delete_files
        }
    
    def delete_duplicate_files(self, dry_run: bool = True) -> List[str]:
        files_to_delete = self.db.get_files_to_delete()
        deleted_files = []
        
        print(f"{'Would delete' if dry_run else 'Deleting'} {len(files_to_delete)} duplicate files...")
        
        for file_path in files_to_delete:
            try:
                if not dry_run:
                    os.remove(file_path)
                deleted_files.append(file_path)
                print(f"{'[DRY RUN] ' if dry_run else ''}Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        
        return deleted_files
    
    def run_deduplication(self, recursive: bool = True, dry_run: bool = True):
        print("=" * 60)
        print("Text Deduplication Process")
        print("=" * 60)
        
        print("\nStep 1: Indexing files...")
        self.index_files(recursive)
        
        print("\nStep 2: Finding duplicate groups...")
        duplicate_groups = self.find_duplicate_groups()
        
        print("\nStep 3: Selecting best files...")
        result = self.select_best_files(duplicate_groups)
        
        print(f"\nResults:")
        print(f"  Files to keep: {len(result['keep'])}")
        print(f"  Files to delete: {len(result['delete'])}")
        
        print("\nStep 4: Deleting duplicates...")
        deleted = self.delete_duplicate_files(dry_run)
        
        print("\n" + "=" * 60)
        print("Deduplication complete!")
        print("=" * 60)
        
        return result
    
    def close(self):
        self.db.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deduplicate text files based on content similarity')
    parser.add_argument('directory', help='Directory containing TXT files')
    parser.add_argument('--db', default='text_deduplication.db', help='SQLite database path')
    parser.add_argument('--threshold', type=int, default=3, help='Similarity threshold (hamming distance)')
    parser.add_argument('--no-recursive', action='store_true', help='Do not search recursively')
    parser.add_argument('--execute', action='store_true', help='Actually delete files (default is dry run)')
    
    args = parser.parse_args()
    
    deduplicator = TextDeduplicator(
        root_dir=args.directory,
        db_path=args.db,
        similarity_threshold=args.threshold
    )
    
    try:
        deduplicator.run_deduplication(
            recursive=not args.no_recursive,
            dry_run=not args.execute
        )
    finally:
        deduplicator.close()


if __name__ == "__main__":
    main()
