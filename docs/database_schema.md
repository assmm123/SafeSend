# مخطط قاعدة البيانات - Database Schema
# Core Foundation

## 📊 الجداول - Tables

### users
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| email | VARCHAR(255) | Unique |
| username | VARCHAR(64) | Unique |
| password_hash | VARCHAR(255) | Hashed password |
| full_name | VARCHAR(255) | Full name |
| role | VARCHAR(50) | User role |
| is_active | BOOLEAN | Account status |
| is_verified | BOOLEAN | Email verified |
| deleted_at | TIMESTAMP | Soft delete |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |

### sessions
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| user_id | UUID | FK to users.id |
| refresh_token | VARCHAR(500) | Refresh token |
| ip_address | VARCHAR(45) | Client IP |
| user_agent | TEXT | Browser info |
| device_info | JSON | Device details |
| expires_at | TIMESTAMP | Expiry time |
| is_active | BOOLEAN | Session status |
| revoked_at | TIMESTAMP | Revocation time |

### audit_logs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| user_id | UUID | FK to users.id |
| action | VARCHAR(50) | Action type |
| resource | VARCHAR(50) | Resource type |
| resource_id | VARCHAR(36) | Resource ID |
| old_value | JSON | Before state |
| new_value | JSON | After state |
| ip_address | VARCHAR(45) | Client IP |
| severity | VARCHAR(20) | Log level |
| created_at | TIMESTAMP | Event time |

### deals
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| title | VARCHAR(200) | Deal title |
| description | TEXT | Description |
| seller_id | UUID | FK to users.id |
| buyer_id | UUID | FK to users.id |
| amount | NUMERIC(10,2) | Deal amount |
| currency | VARCHAR(10) | Currency |
| status | VARCHAR(20) | Deal status |
| deadline | TIMESTAMP | Expiry deadline |
| funded_at | TIMESTAMP | Fund time |
| completed_at | TIMESTAMP | Completion time |
| created_at | TIMESTAMP | Creation time |

### conversations
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| deal_id | UUID | FK to deals.id |
| buyer_id | UUID | FK to users.id |
| seller_id | UUID | FK to users.id |
| subject | VARCHAR(200) | Subject |
| status | VARCHAR(20) | Status |
| deleted_at | TIMESTAMP | Soft delete |
| last_message_at | TIMESTAMP | Last message |
| created_at | TIMESTAMP | Creation time |

### messages
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary Key |
| conversation_id | UUID | FK to conversations.id |
| sender_id | UUID | FK to users.id |
| content | TEXT | Message content |
| content_type | VARCHAR(20) | Content type |
| media_url | VARCHAR(500) | Media URL |
| is_read | BOOLEAN | Read status |
| read_at | TIMESTAMP | Read time |
| delivery_status | VARCHAR(20) | Delivery status |
| deleted_at | TIMESTAMP | Soft delete |
| reactions | JSON | Emoji reactions |
| created_at | TIMESTAMP | Creation time |

---

## 🔗 العلاقات - Relationships

```

users
├── sessions (1:N)
├── audit_logs (1:N)
├── deals (as seller) (1:N)
├── deals (as buyer) (1:N)
├── conversations (as buyer) (1:N)
├── conversations (as seller) (1:N)
└── messages (1:N)

deals
└── conversations (1:N)

conversations
└── messages (1:N)

messages
└── messages (reply_to) (self-referential)

```

---

## 📈 الفهارس - Indexes

| Table | Index | Columns |
|-------|-------|---------|
| users | ix_users_email | email |
| users | ix_users_username | username |
| users | ix_users_deleted_at | deleted_at |
| sessions | ix_sessions_user_id | user_id |
| sessions | ix_sessions_refresh_token | refresh_token |
| audit_logs | ix_audit_logs_user_id | user_id |
| audit_logs | ix_audit_logs_action | action |
| deals | ix_deals_seller_id | seller_id |
| deals | ix_deals_buyer_id | buyer_id |
| deals | ix_deals_status | status |
| conversations | ix_conversations_deal_id | deal_id |
| messages | ix_messages_conversation_id | conversation_id |
| messages | ix_messages_sender_id | sender_id |
