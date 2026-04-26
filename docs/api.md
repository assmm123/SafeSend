# توثيق API - Core Foundation
# API Documentation - Core Foundation

## 📋 المصادقة - Authentication

### POST /api/v1/auth/register
تسجيل مستخدم جديد | Register new user

**Request:**
```json
{
    "email": "user@example.com",
    "username": "username",
    "password": "SecurePass123!",
    "full_name": "Full Name"
}
```

Response:

```json
{
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "username"
}
```

---

POST /api/v1/auth/login

تسجيل الدخول | Login

Request:

```json
{
    "email": "user@example.com",
    "password": "SecurePass123!"
}
```

Response:

```json
{
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "user": { ... }
}
```

---

POST /api/v1/auth/logout

تسجيل الخروج | Logout

Headers:

```
Authorization: Bearer <access_token>
```

---

POST /api/v1/auth/refresh

تحديث التوكن | Refresh token

Request:

```json
{
    "refresh_token": "refresh_token"
}
```

---

📋 المستخدمين - Users

GET /api/v1/users/me

جلب الملف الشخصي | Get profile

PUT /api/v1/users/me

تحديث الملف الشخصي | Update profile

POST /api/v1/users/me/change-password

تغيير كلمة المرور | Change password

POST /api/v1/users/verify-email

التحقق من البريد | Verify email

POST /api/v1/users/forgot-password

نسيت كلمة المرور | Forgot password

POST /api/v1/users/reset-password

إعادة تعيين كلمة المرور | Reset password

---

📋 الصفقات - Deals

GET /api/v1/deals

قائمة الصفقات | List deals

Query Parameters:

· status: pending, funded, completed
· page: رقم الصفحة
· limit: عدد العناصر

POST /api/v1/deals

إنشاء صفقة | Create deal

Request:

```json
{
    "title": "Deal Title",
    "description": "Description",
    "seller_id": "uuid",
    "buyer_id": "uuid",
    "amount": 1000.00,
    "currency": "USDT"
}
```

GET /api/v1/deals/{id}

تفاصيل الصفقة | Get deal

PUT /api/v1/deals/{id}/status

تحديث حالة الصفقة | Update deal status

---

📋 المحادثات - Conversations

GET /api/v1/conversations

قائمة المحادثات | List conversations

POST /api/v1/conversations

إنشاء محادثة | Create conversation

GET /api/v1/conversations/{id}

تفاصيل المحادثة | Get conversation

---

📋 الرسائل - Messages

GET /api/v1/conversations/{id}/messages

رسائل المحادثة | Get messages

POST /api/v1/conversations/{id}/messages

إرسال رسالة | Send message

PUT /api/v1/messages/{id}/read

تعليم كمقروء | Mark as read

---

📋 سجل التدقيق - Audit Logs

GET /api/v1/audit-logs

سجل التدقيق | Get audit logs

Query Parameters:

· user_id: تصفية حسب المستخدم
· action: تصفية حسب الإجراء
· resource: تصفية حسب المورد

---

📋 الإحصائيات - Statistics

GET /api/v1/stats/users

إحصائيات المستخدمين | User statistics

GET /api/v1/stats/deals

إحصائيات الصفقات | Deal statistics

---

📋 النسخ الاحتياطي - Backup

POST /api/v1/backup

إنشاء نسخة احتياطية | Create backup

GET /api/v1/backup

قائمة النسخ | List backups

POST /api/v1/backup/{id}/restore

استعادة نسخة | Restore backup

---

🔒 رموز الحالة - Status Codes

Code Description
200 نجاح
201 تم الإنشاء
400 بيانات غير صالحة
401 غير مصرح
403 محظور
404 غير موجود
409 تعارض
500 خطأ في الخادم

---

📊 نماذج البيانات - Data Models

User

```json
{
    "id": "uuid",
    "email": "string",
    "username": "string",
    "full_name": "string",
    "role": "user|admin|moderator",
    "is_active": true,
    "is_verified": false,
    "created_at": "datetime"
}
```

Deal

```json
{
    "id": "uuid",
    "title": "string",
    "description": "string",
    "seller_id": "uuid",
    "buyer_id": "uuid",
    "amount": "decimal",
    "currency": "USDT|USD",
    "status": "pending|funded|completed|cancelled",
    "created_at": "datetime"
}
```

Message

```json
{
    "id": "uuid",
    "conversation_id": "uuid",
    "sender_id": "uuid",
    "content": "string",
    "content_type": "text|image|file",
    "is_read": false,
    "created_at": "datetime"
}
```

