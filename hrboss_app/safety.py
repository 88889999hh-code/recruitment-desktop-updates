"""Fail-closed delivery gates for the HRBOSS-derived Windows client.

The public-login candidate has no UI or config path that can turn on live
candidate sending, active outreach, or paid model calls.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformPermission:
    platform_approved: bool = False
    adapter_verified: bool = False
    recipient_authorized: bool = False


def require_live_send(permission: PlatformPermission | None = None) -> None:
    if permission is None or not all((
        permission.platform_approved,
        permission.adapter_verified,
        permission.recipient_authorized,
    )):
        raise PermissionError('真实 BOSS 发送已锁定：平台许可、页面适配和收件人授权尚未核验')


def require_active_outreach() -> None:
    raise PermissionError('主动搜索与批量打招呼在本候选版中关闭')


def require_paid_model_call() -> None:
    raise PermissionError('付费模型调用在本候选版中关闭')
