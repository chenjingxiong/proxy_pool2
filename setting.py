# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     setting.py
   Description :   配置文件
   Author :        JHao
   date：          2019/2/15
-------------------------------------------------
   Change Activity:
                   2019/2/15:
-------------------------------------------------
"""

BANNER = r"""
****************************************************************
*** ______  ********************* ______ *********** _  ********
*** | ___ \_ ******************** | ___ \ ********* | | ********
*** | |_/ / \__ __   __  _ __   _ | |_/ /___ * ___  | | ********
*** |  __/|  _// _ \ \ \/ /| | | ||  __// _ \ / _ \ | | ********
*** | |   | | | (_) | >  < \ |_| || |  | (_) | (_) || |___  ****
*** \_|   |_|  \___/ /_/\_\ \__  |\_|   \___/ \___/ \_____/ ****
****                       __ / /                          *****
************************* /___ / *******************************
*************************       ********************************
****************************************************************
"""

VERSION = "2.4.0"

# ############### server config ###############
HOST = "0.0.0.0"

PORT = 5010

# ############### database config ###################
# db connection uri
# example:
#      Redis: redis://:password@ip:port/db
#      Ssdb:  ssdb://:password@ip:port
DB_CONN = 'redis://:pwd@127.0.0.1:6380/0'

# proxy table name
TABLE_NAME = 'use_proxy'


# ###### config the proxy fetch function ######
PROXY_FETCHER = [
    "freeProxy03",
    "freeProxy05",
    "freeProxy07",
    "freeProxy10",
    "freeProxy11",
    "freeProxy12",
    "freeProxy13",
    "freeProxy15",
    "freeProxy17",
    "freeProxy18",
    "freeProxyScdn",
    "freeProxy43",
    "freeProxy46",
    "freeProxy47",
    "freeProxy50",
    "freeProxy51",
    "freeProxy52",
    "freeProxy53",
    "freeProxy54",
    "freeProxy55",
    "freeProxy56",
    "freeProxy57",
    "freeProxy58",
    "freeProxy59",
    "freeProxy60",
    "freeProxy61",
    "freeProxy62",
    "freeProxy63",
    "freeProxy64",
    "freeProxy65",
    "freeProxy66",
    "freeProxy67",
    "freeProxy68",
    "freeProxy69",
    "freeProxy70",
    "freeProxy71",
    "freeProxy72",
    "freeProxy73",
    "freeProxy74",
    "freeProxy75",
    "freeProxy76",
    "freeProxy77",
    "freeProxy78",
    "freeProxy79",
    "freeProxy80",
    "freeProxy81",
    "freeProxy82",
    "freeProxy83",
    "freeProxy84",
    "freeProxy85",
    "freeProxy86",
    "freeProxy87",
    "freeProxy88",
    "freeProxy89",
    "freeProxy90",
    "freeProxy91",
    "freeProxy92",
    "freeProxy93",
    "freeProxy94",
    "freeProxy95",
    "freeProxy96",
    "freeProxy97",
    "freeProxy98",
    "freeProxy99",
    "freeProxy100",
]

# ############# proxy validator #################
# 代理验证目标网站
HTTP_URL = "http://httpbin.org"

HTTPS_URL = "https://www.qq.com"

# 代理验证时超时时间
VERIFY_TIMEOUT = 10

# 近PROXY_CHECK_COUNT次校验中允许的最大失败次数,超过则剔除代理
MAX_FAIL_COUNT = 0

# 近PROXY_CHECK_COUNT次校验中允许的最大失败率,超过则剔除代理
# MAX_FAIL_RATE = 0.1

# proxyCheck时代理数量少于POOL_SIZE_MIN触发抓取
POOL_SIZE_MIN = 20

# ############# proxy attributes #################
# 是否启用代理地域属性
PROXY_REGION = True

# ############# scheduler config #################

# Set the timezone for the scheduler forcely (optional)
# If it is running on a VM, and
#   "ValueError: Timezone offset does not match system offset"
#   was raised during scheduling.
# Please uncomment the following line and set a timezone for the scheduler.
# Otherwise it will detect the timezone from the system automatically.

TIMEZONE = "Asia/Shanghai"

# ############# AI proxy search config #################
# AI API密钥（必须通过环境变量设置，不要硬编码）
AI_API_KEY = ""

# AI API基础URL（OpenAI兼容接口）
AI_API_BASE_URL = "https://api.openai.com/v1"

# AI模型名称
AI_MODEL = "gpt-3.5-turbo"

# 是否启用AI代理搜索（设置了AI_API_KEY时自动启用）
AI_SEARCH_ENABLED = False

# 每日AI搜索执行时间（0-23点，默认凌晨3点）
AI_SEARCH_HOUR = 3

# AI每次搜索最多探索的代理源数量
AI_MAX_SOURCES = 10

# AI API请求超时时间（秒）
AI_API_TIMEOUT = 60
