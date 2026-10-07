# Multi-Agent AI Healthcare Assistant

This project contains a frontend application (HTML/CSS/JS) and a backend application (Flask/PostgreSQL).

## How to Run the Project

To avoid "Network error" alerts, both the frontend and backend must be running.

### 1. Start the Backend Server
The backend is a Flask API running on port `5000`.

- **On Windows**:
  Double-click the [start-backend.bat](file:///c:/projects/Multi-Agent%20AI%20Assistant/start-backend.bat) script in the root folder.
  
  *Alternatively, via PowerShell/Command Prompt:*
  ```bash
  cd backend
  venv\Scripts\activate
  python run.py
  ```

- **On macOS/Linux**:
  ```bash
  cd backend
  source venv/bin/activate
  python run.py
  ```

### 2. Start the Frontend
The frontend connects to the backend at `http://localhost:5000`.
- Open `frontend/login.html` or `frontend/register.html` in your browser (e.g., using the VS Code **Live Server** extension which runs on `http://127.0.0.1:5500`).

---

## Troubleshooting

### "Network error. Please try again."
If you see this error when trying to Register or Sign In, it means the frontend is unable to communicate with the Flask backend. 
- Ensure you have started the backend server using the steps above.
- Make sure the terminal window running the backend shows: `* Running on http://127.0.0.1:5000` or `* Running on http://localhost:5000`.
