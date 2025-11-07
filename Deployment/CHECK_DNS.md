# DNS 配置檢查指南

## 當前 DNS 解析結果

根據您的 `nslookup` 輸出，域名 `countclimbingscore.online` 解析到多個 IP：

```
76.223.105.230
13.248.243.5
3.26.6.19  ✅ (正確的 EC2 IP)
```

## 問題分析

### ✅ 好消息
- `3.26.6.19` 在解析結果中，說明 DNS 配置基本正確

### ⚠️ 需要注意
- 有額外的 IP 地址（`76.223.105.230` 和 `13.248.243.5`）
- 這可能導致訪問不穩定或指向錯誤的服務器

## 可能的原因

### 1. 配置了多個 A 記錄

**檢查方法**：
- 登入域名註冊商的 DNS 管理界面
- 查看是否有**多條** A 記錄指向不同的 IP

**解決方法**：
- 刪除所有指向其他 IP 的 A 記錄
- 只保留一條指向 `3.26.6.19` 的 A 記錄

### 2. 使用了 CDN 或代理服務（如 Cloudflare）

**檢查方法**：
```bash
# 檢查是否使用 Cloudflare
curl -I https://countclimbingscore.online | grep -i cloudflare

# 或查看 DNS 服務器
nslookup -type=NS countclimbingscore.online
```

**如果使用 Cloudflare**：
- 額外的 IP 是 Cloudflare 的代理服務器（正常）
- 確保 Cloudflare 的代理設置正確
- 確保 "DNS only" 模式或 "Proxied" 模式配置正確

### 3. DNS 仍在傳播中

**檢查方法**：
```bash
# 使用在線工具檢查全球 DNS 傳播
# https://www.whatsmydns.net/#A/countclimbingscore.online
```

**解決方法**：
- 等待更長時間（最多 48 小時）
- 清除本地 DNS 緩存

## 建議的修復步驟

### 步驟 1: 檢查 DNS 配置

登入您的域名註冊商，確認 DNS 記錄：

**應該只有**：
```
類型    主機記錄    值            TTL
A       @          3.26.6.19     600
A       www        3.26.6.19     600
```

**不應該有**：
- 指向 `76.223.105.230` 的 A 記錄
- 指向 `13.248.243.5` 的 A 記錄
- 其他指向不同 IP 的 A 記錄

### 步驟 2: 清理多餘的 DNS 記錄

1. 刪除所有指向其他 IP 的 A 記錄
2. 只保留指向 `3.26.6.19` 的記錄
3. 等待 DNS 傳播（5 分鐘到 48 小時）

### 步驟 3: 驗證修復

```bash
# 等待一段時間後再次檢查
nslookup countclimbingscore.online

# 應該只返回 3.26.6.19
```

## 當前狀態評估

### ✅ 可以繼續配置 SSL

雖然有多個 IP，但 `3.26.6.19` 在列表中，**可以嘗試配置 SSL**：

```bash
sudo certbot --nginx -d countclimbingscore.online -d www.countclimbingscore.online
```

**注意**：
- Certbot 會驗證域名所有權
- 如果訪問到錯誤的 IP，驗證可能會失敗
- 建議先清理多餘的 DNS 記錄

### ⚠️ 建議先修復 DNS

為了確保穩定性，建議：
1. 先清理多餘的 DNS 記錄
2. 等待 DNS 完全生效（只返回 `3.26.6.19`）
3. 再配置 SSL 證書

## 快速檢查命令

```bash
# 檢查 DNS 解析
nslookup countclimbingscore.online

# 使用 dig 獲取更詳細信息
dig countclimbingscore.online +short

# 檢查特定 IP 是否在結果中
nslookup countclimbingscore.online | grep "3.26.6.19"

# 在線檢查（全球 DNS 傳播）
# https://www.whatsmydns.net/#A/countclimbingscore.online
```

## 下一步

1. **如果使用 Cloudflare 或其他 CDN**：
   - 確保代理設置正確
   - 額外的 IP 是正常的（CDN 節點）

2. **如果沒有使用 CDN**：
   - 清理多餘的 DNS 記錄
   - 只保留指向 `3.26.6.19` 的記錄
   - 等待 DNS 傳播完成

3. **配置 SSL**：
   - 可以嘗試配置（如果驗證失敗，先修復 DNS）
   - 或等待 DNS 清理完成後再配置

