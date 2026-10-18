# Understanding the Campus Lost and Found Project

This guide explains the `campus_lost_found` Django project in simple language. It describes how the project handles MVT (Model-View-Template) web pages, HTML forms, database relationships, and Django REST Framework (DRF) Serializers & JSON APIs.

---

## 1. Project Structure & Applications

The `campus_lost_found` project consists of 4 main apps:

1. **`student`**: Manages campus students who can report items or make claims.
2. **`category`**: Classifies lost/found items (e.g. Electronics, Books, ID Cards, Keys).
3. **`item`**: Manages lost, found, and returned items.
4. **`claim`**: Tracks student claims on lost/found items.

```text
campus_lost_found/
├── manage.py
├── campus_lost_found/    (Global project configuration)
├── student/              (Student model, forms, views, serializers)
├── category/             (Category model, views, serializers)
├── item/                 (Item model, forms, views, serializers)
└── claim/                (Claim model, forms, views, serializers)
```

---

## 2. Database Models & Relationships

- **`Student` (`student/models.py`)**: Stores student details (`first_name`, `last_name`, `email`, `phone`).
- **`Category` (`category/models.py`)**: Stores item category names.
- **`Item` (`item/models.py`)**: Stores item posts (`title`, `description`, `location`, `status`, `created_by`).
  - Connects to `Student` via `ForeignKey(Student, on_delete=models.CASCADE)`.
- **`Claim` (`claim/models.py`)**: Stores claims submitted for items (`item`, `claimant`, `message`, `status`).
  - Connects to `Item` via `ForeignKey(Item)` and `Student` via `ForeignKey(Student)`.

---

## 3. Django REST Framework (DRF) & Serializers

Every app includes a `serializers.py` file to convert Python database models into JSON data for APIs:

- **`StudentSerializer`**: Converts student records and validates email formatting (`return email.lower()`).
- **`CategorySerializer`**: Converts category records into JSON.
- **`ItemSerializer`**: Converts item records into JSON.
- **`ClaimSerializer`**: Converts claim records into JSON.

---

## 4. All Project Endpoints Cheat Sheet

Start your server with `python manage.py runserver` from the project root.

### REST API Endpoints (Return / Accept JSON):
| App | Method | URL | Description |
| :--- | :--- | :--- | :--- |
| `student` | GET / POST | `http://127.0.0.1:8000/students/student-api/` | List all students / Register student |
| `category` | GET / POST | `http://127.0.0.1:8000/categories/category-api/` | List all categories / Create category |
| `item` | GET / POST | `http://127.0.0.1:8000/items/item-api/` | List all items / Create item post |
| `claim` | GET / POST | `http://127.0.0.1:8000/claims/claim-api/` | List all claims / Submit claim |

### HTML Web Page Endpoints (Render HTML Webpages):
| App | URL | Description |
| :--- | :--- | :--- |
| `student` | `http://127.0.0.1:8000/` | Home Page |
| `student` | `http://127.0.0.1:8000/students/` | HTML student list table |
| `student` | `http://127.0.0.1:8000/students/add/` | HTML student registration form |
| `category` | `http://127.0.0.1:8000/categories/` | HTML categories list |
| `category` | `http://127.0.0.1:8000/categories/add/` | HTML category creation form |
| `item` | `http://127.0.0.1:8000/items/` | HTML items list |
| `item` | `http://127.0.0.1:8000/items/add/` | HTML item report form |
| `claim` | `http://127.0.0.1:8000/claims/` | HTML claims list |
| `claim` | `http://127.0.0.1:8000/claims/add/` | HTML claim submission form |
