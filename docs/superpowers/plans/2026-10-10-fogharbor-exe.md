# 雾港守灯人单文件EXE

用户授权：将当前项目打包为可直接运行的EXE；沿用E盘制作约束。

- [x] 增加冻结资源/用户配置路径，兼容源码与EXE。
- [x] 编写桌面启动器，使用本EXE启动隐藏服务，自动端口、打开浏览器、关闭清理。
- [x] 构建白名单资源、Streamlit动态模块、图标与PyInstaller单文件配置，不包含真实.env。
- [x] 构建Windows x64单文件并验证Tk窗口、独立运行、剧情与沙盘、退出清理。
- [x] 更新README、验收证据、成品校验值并交付。

构建目录：E:/0/.runtime/build；PyInstaller缓存：E:/0/.runtime/pyinstaller；输出：E:/0/dist/Fogharbor.exe。
单文件解包：E:/0/.runtime/bundle；运行缓存：EXE旁.runtime；用户.env：EXE旁，真实Key不打包。

首轮实际浏览器发现Streamlit的AST魔法函数为动态导入，补充框架子模块收集后重新构建。

## 验收

- 成品：E:/0/dist/Fogharbor.exe，Windows x64单文件，104590716字节（99.7MiB）。
- SHA256：98ec8fa11802dc52f1b6545676624fd1fd6449c6d1b7b364d05cf80624c30585。
- 源码测试：82 passed；Ruff：All checks passed。
- 实际成品复制到独立目录，PATH清空；真实Tk窗口及图标加载成功（验证时隐藏窗口）。
- 剧情：105次移动、21回合、四敌人、支线、首领及结局；鼠标/键盘/小屏/复盘/海报/重开通过。
- 沙盘：Plotly实际点击、非法移动、六场战斗、胜利、复盘、海报与重置通过。
- 验证通过同一关闭回调停止两个服务，并确认两个端口不再响应。
- EXE资源清单检查：页面、Canvas JS/CSS、工作流、素材许可证与Tk资源完整；没有.env或secrets.toml。
- 成品验证记录：artifacts/exe-verification.json；截图保存在artifacts/。
- 可选DeepSeek/GPU工作流未使用真实Key或模型联调；离线游戏与海报占位已实测。
