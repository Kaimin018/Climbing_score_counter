// 主 JavaScript 文件
// 通用功能可以在這裡定義

console.log('攀岩計分系統已載入');

       // 檢查用戶登錄狀態並更新導航欄
       function updateUserInfo() {
           fetch('/api/auth/current-user/', {
               credentials: 'include'
           })
           .then(response => {
               if (response.ok) {
                   return response.json();
               } else {
                   throw new Error('未登錄');
               }
           })
           .then(user => {
               // 顯示用戶信息
               const userInfo = document.getElementById('userInfo');
               const usernameDisplay = document.getElementById('usernameDisplay');
               if (userInfo && usernameDisplay) {
                   // 如果是訪客用戶，顯示特殊標識
                   const displayName = user.username.startsWith('guest_') 
                       ? '訪客' 
                       : user.username;
                   usernameDisplay.textContent = `歡迎，${displayName}`;
                   userInfo.style.display = 'inline-block';
               }
           })
           .catch(error => {
               // 隱藏用戶信息
               const userInfo = document.getElementById('userInfo');
               if (userInfo) {
                   userInfo.style.display = 'none';
               }
           });
       }

// 登出功能
function handleLogout() {
    if (!confirm('確定要登出嗎？')) {
        return;
    }

    fetch('/api/auth/logout/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include'
    })
    .then(response => {
        if (response.ok) {
            // 登出成功，重新載入頁面
            window.location.href = '/';
        } else {
            alert('登出失敗，請重試');
        }
    })
    .catch(error => {
        console.error('登出失敗:', error);
        alert('登出失敗，請重試');
    });
}

// 獲取 CSRF Token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 頁面載入時更新用戶信息
document.addEventListener('DOMContentLoaded', function() {
    updateUserInfo();
});








