# HRBOSS 衍生版：Windows 公开登录页核验候选

基于 `zhbo192883/HRBOSS` 固定提交 `053ad93c2c585fe8d97eb531baa6a70493284f85` 和其 MIT 许可证修改。此候选版只打开独立 Chrome 的 BOSS 官方**公开登录页**；真实候选人读取、发送、主动搜索、批量打招呼、复聊唤醒及付费模型调用均锁定。原招聘助手 v0.1.26 和其中的 325158 字节聊天存档、Windows 加密 Key 保持原样；不直接复制或解密。

原 HRBOSS 所依赖的 DrissionPage 许可证禁止未经授权的商业使用。本候选版不包含 DrissionPage、requests 或开放的远程调试端口。构建产物是内置 Python/Tkinter 的单个 Windows EXE，Windows 用户不需安装 Python。

本地源码回归：`PYTHONPATH=hrboss_app python3 -m unittest discover -s hrboss_app/tests -v`。Windows 构建工作流模板为 `windows-build.yml`，必须在 Windows runner 上运行；macOS 产物不能当作 Windows EXE。构建成功后还需在 zhaopin 上双击启动并只读核验官方公开页。未获平台接入许可和页面适配证据前，不能开启真实自动接待或让 Owner 输入验证码。
