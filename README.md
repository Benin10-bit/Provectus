![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![React](https://img.shields.io/badge/react-frontend-blue)
![License](https://img.shields.io/badge/license-MIT-green)

# ⚔️ Provectus

<p align="center">
  <b>Strategic study performance system for EsPCEx candidates</b>
</p>

<p align="center">
  A data-driven platform that transforms study data into actionable performance insights.
</p>

---

## 📊 Overview

**Provectus** is a performance analysis system designed to help candidates preparing for the **EsPCEx (Escola Preparatória de Cadetes do Exército)** monitor their study efficiency and optimize their preparation.

Instead of focusing only on study time, Provectus analyzes **real performance indicators**, combining:

- Question accuracy
- Study consistency
- Performance trends
- Topic mastery

The goal is simple:

> **Provide a clear answer to the question: _"If the exam were today, would I pass?"_**

---

## ✨ Features

- 📈 Performance analytics dashboard
- ⏱️ Study time tracking
- 🧠 Question accuracy monitoring
- 📊 Performance trend analysis
- 🎯 Topic weakness detection
- 📝 Essay evaluation tracking
- 📚 Simulated exam analysis
- 📉 Strategic performance indicators (IPR)

---

## 🧠 Core Concept

### IPR — Real Performance Index

Provectus introduces the **IPR (Índice de Performance Real)**.

The metric combines:

- Number of questions solved
- Accuracy rate
- Consistency of study
- Performance trends

This creates a **realistic indicator of exam readiness**, instead of relying only on hours studied.

---

## 🏗️ Architecture

```
Provectus
│
├── api/                  # FastAPI backend
│   └── app/
│       ├── models/
│       ├── schemas/
│       ├── routes/
│       ├── services/
│       └── main.py
│
├── frontend/             # React frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── lib/
│
└── README.md
```

---

## ⚙️ Tech Stack

### Backend

- **FastAPI**
- **SQLAlchemy**
- **PostgreSQL**
- **Pydantic**
- **Uvicorn**

### Frontend

- **React**
- **TypeScript**
- **Vite**
- **TailwindCSS**
- **shadcn/ui**
- **React Query**
- **Recharts**

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/provectus.git
cd provectus
```

---

## Backend Setup

### 2. Navigate to API folder

```bash
cd api
```

### 3. Create virtual environment

```bash
python -m venv venv
```

### 4. Activate environment

```bash
# Linux / Mac
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure database

Create an environment variable:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/provectus
```

### 7. Run the API

```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

---

## Frontend Setup

### 8. Navigate to frontend folder

```bash
cd frontend
```

### 9. Install dependencies

```bash
npm install
# or
bun install
```

### 10. Start development server

```bash
npm run dev
```

Application will be available at `http://localhost:5173`

---

## 🔗 Frontend ↔ Backend

The frontend communicates with the API at `http://localhost:8000`. Ensure both servers are running simultaneously.

---

## 📊 Project Philosophy

Provectus is based on three principles:

### 1️⃣ Measurable Discipline

Study effort must be **quantifiable**.

### 2️⃣ Real Performance

Hours studied are irrelevant if they do not produce **correct answers in exams**.

### 3️⃣ Strategy

Preparation without performance data leads to **inefficient study cycles**.

---

## 📸 Screenshots

_(Add screenshots of your dashboard here)_

```
docs/screenshots/dashboard.png
docs/screenshots/analytics.png
```

---

## 🛣️ Roadmap

Future planned features:

- 📱 Mobile responsive improvements
- 🤖 AI-assisted performance analysis
- 📊 Advanced study analytics
- 📚 Topic mastery heatmaps
- 🧠 Predictive approval probability

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/new-feature
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push the branch

```bash
git push origin feature/new-feature
```

5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 👨‍💻 Author

Developed by **Benicio Neto**