# 文本去重工具配置文件
# 将此文件重命名为 config.py 并根据需要修改参数

# ============== 基本配置 ==============

# 默认的根目录（包含TXT文件的目录）
DEFAULT_ROOT_DIR = "./books"

# SQLite数据库文件路径
DEFAULT_DB_PATH = "text_deduplication.db"

# 相似度阈值（海明距离）
# 值越小，判断越严格；值越大，判断越宽松
# 推荐值：3（平衡模式）
SIMILARITY_THRESHOLD = 3

# 是否递归搜索子目录
RECURSIVE_SEARCH = True

# 是否试运行（不实际删除文件）
DRY_RUN = True

# ============== 日志配置 ==============

# 日志级别：DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = "INFO"

# 日志文件路径
LOG_FILE = "text_deduplication.log"

# 是否在控制台显示日志
CONSOLE_LOGGING = True

# ============== 性能配置 ==============

# SimHash位数（64位推荐，32位更快但准确性较低）
SIMHASH_BITS = 64

# 批处理大小（用于大批量文件处理）
BATCH_SIZE = 1000

# 是否启用WAL模式（提升并发性能）
ENABLE_WAL_MODE = True

# ============== 文件处理配置 ==============

# 文件编码（默认UTF-8，遇到编码错误时忽略）
FILE_ENCODING = "utf-8"
FILE_ERRORS = "ignore"

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = [".txt"]

# 最小文件大小（字节），小于此值的文件会被跳过
MIN_FILE_SIZE = 100

# 最大文件大小（字节），大于此值的文件会被跳过（0表示不限制）
MAX_FILE_SIZE = 0

# ============== 高级配置 ==============

# 是否使用中文分词（需要安装jieba）
USE_CHINESE_TOKENIZATION = False

# 是否使用英文分词（需要安装nltk或其他分词库）
USE_ENGLISH_TOKENIZATION = False

# 是否缓存SimHash结果（加速重复处理）
CACHE_SIMHASH = True

# 是否生成详细报告
GENERATE_REPORT = True

# 报告文件路径
REPORT_FILE = "deduplication_report.txt"

# ============== 输出配置 ==============

# 是否显示进度条
SHOW_PROGRESS = True

# 进度更新间隔（秒）
PROGRESS_UPDATE_INTERVAL = 1.0

# 是否在报告中显示所有删除文件（False只显示前20个）
SHOW_ALL_DELETED_FILES = False

# ============== 安全配置 ==============

# 是否在删除前确认
CONFIRM_BEFORE_DELETE = True

# 是否创建备份（在删除前复制到备份目录）
CREATE_BACKUP = False

# 备份目录路径
BACKUP_DIR = "./backup"

# ============== 相似度算法配置 ==============

# SimHash算法配置
SIMHASH_CONFIG = {
    "hash_bits": 64,
    "token_weight": "frequency",  # frequency, binary
    "normalize": True
}

# 替代算法配置（如果需要）
ALTERNATIVE_ALGORITHM = "simhash"  # simhash, minhash, lsh

# ============== 调试配置 ==============

# 是否启用调试模式
DEBUG_MODE = False

# 是否保存中间结果
SAVE_INTERMEDIATE_RESULTS = False

# 中间结果保存目录
INTERMEDIATE_DIR = "./intermediate"

# ============== 示例配置预设 ==============

# 严格模式（只删除几乎完全相同的文件）
STRICT_MODE = {
    "threshold": 1,
    "description": "严格模式 - 只删除海明距离≤1的文件"
}

# 平衡模式（推荐）
BALANCED_MODE = {
    "threshold": 3,
    "description": "平衡模式 - 删除海明距离≤3的文件"
}

# 宽松模式（删除更多相似文件）
LOOSE_MODE = {
    "threshold": 5,
    "description": "宽松模式 - 删除海明距离≤5的文件"
}

# ============== 使用说明 ==============
"""
使用方法：

1. 基本使用：
   from text_deduplication_advanced import TextDeduplicator
   from config import *
   
   deduplicator = TextDeduplicator(
       root_dir=DEFAULT_ROOT_DIR,
       db_path=DEFAULT_DB_PATH,
       similarity_threshold=SIMILARITY_THRESHOLD,
       log_level=LOG_LEVEL
   )
   
   deduplicator.run_deduplication(
       recursive=RECURSIVE_SEARCH,
       dry_run=DRY_RUN
   )

2. 使用预设模式：
   from config import STRICT_MODE, BALANCED_MODE, LOOSE_MODE
   
   # 使用平衡模式
   deduplicator = TextDeduplicator(
       root_dir="./books",
       similarity_threshold=BALANCED_MODE["threshold"]
   )

3. 命令行参数会覆盖配置文件：
   python text_deduplication_advanced.py ./books --threshold 2 --execute
"""
