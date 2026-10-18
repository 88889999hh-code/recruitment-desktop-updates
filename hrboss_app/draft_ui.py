"""Local synthetic dialogue tester. No access to BOSS or any remote service."""

import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from draft_assistant import OfflineDraftAssistant


def open_demo_window(parent, data_dir: Path):
    win = tk.Toplevel(parent)
    win.title("招聘回复演练 · 仅模拟，不会发送")
    win.geometry("790x670")
    win.minsize(610, 490)
    win.configure(bg="#f8fafc")
    worker = OfflineDraftAssistant(Path(data_dir) / "reply_demo.db",
                                   Path(data_dir) / "reply_demo_knowledge")
    latest = {"id": None, "reply": ""}
    session = tk.StringVar(value="demo:chat-1")

    ttk.Label(win, text="模拟来信 → 本地生成回复草稿", font=("微软雅黑", 14, "bold")).pack(
        anchor="w", padx=18, pady=(15, 4))
    tk.Label(win, text="规则回复演练，不是线上 BOSS 自动聊天；不读取真实会话、不开启付费模型、不会发信。",
             bg="#f8fafc", fg="#b45309", wraplength=720, justify="left").pack(
                 fill="x", padx=18, pady=(0, 13))

    top = ttk.Frame(win)
    top.pack(fill="x", padx=18)
    ttk.Label(top, text="虚拟会话编号：").pack(side="left")
    ttk.Entry(top, textvariable=session, width=25).pack(side="left", padx=6)
    ttk.Label(top, text="示例 demo:chat-1、demo:chat-2（会话隔离）").pack(side="left")

    transcript = tk.Text(win, height=20, wrap="word", relief="solid", bd=1,
                         state="disabled", font=("微软雅黑", 10))
    transcript.pack(fill="both", expand=True, padx=18, pady=12)
    transcript.tag_configure("candidate", foreground="#374151")
    transcript.tag_configure("reply", foreground="#0369a1")
    transcript.tag_configure("notice", foreground="#b45309")
    ttk.Label(win, text="输入模拟求职者问题（例如：每天直播多久？没有经验能做吗？）：").pack(
        anchor="w", padx=18)
    incoming = tk.Text(win, height=3, wrap="word", font=("微软雅黑", 10))
    incoming.pack(fill="x", padx=18, pady=6)

    def show_line(label, value, tag):
        transcript.configure(state="normal")
        transcript.insert("end", f"{label}：{value}\n\n", tag)
        transcript.configure(state="disabled")
        transcript.see("end")

    def simulate():
        text = incoming.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "请先输入模拟消息", parent=win)
            return
        try:
            result_id = uuid.uuid4().hex
            result = worker.accept(session.get().strip(), result_id, text)
        except ValueError as exc:
            messagebox.showwarning("模拟输入无效", str(exc), parent=win)
            return
        show_line("模拟求职者", text, "candidate")
        if result.state == "stopped":
            show_line("系统", "该会话已停止联系，不再生成回复。", "notice")
            latest.update(id=None, reply="")
        else:
            show_line("自动生成草稿（未发送）", result.text, "reply")
            latest.update(id=result_id, reply=result.text)
        incoming.delete("1.0", "end")

    def copy_draft():
        if not latest["id"] or not latest["reply"]:
            messagebox.showinfo("提示", "请先生成草稿", parent=win)
            return
        body = worker.copy_prepared(session.get().strip(), latest["id"])
        if body:
            win.clipboard_clear()
            win.clipboard_append(body)
            show_line("系统", "已复制草稿到剪贴板；未向 BOSS 发送。", "notice")

    def new_session():
        session.set("demo:chat-" + uuid.uuid4().hex[:8])
        latest.update(id=None, reply="")
        show_line("系统", "已切换到新的虚拟测试会话，历史隔离。", "notice")

    row = ttk.Frame(win)
    row.pack(fill="x", padx=18, pady=(2, 15))
    ttk.Button(row, text="生成模拟回复", command=simulate).pack(side="left")
    ttk.Button(row, text="复制草稿（不发送）", command=copy_draft).pack(side="left", padx=8)
    ttk.Button(row, text="新建测试会话", command=new_session).pack(side="left")

    def shutdown():
        worker.close()
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", shutdown)
    return win
