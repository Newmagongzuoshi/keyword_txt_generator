import os

MAX_WORKERS = min(32, max(4, (os.cpu_count() or 4) * 2))

RANDOM_ATTEMPTS = 20

MIN_LENGTH_VARIATION_RATE = 0.02
MAX_LENGTH_VARIATION_RATE = 0.15

LOG_UPDATE_INTERVAL = 20

ENABLE_DETAILED_LOG = True
ENABLE_EXTRACT_CACHE = True

OUTPUT_ENCODING = "utf-8"

LEVEL_PROVINCE = 1
LEVEL_CITY = 2
LEVEL_COUNTY = 3
LEVEL_TOWN = 4
LEVEL_VILLAGE = 5

LEVEL_NAMES = {
    1: "省级",
    2: "市级",
    3: "区县级",
    4: "乡镇街道级",
    5: "村社区级",
}

LEVEL_ORDER = ["省级", "市级", "区县级", "乡镇街道级", "村社区级"]

VIDEO_EXTS = {
    ".mp4", ".mov", ".avi", ".mkv", ".flv",
    ".wmv", ".mpeg", ".mpg", ".m4v", ".3gp",
    ".ts", ".webm"
}

INVALID_PREFIXES = [
    "中国",
    "全国",
    "国内",
    "本地",
]

INVALID_TAIL_WORDS = [
    "地区",
    "省份",
    "区域",
    "辖区",
    "地方",
    "附近",
    "周边",
    "本地",
    "文件夹",
]

FULL_WIDTH_DIGITS = "０１２３４５６７８９"
HALF_WIDTH_DIGITS = "0123456789"
DIGIT_TRANSLATION = str.maketrans(FULL_WIDTH_DIGITS, HALF_WIDTH_DIGITS)
