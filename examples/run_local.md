# 本地运行示例

1. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. 使用 CLI 运行样例输入并输出成果：
   ```bash
   python -m emenv.app.cli examples/request_basic_free_space.json --output-dir outputs/demo
   ```
3. 启动 REST 服务：
   ```bash
   uvicorn emenv.app.rest:app --reload
   ```
4. REST 测试：
   ```bash
   curl -X POST http://127.0.0.1:8000/compute -H "Content-Type: application/json" --data-binary "@examples/request_basic_free_space.json"
   curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" -d "{\"lat\": 33.90, \"lon\": 118.15, \"band\": \"S\"}"
   ```
