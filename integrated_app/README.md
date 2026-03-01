# integrated_app 目录说明

该目录原先包含与仓库根目录重复的 Streamlit 应用与页面文件，
已在工程去重中移除，避免双份代码并行维护。

## 当前唯一代码源

- 入口：`app.py`
- 页面：`pages/`
- 共享业务逻辑：`core/`

## 运行方式

请在**仓库根目录**执行：

```bash
streamlit run app.py
```
