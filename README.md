# SuperShop — Retail Inventory Management and Billing (POS) System

A complete retail Point of Sale (POS) and Inventory Management System built with **Django**, **Python**, **Bootstrap 5**, and client-side reactive **JavaScript**.

---

## 🚀 Key Features

* **Point of Sale (POS) Billing:** Dual-pane reactive cashier terminal with real-time subtotal and total calculations without page reloads.
* **Atomic Checkout:** Database operations wrapped in `transaction.atomic()` to guarantee all-or-nothing consistency and prevent orphaned sale records.
* **Inventory & Restocking:** Dynamic stock tracking, configurable low-stock threshold alerts (`stock < 3`), and a consolidated low-stock alert hub with one-click inline restocking.
* **Role-Based Access Control (RBAC):** Custom `@admin_required` decorators ensuring staff cashiers only access billing and receipts, while administrators access inventory, user management, and revenue analytics.
* **Invoice Generation & Printing:** Clean printable receipt/invoice format with `@media print` styling that hides navigation bars.
* **Business Analytics & Reporting:** Real-time dashboards displaying daily revenue, top-selling items, and longitudinal sales trends.
* **Self-Service Password Management:** Integrated password change functionality for all authenticated users.

---

## 🛠️ Incremental Development Process Model

This project was developed following the **Incremental Process Model**:

1. **Increment 1: Core Setup & POS Billing Engine**
   - Base project setup and architecture
   - `Category`, `Product`, `Sale`, and `SaleItem` models (`0001_initial.py`)
   - Product and Category CRUD management
   - POS checkout interface and printable invoice generation
2. **Increment 2: Inventory Tracking & Low-Stock Alerts Hub**
   - Stock deduction upon sale completion
   - Global unread low-stock counter context processor (`low_stock_count`)
   - Dedicated low-stock alert console (`/inventory/low-stock/`) with inline instant restocking
3. **Increment 3: Role-Based Access Control & User Security**
   - Role partitioning: Cashier (Staff) vs Store Manager (Admin)
   - `@admin_required` route protection decorators
   - User provisioning and user list management
   - Self-service password change module
4. **Increment 4: Business Intelligence & Revenue Analytics**
   - Daily sales summary with transaction counter
   - Top 10 product ranking by units sold and revenue
   - Longitudinal revenue analysis with 7-day trend chart
5. **Increment 5: Quality Assurance, Bug Fixes & Automated TDD Suite**
   - Fixed ghost sale creation via pre-allocation stock validation
   - Migration `0003_saleitem_safe_delete.py` to prevent cascade loss on product deletion
   - Full 18-test suite in `core/tests.py` covering Models, Billing, RBAC, Alerts, and Password management (100% pass)

---

## 💻 Tech Stack

* **Backend:** Python 3.13, Django 6.1
* **Database:** SQLite (ACID-compliant with atomic transactions)
* **Frontend:** Bootstrap 5, Bootstrap Icons, HTML5, Vanilla JavaScript (Event-driven DOM updates)
* **Testing:** Django `TestCase`, Python `unittest`, `unittest.mock`

---

## 📦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Hi-There-shuvo/Inventory-and-Billing-System.git
   cd Inventory-and-Billing-System
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **(Optional) Seed sample data:**
   ```bash
   python manage.py seed_data
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   Open `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running Automated Tests

Run the complete 18-test automated suite:
```bash
python manage.py test
```

For verbose test-by-test results:
```bash
python manage.py test -v 2
```

---

## 📄 License
Academic and educational project for **CSE-3206: Software Engineering Lab**.
