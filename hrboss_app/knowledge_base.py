"""Verified local recruitment facts for the HRBOSS-derived client.

The raw BOSS chat archive is never loaded into this module automatically.
"""

import json
import re
from pathlib import Path


DEFAULT_COMPANY_INFO = """# 已核实岗位信息
岗位：抖音服装鞋帽兼职带货主播；新人和有经验者均可；每天直播 3 小时。
收益、地点、排班、设备、培训、招聘微信号、现场接待时间和联系人尚未核实。
"""

DEFAULT_QA_RULES = [
    {'keywords': ['直播多久', '几个小时', '每天直播'], 'answer': '每天直播 3 小时。'},
    {'keywords': ['薪资', '工资', '收入', '收益', '提成', '结算'],
     'answer': '具体收益和结算方式还没核实，我先记录问题，确认后答复。'},
    {'keywords': ['地点', '地址', '在哪里', '看货盘'],
     'answer': '完整地址和接待安排还没核实，确认后再邀请你到现场了解。'},
    {'keywords': ['培训', '设备', '排班', '休息'],
     'answer': '这项安排还没核实，我先记录问题，确认后答复。'},
]

DEFAULT_SYSTEM_TEMPLATE = """你是企业招聘 AI 助手，当前岗位：{job}。
请以自然、简短的中文回答，通常一轮 1–2 句，并明确自己是自动助手、可以转人工。
只使用下列已核实资料；收益、地址、排班、设备、培训等未核实信息不能编造。
只根据岗位能力和对方主动提供的工作相关事实沟通，不按性别、年龄等无关或受保护属性筛选。
候选人明确拒绝或要求停止联系后立刻停止。交换微信前先征得同意；交换后继续回答问题。
只有完整地址、可接待时段和联系人都核实后，才能提出具体到场邀请；不要冒充已经加好友或已约定。
【已核实资料】
{company_info}
"""


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path):
        self.dir = Path(knowledge_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.company_info_path = self.dir / 'company_info.md'
        self.qa_rules_path = self.dir / 'qa_rules.json'
        self._ensure_defaults()
        self.reload()

    def _ensure_defaults(self):
        if not self.company_info_path.exists():
            self.company_info_path.write_text(DEFAULT_COMPANY_INFO, encoding='utf-8')
        if not self.qa_rules_path.exists():
            self.qa_rules_path.write_text(json.dumps(DEFAULT_QA_RULES, ensure_ascii=False, indent=2), encoding='utf-8')

    def reload(self):
        try:
            self.company_info = self.company_info_path.read_text(encoding='utf-8')
            rules = json.loads(self.qa_rules_path.read_text(encoding='utf-8'))
            self.qa_rules = rules if isinstance(rules, list) else DEFAULT_QA_RULES
        except (OSError, ValueError, TypeError):
            self.company_info = DEFAULT_COMPANY_INFO
            self.qa_rules = DEFAULT_QA_RULES

    def match_rule(self, message: str):
        if not isinstance(message, str) or not message.strip():
            return None
        for rule in self.qa_rules:
            if not isinstance(rule, dict):
                continue
            keywords = rule.get('keywords') or []
            if isinstance(keywords, list) and any(isinstance(kw, str) and kw and kw in message for kw in keywords):
                answer = rule.get('answer')
                return answer if isinstance(answer, str) and answer.strip() else None
        return None

    def company_info_for_job(self, job: str):
        parts = re.split(r'^##\s*岗位[:：]\s*', self.company_info, flags=re.MULTILINE)
        general = parts[0].strip()
        if len(parts) == 1:
            return general
        for part in parts[1:]:
            title, _, body = part.partition('\n')
            if title.strip() and job and (title.strip() in job or job in title.strip()):
                return f'{general}\n\n## 岗位：{title.strip()}\n{body.strip()}'.strip()
        return general + '\n该候选人应聘的具体岗位段落未核实，不能借用其他岗位条件。'

    def build_system_prompt(self, job: str, constraints: str = '', recruiter_wechat: str = ''):
        # Unverified UI settings and raw recruiter WeChat IDs are not model facts.
        return DEFAULT_SYSTEM_TEMPLATE.format(job=job or '抖音服装鞋帽兼职带货主播',
                                              company_info=self.company_info_for_job(job))
