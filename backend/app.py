# -*- coding: utf-8 -*-

# 導入必要的函式庫
from flask import Flask, request, jsonify, send_from_directory  # 確保導入 send_from_directory
from flask_cors import CORS
import jwt                     # 用於 JWT 操作
import datetime                # 用於設定 JWT 到期時間
import os
from datetime import date      # 用於資料庫中的日期

# 假設 models.py 定義了 db 和 Client 模型
from models import db, Client
# 假設 config.py 定義了 Config 類別
from config import Config      # 明確導入 Config

# --- Flask App 初始化 ---
app = Flask(__name__, static_folder=None)  # 設置 static_folder=None 以避免與自定義路由衝突
app.config.from_object('config.Config')      # 從設定檔載入設定
CORS(app)                                    # 啟用 CORS，允許跨來源請求
db.init_app(app)                             # 初始化資料庫綁定

# --- JWT 驗證函數 ---
def verify_jwt(token):
    """驗證傳入的 JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        print("JWT Token 已過期")
        return None
    except jwt.InvalidTokenError as e:
        print(f"無效的 JWT Token: {e}")
        return None
    except Exception as e:
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
    # 目前使用明文密碼比較，僅適用於測試環境；生產環境必須使用安全的密碼 Hashing 函數
    if client and client.password_hash == password:
        try:
            payload = {
                'username': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
            return jsonify({'token': token})
        except Exception as e:
            print(f"生成 JWT Token 時發生錯誤: {e}")
            return jsonify({"error": "無法生成 Token"}), 500
    else:
        return jsonify({'error': '帳號或密碼錯誤'}), 401

@app.route('/api/policy/cost', methods=['GET'])
def get_policy_cost():
    # --- 完整 JWT 驗證邏輯 ---
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        print("[ERROR] Missing or invalid Authorization header")
        return jsonify({'error': '缺少或無效的 Authorization header'}), 401
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            print("[ERROR] Malformed Authorization header")
            return jsonify({'error': '無效的 Authorization header format'}), 401
    else:
        token = auth_header

    payload = verify_jwt(token)
    if not payload:
        return jsonify({'error': '無效或過期的 token'}), 401
    # --- END: 完整 JWT 驗證邏輯 ---

    username = payload.get('username')
    if not username:
        print("[ERROR] Username not found in token payload")
        return jsonify({'error': '無法從 token 中獲取使用者名稱'}), 401

    print(f"[INFO] Processing /api/policy/cost request for user: {username}")
    client = Client.query.filter_by(username=username).first()
    if not client:
        print(f"[WARN] Client data not found for user: {username}")
        return jsonify({'error': '找不到客戶資料'}), 404

    if client.policy_cost is not None:
        print(f"[INFO] Returning policy cost for user: {username}")
        return jsonify({'policy_cost': client.policy_cost})
    else:
        print(f"[WARN] Policy cost data not available for user: {username}")
        return jsonify({'error': '此使用者沒有保單費用資料'}), 404

@app.route('/api/policy/date', methods=['GET'])
def get_policy_date():
    # --- 完整 JWT 驗證邏輯 ---
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        print("[ERROR] Missing or invalid Authorization header")
        return jsonify({'error': '缺少或無效的 Authorization header'}), 401
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({"error_message": "無效的 Authorization header format"}), 401
    else:
        token = auth_header

    payload = verify_jwt(token)
    if not payload:
        return jsonify({'error': '無效或過期的 token'}), 401
    # --- END: 完整 JWT 驗證邏輯 ---

    username = payload.get('username')
    if not username:
        print("[ERROR] Username not found in token payload")
        return jsonify({'error': '無法從 token 中獲取使用者名稱'}), 401

    print(f"[INFO] Processing /api/policy/date request for user: {username}")
    client = Client.query.filter_by(username=username).first()
    if not client:
        print(f"[WARN] Client data not found for user: {username}")
        return jsonify({'error': '找不到客戶資料'}), 404

    if client.policy_due_date is not None:
        print(f"[INFO] Returning policy due date for user: {username}")
        return jsonify({'policy_due_date': client.policy_due_date.strftime('%Y-%m-%d')})
    else:
        print(f"[WARN] Policy due date data not available for user: {username}")
        return jsonify({'error': '此使用者沒有保單付款日期資料'}), 404

@app.route('/api/policy/function', methods=['POST'])
def policy_function():
    """
    接受包含 action 參數的 JSON 請求，
    action 可為 "get_cost" (查詢費用) 或 "get_date" (查詢日期)，
    根據 action 查詢並回傳對應的保單費用或下次繳款日期，
    回應格式符合 Function 工具的輸入輸出參數 schema。
    """
    # --- 完整 JWT 驗證邏輯 ---
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error_message": "缺少或無效的 Authorization header"}), 401
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({"error_message": "無效的 Authorization header format"}), 401
    else:
        token = auth_header

    payload = verify_jwt(token)
    if not payload:
        return jsonify({"error_message": "無效或過期的 token"}), 401

    username = payload.get('username')
    if not username:
        return jsonify({"error_message": "無法從 token 中獲取使用者名稱"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error_message": "請求主體必須是 JSON 格式"}), 400

    action = data.get('action')
    if not action:
        return jsonify({"error_message": "缺少必要的 action 參數"}), 400

    client = Client.query.filter_by(username=username).first()
    if not client:
        return jsonify({"error_message": "找不到客戶資料"}), 404

    if action == "get_cost":
        if client.policy_cost is not None:
            return jsonify({"policy_cost": client.policy_cost, "error_message": ""})
        else:
            return jsonify({"error_message": "此使用者沒有保單費用資料"}), 404
    elif action == "get_date":
        if client.policy_due_date is not None:
            return jsonify({"policy_date": client.policy_due_date.strftime('%Y-%m-%d'), "error_message": ""})
        else:
            return jsonify({"error_message": "此使用者沒有保單付款日期資料"}), 404
    else:
        return jsonify({"error_message": "無效的 action: " + str(action)}), 400

def initialize_or_update_client(username, password, policy_num, cost, due_date_obj):
    """初始化或更新客戶資料的輔助函數"""
    client = Client.query.filter_by(username=username).first()
    password_to_store = password  # 測試用明文，實際應 hash

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

with app.app_context():
    print("正在建立資料庫表格...")
    db.create_all()
    print("正在初始化/更新客戶資料...")
    initialize_or_update_client("user1", "pass1", "1212", "NT$15000", date(2025, 5, 15))
    initialize_or_update_client("user2", "pass2", "3434", "NT$20000", date(2025, 6, 20))
    print("資料庫初始化完成。")

@app.route('/health')
def health_check():
    return "OK", 200

@app.route('/')
def index():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.abspath(os.path.join(current_dir, '../frontend'))
    file_path = os.path.join(frontend_dir, 'index.html')
    print(f"[DEBUG] Root request: frontend_dir='{frontend_dir}', file_path='{file_path}'")
    exists = os.path.exists(file_path)
    print(f"[DEBUG] Root request: index.html exists? {exists}")
    if not exists:
        return "Internal Server Error: index.html not found at expected path.", 500
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.startswith('api/'):
        return "Not Found", 404
    frontend_dir = os.path.join(app.root_path, '../frontend')
    file_path = os.path.join(frontend_dir, filename)
    print(f"[DEBUG] Static request: Serving '{filename}'. frontend_dir='{frontend_dir}', file_path='{file_path}'")
    exists = os.path.exists(file_path)
    print(f"[DEBUG] Static request: '{filename}' exists? {exists}")
    if not exists:
        return f"{filename} not found", 404
    return send_from_directory(frontend_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_mode = app.config.get('DEBUG', False)
    print(f"啟動 Flask 伺服器於 Port {port}，偵錯模式: {debug_mode}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)