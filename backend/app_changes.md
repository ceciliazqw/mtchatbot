# Backend API Policy Endpoint Modification

## 目標說明
本次修改目標在於讓 `/api/policy` 端點能夠根據 Agent Builder Tool 的請求，根據 URL 查詢參數 `field` 回傳特定的保單資訊。具體而言：
- 當 `field` 為 `"cost"` 時，回傳 JSON 格式：  
  `{ "policy_cost": <client.policy_cost> }`
- 當 `field` 為 `"date"` 時，回傳 JSON 格式：  
  `{ "policy_due_date": <client.policy_due_date in YYYY-MM-DD format> }`
  
此外，必須使用 JWT Token 進行身份驗證，並確保僅回傳工具請求的那個欄位。另外，由於不使用 webhook 功能，請將 `/api/webhook` 端點移除或註解。

## 必要修改說明

1. **身份驗證**  
   - 在 `/api/policy` 端點中，須檢查 HTTP Header `Authorization` 是否存在，並使用現有的 `verify_jwt` 函數驗證 Token 合法性。
   - 若驗證失敗，回傳 HTTP 401 錯誤。

2. **查詢參數處理**  
   - 使用 `request.args.get('field')` 讀取 URL 查詢參數 `field`，此參數決定回傳哪個欄位：
     - 若 `field` 為 `"cost"`，僅回傳 `policy_cost`。
     - 若 `field` 為 `"date"`，僅回傳 `policy_due_date`，以 `YYYY-MM-DD` 形式格式化。
   - 若 `field` 參數缺失或無效，回傳 HTTP 400 錯誤與錯誤訊息。

3. **資料查詢**  
   - 從查詢參數中也可取得 `username`（或從 token 中解析），依此從資料庫中查詢對應的 Client 資料。
   - 若找不到使用者資料，回傳 HTTP 404 錯誤。

4. **回傳格式**  
   - 根據 `field` 的值，回傳單一 JSON 物件。確保 JSON key 固定：
     - 當 `field` 為 `"cost"`：`{ "policy_cost": client.policy_cost }`
     - 當 `field` 為 `"date"`：`{ "policy_due_date": client.policy_due_date.strftime('%Y-%m-%d') }`

5. **移除 Webhook**  
   - 請移除或註解掉 `/api/webhook` 端點及其相關函數，避免混淆。

## Sample Code Snippet
以下提供一個範例程式碼片段，可參考實作於 `backend/app.py`：

```python
@app.route('/api/policy', methods=['GET'])
def get_policy():
    # 驗證 Authorization Header 與 JWT Token
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Missing Authorization header"}), 401
    token = auth_header.split(" ")[1]
    if not verify_jwt(token):
        return jsonify({"error": "Invalid token"}), 401

    # 從查詢參數獲取 username 與 field
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400

    client = Client.query.filter_by(username=username).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404

    field = request.args.get('field')
    if not field:
        return jsonify({"error": "Field parameter is required"}), 400

    if field == "cost":
        return jsonify({"policy_cost": client.policy_cost})
    elif field == "date":
        return jsonify({"policy_due_date": client.policy_due_date.strftime('%Y-%m-%d')})
    else:
        return jsonify({"error": "Invalid field parameter"}), 400
```

## 測試步驟
- 刪除或註解 `/api/webhook` 端點。
- 使用以下 GET 請求測試 `/api/policy` 端點：
  - 查詢保費金額：  
    `GET /api/policy?username=user1&field=cost`  
    預期回應： `{ "policy_cost": "NT$15000" }`
  - 查詢繳費日期：  
    `GET /api/policy?username=user1&field=date`  
    預期回應： `{ "policy_due_date": "2025-05-15" }`

## 與 Agent Builder Tool 整合
- 在 Agent Builder 中配置工具時，設定上述的 Input Parameter Schema (包含 username 與 field) 與 Output Parameter Schema 對應相應查詢結果。
- 當 Agent 判斷用戶的查詢意圖時，根據對話上下文中的 username，工具會呼叫 `/api/policy` 端點並傳遞 `field` 參數，從而精準回傳查詢結果。

以上修改將使得您的後端 API 能夠精確根據 Agent Builder Tool 的要求，只返回查詢需求的單一欄位數據，同時保持安全的身份驗證機制。