# Orvanta — Business Operations and Order Management Platform

A centralized web-based business operations and order management platform built with Django and PostgreSQL (Supabase). Orvanta helps small businesses (furniture makers, print shops, repair services, custom contractors) organize customers, track itemized orders, handle status workflows, and manage operations in one unified system.

---

## 📌 Project Information
- **Course**: CSIT327 – Information Management 2
- **Increment**: Project Development 2 – Core Feature (Vertical Slice)
- **Author**: Danielle D. Manguilimotan
- **Section**: IT317 - G5 / G2

---

## 🚀 Implemented Features

### 1. Standard Features (Project Development 1)
- **Account Registration**: Create business owner or staff accounts with validation.
- **Authentication**: Secure login and logout with session management and user data isolation.
- **Role-Based User Dashboards**: Distinct dashboards for `Owner` and `Staff` displaying relevant metrics, order queues, and action triggers.
- **User Profile Management**: View and edit user details, business name, and contact information.

### 2. Core Feature — Order Management (Vertical Slice)
Order Management is the central engine of Orvanta, implementing a full vertical slice through the database, backend logic, and user interface:
- **Customer Management**:
  - Full CRUD operations for business clients (`Customer` model).
  - Business rules: Full name + at least one contact method (email or phone) required (BR-14).
  - Archive/restore capability preserving order history integrity (BR-16).
- **Custom Order Categories (`OrderType`)**:
  - Flexible categories tailored to business needs (e.g. Custom Furniture, Repair, Bulk Orders).
- **Itemized Orders (`Order` & `OrderItem`)**:
  - Auto-generated sequential order numbers (`ORD-YYYY-NNNN`).
  - Itemized line items with dynamic line total calculation ($quantity \times unit\_price$) and automatic order total recalculation.
  - Required validation: at least 1 line item required per order (BR-21).
  - Date validations: deadline and fulfillment dates must be $\ge$ order date.
- **Order Status Tracking & Audit History (`OrderStatusHistory`)**:
  - Status progression workflow: `Pending` $\rightarrow$ `In Progress` $\rightarrow$ `Ready` $\rightarrow$ `Completed` / `Cancelled`.
  - Audit trail logging who modified the order, previous status, new status, timestamp, and remarks (BR-23, BR-25).
  - Timestamp tracking (`completed_at` recorded automatically upon completion).
- **Role-Based Permissions**:
  - **Owner**: Full CRUD (Create, Read, Update, Delete) and revenue analytics.
  - **Staff**: Operational CRUD (Create, Read, Update status); deletion is restricted to Owners.
- **User Data Isolation**: All customer, order, and audit records are strictly scoped to the authenticated user's business tenant.

---

## 🛠️ Technology Stack
- **Backend Framework**: Django 6.1.3 (Python 3.12)
- **Database**: PostgreSQL hosted on Supabase
- **Frontend**: Django Templates, Vanilla HTML5 & Responsive CSS3

---

## 💻 Setup & Installation Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/dmanguie/Orvanta-Manguilimotan-Danielle-G2.git
cd Orvanta-Manguilimotan-Danielle-G2
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Create a `.env` file in the project root with your Supabase PostgreSQL credentials:
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DB_NAME=postgres
DB_USER=postgres.xxxxxxxx
DB_PASSWORD=your-supabase-db-password
DB_HOST=aws-0-ap-northeast-1.pooler.supabase.com
DB_PORT=5432
```

### 5. Apply Database Migrations
```bash
python manage.py migrate
```

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running Automated Tests
```bash
python manage.py test customers orders
```

---

## 🌿 Git Branching Strategy
- **`main`**: Production-ready, stable releases.
- **`develop`**: Integration branch for ongoing development.
- **`feature/customer-management`**: Customer CRUD and data isolation.
- **`feature/order-management`**: Core feature vertical slice (Order, OrderItem, OrderStatusHistory).
