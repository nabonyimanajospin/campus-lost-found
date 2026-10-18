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

### REST API (JSON, base `http://127.0.0.1:8000/api/v1/`)

Authenticate with `Authorization: Token <token>` (get one from register/login). Lists are paginated (`?page=2`).

| Method | URL | Who | Description |
| :--- | :--- | :--- | :--- |
| POST | `auth/register/` | anyone | Create account + student profile, returns token |
| POST | `auth/login/` | anyone | `{email, password}` -> token (throttled 10/min) |
| POST | `auth/logout/` | logged in | Revoke the current token |
| GET / PATCH | `auth/me/` | logged in | Own profile (the only place contact details show) |
| GET | `students/` | staff | Student directory |
| GET | `categories/` | anyone | List categories (POST/PUT/DELETE: staff) |
| GET | `items/` | anyone | Filters: `?status=` `?category=` `?mine=true` `?search=` `?ordering=` |
| POST | `items/` | logged in | Report an item (owner comes from your token) |
| GET / PATCH / DELETE | `items/<id>/` | anyone / owner | Owner or staff can edit; returned items are frozen |
| POST | `items/<id>/mark-returned/` | owner | Close the item and reject pending claims |
| GET | `claims/` | logged in | Only claims you made or received. `?role=claimant\|owner` `?item=` `?status=` |
| POST | `claims/` | logged in | `{item, message}`; cannot claim your own or a returned item |
| POST | `claims/<id>/approve/` | item owner | Approves, marks item returned, rejects rival claims, reveals contacts |
| POST | `claims/<id>/reject/` | item owner | Reject a pending claim |
| POST | `claims/<id>/withdraw/` | claimant | Withdraw your pending claim |

Invalid state changes return `409 Conflict`; validation problems return `400`.

Run the tests with `python manage.py test`.

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
