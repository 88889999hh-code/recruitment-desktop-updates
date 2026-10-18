# -*- coding: utf-8 -*-
"""
AI 功能统一配置模块。
独立于 boss_recruiter.py 原有的 cfg 文件，避免互相污染。
"""
import json
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('APPDATA') or (Path.home() / '.recruitment-hrboss')) / 'RecruitmentHRBOSS'
AI_CFG_FILE = DATA_DIR / 'ai_config.json'

AI_DEF = {
    # --- DeepSeek ---
    'deepseek_api_key': '',
    'deepseek_model': 'deepseek-chat',
    'deepseek_base_url': 'https://api.deepseek.com/chat/completions',

    # --- 功能开关 ---
    'reply_enabled': '0',
    'reengage_enabled': '0',
    # 回复模式：synced=同步（只在打招呼中途暂停时回，推荐，像真人）；standalone=独立（自己轮询）；off=关闭
    'reply_mode': 'off',
    'reply_gap_minutes': '20',           # 同步模式下，打招呼过程中每隔多少分钟回一轮未读消息

    # --- 自动回复：稳妥风控参数 ---
    'reply_daily_max': '80',           # 每天最多AI回复条数（含规则命中）
    'reply_poll_interval_min': '25',   # 轮询未读消息最小间隔秒
    'reply_poll_interval_max': '55',   # 轮询未读消息最大间隔秒
    'reply_typing_delay_per_char': '0.18',  # 模拟打字：每字延迟秒数（越大越像真人越慢）
    'reply_typing_delay_min': '1.2',
    'reply_typing_delay_max': '6.0',
    'reply_work_start': '09:00',
    'reply_work_end': '21:30',
    'reply_work_start_enabled': '1',
    'reply_work_end_enabled': '1',

    # --- 复聊唤醒：更保守 ---
    'reengage_daily_max': '15',        # 每天最多唤醒人数
    'reengage_dormant_days': '3',      # 超过N天无新消息视为沉寂
    'reengage_min_gap_hours': '2',     # 两次唤醒之间最小间隔小时
    'reengage_max_gap_hours': '6',     # 两次唤醒之间最大间隔小时
    'reengage_scan_window_days': '14', # 只在最近N天的会话里找沉寂对象，避免翻旧账过猛

    # --- 沟通目标：拿手机号+简历，之后发微信号收尾暂停 ---
    'recruiter_wechat': '',            # 招聘微信号：填了之后AI才会在拿到简历后主动发给候选人
    'resume_keywords': '简历,附件简历,在线简历,查看简历',  # 判断"候选人是否发过简历"的关键词，逗号分隔
    'pause_after_goal': '0',           # 微信交换后仍需继续回答问题

    # --- 计数持久化 ---
    'reply_daily_count': '0',
    'reply_daily_count_date': '',
    'reengage_daily_count': '0',
    'reengage_daily_count_date': '',
}


def load_ai_cfg():
    c = dict(AI_DEF)
    try:
        if os.path.exists(AI_CFG_FILE):
            with open(AI_CFG_FILE, encoding='utf-8') as source:
                raw = json.load(source)
            raw.pop('deepseek_api_key', None)
            c.update(raw)
    except Exception:
        pass
    c.update(deepseek_api_key='', reply_enabled='0', reengage_enabled='0', reply_mode='off')
    return c


def save_ai_cfg(c):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        safe = dict(c)
        safe.pop('deepseek_api_key', None)
        safe.update(reply_enabled='0', reengage_enabled='0', reply_mode='off')
        with open(AI_CFG_FILE, 'w', encoding='utf-8') as output:
            json.dump(safe, output, ensure_ascii=False, indent=2)
    except Exception:
        pass


def knowledge_dir():
    d = DATA_DIR / 'knowledge'
    d.mkdir(parents=True, exist_ok=True)
    return d
