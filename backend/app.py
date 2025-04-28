# -*- coding: utf-8 -*-

# 導入必要的函式庫
from flask import Flask, request, jsonify, send_from_directory # <-- 確保導入 send_from_directory
from flask_cors import CORS
import jwt                     # 用於 JWT 操作
import datetime                # 用於設定 JWT 到期時間
import os
from datetime import date      # 用於資料庫中的日期

# 假設 models.py 定義了 db 和 Client 模型
from models import db, Client
# 假設 config.py 定義了 Config 類別
from config import Config      # <-- 明確導入 Config

# --- Flask App 初始化 ---
app = Flask(__name__, static_folder=None) # 可以設置 static_folder=None 避免與自定義路由衝突
# 從設定檔載入設定 (使用 config.py 中的 Config 類別)
app.config.from_object('config.Config')
CORS(app) # 啟用 CORS，允許跨來源請求
db.init_app(app) # 初始化資料庫綁定

# --- JWT 驗證函數 (真實實現) ---
def verify_jwt(token):
    """驗證傳入的 JWT token"""
    try:
        # 使用設定的 SECRET_KEY 解碼並驗證 token
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload # 回傳解碼後的 payload
    except jwt.ExpiredSignatureError:
        # Token 已過期
        print("JWT Token 已過期")
        return None
    except jwt.InvalidTokenError as e:
        # 無效 Token (格式錯誤、簽名不符等)
        print(f"無效的 JWT Token: {e}")
        return None
    except Exception as e:
        # 其他解碼時發生的錯誤
        print(f"解碼 JWT Token 時發生錯誤: {e}")
        return None

# --- API 端點 ---

@app.route('/api/login', methods=['POST'])
def login():
    """處理使用者登入請求，驗證成功後回傳 JWT"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "請求主體必須是 JSON 格式"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "必須提供使用者名稱和密碼"}), 400

    client = Client.query.filter_by(username=username).first()

    # --- 安全性警告 ---
    # 目前使用明文密碼比較，僅適用於 **測試環境**。
    # **生產環境** 必須使用安全的密碼 Hashing 函數進行儲存和驗證
    if client and client.password_hash == password:
        try:
            # --- 生成 JWT Token (真實實現) ---
            payload = {
                'username': username,
                # 設定 token 有效期為 1 小時
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            # 使用 SECRET_KEY 和 HS256 演算法生成 token
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

            # 回傳包含 token 的 JSON
            return jsonify({'token': token})
        except Exception as e:
            print(f"生成 JWT Token 時發生錯誤: {e}")
            return jsonify({"error": "無法生成 Token"}), 500
    else:
        # 登入失敗，為了安全，回傳通用的錯誤訊息
        return jsonify({'error': '帳號或密碼錯誤'}), 401

@app.route('/api/policy', methods=['GET'])
def get_policy():
    """根據 JWT 和 'field' 查詢參數，獲取特定的保單資訊"""
    # 1. 從 Authorization Header 取得並驗證 JWT Token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({'error': '缺少或無效的 Authorization header'}), 401

    token = auth_header.split(" ")[1] # 取得 token 部分
    payload = verify_jwt(token) # 驗證 token
    if not payload:
        return jsonify({'error': '無效或過期的 token'}), 401

    # 2. 從已驗證的 JWT payload 中可靠地取得 username
    username = payload.get('username')
    if not username:
        return jsonify({'error': '無法從 token 中獲取使用者名稱'}), 401

    # 3. 根據 token 中的 username 查詢客戶資料
    client = Client.query.filter_by(username=username).first()
    if not client:
        return jsonify({'error': '找不到對應已驗證使用者的客戶資料'}), 404

    # 4. 從 URL 查詢參數獲取請求的欄位 ('field')
    requested_field = request.args.get('field')
    if not requested_field:
        return jsonify({'error': '缺少必要的查詢參數: field'}), 400

    # 5. 根據請求的欄位回傳對應的資料
    if requested_field == 'cost':
        if client.policy_cost is not None: # 檢查值是否存在
            return jsonify({'policy_cost': client.policy_cost})
        else:
            return jsonify({'error': '此使用者沒有保單費用資料'}), 404

    elif requested_field == 'date':
        if client.policy_due_date is not None: # 檢查值是否存在
            return jsonify({'policy_due_date': client.policy_due_date.strftime('%Y-%m-%d')})
        else:
            return jsonify({'error': '此使用者沒有保單付款日期資料'}), 404

    else:
        # 處理無效的 'field' 參數值
        return jsonify({'error': f'查詢參數 "field" 的值無效: {requested_field}。有效選項為 "cost" 或 "date"'}), 400

# --- 資料庫初始化輔助函數 ---
def initialize_or_update_client(username, password, policy_num, cost, due_date_obj):
    """初始化或更新客戶資料的輔助函數"""
    client = Client.query.filter_by(username=username).first()
    password_to_store = password # 測試用明文，實際應 hash

    if client:
        client.password_hash = password_to_store
        client.policy_number = policy_num
        client.policy_cost = cost
        client.policy_due_date = due_date_obj
        print(f"正在更新客戶: {username}")
    else:
        new_client = Client(
            username=username,
            password_hash=password_to_store,
            policy_due_date=due_date_obj,
            policy_number=policy_num,
            policy_cost=cost
        )
        db.session.add(new_client)
        print(f"正在建立新客戶: {username}")
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"初始化/更新客戶 {username} 時發生錯誤: {e}")

# --- 在 App Context 中執行資料庫初始化 ---
# with app.app_context():
#     print("正在建立資料庫表格...")
#     db.create_all() # 確保所有定義的模型對應的表格都已建立
#     print("正在初始化/更新客戶資料...")
#     initialize_or_update_client("user1", "pass1", "1212", "NT$15000", date(2025, 5, 15))
#     initialize_or_update_client("user2", "pass2", "3434", "NT$20000", date(2025, 6, 20))
#     print("資料庫初始化完成。")

# --- 新增：處理前端靜態文件的路由 ---
@app.route('/')
def index():
    # app.root_path 指的是 backend/ 目錄
    # os.path.join(app.root_path, '../frontend') 會正確指向 MINTAI WEB API/frontend/ 目錄
    frontend_dir = os.path.join(app.root_path, '../frontend')
    print(f"Serving index.html from: {frontend_dir}") # 加入 print 方便除錯
    # 檢查檔案是否存在 (可選，但有助於除錯)
    if not os.path.exists(os.path.join(frontend_dir, 'index.html')):
         print(f"Warning: index.html not found at {os.path.join(frontend_dir, 'index.html')}")
         return "index.html not found", 404 # 回傳明確錯誤
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    # 同上，路徑會指向 MINTAI WEB API/frontend/ 目錄
    frontend_dir = os.path.join(app.root_path, '../frontend')
    print(f"Serving static file: {filename} from: {frontend_dir}") # 加入 print 方便除錯
     # 檢查檔案是否存在 (可選)
    if not os.path.exists(os.path.join(frontend_dir, filename)):
         print(f"Warning: Static file {filename} not found at {os.path.join(frontend_dir, filename)}")
         return f"{filename} not found", 404 # 回傳明確錯誤
    return send_from_directory(frontend_dir, filename)

# --- 主程式進入點 ---
if __name__ == '__main__':
    # 從環境變數讀取 PORT，若無則預設為 88
    port = int(os.environ.get('PORT', 88))
    # 從設定檔讀取 DEBUG 模式，若無則預設為 False (更安全的預設)
    debug_mode = app.config.get('DEBUG', False) # 預設為 False
    print(f"啟動 Flask 伺服器於 Port {port}，偵錯模式: {debug_mode}")
    # 使用 host='0.0.0.0' 使伺服器可從區域網路訪問
    app.run(debug=debug_mode, host='0.0.0.0', port=port)