# Autonomous Customer Success Swarm

A multi-agent AI system for automating customer success operations using FastAPI, React, and LangGraph. The system orchestrates specialized agents to handle customer inquiries, process orders, verify policies, and generate resolutions.

## 🎯 Overview

This project implements an intelligent customer success platform that uses multiple AI agents working together to:
- **Triage** customer messages and extract intent
- **Fetch** order details from database
- **Verify** refund/return/exchange policies  
- **Generate** automated resolutions with return labels
- **Escalate** complex cases when needed

The system uses LangGraph for orchestration and Ollama for local LLM inference.

## ✨ Key Features (Latest Updates)

- **LLM-Powered Triage Engine**: Replaces rigid keyword rules with robust local LLM extraction for intent detection. It intrinsically understands general questions, nuances in multi-turn interactions, and manages casual conversation without failing the pipeline.
- **Context-Aware Memory Storage**: Persistent conversation state tracks message history over multiple turns. Enables agents to answer context-dependent follow-up queries without forcing users to repeat details.
- **Dynamic Order ID Resolution**: Actively prompts the user for an Order ID if missing, and gracefully resolves ambiguities when a single user has multiple associated orders.
- **Smart Routing**: Optimizes query handling by discerning isolated policy questions (handled directly by the Policy Agent) from active return/exchange execution requests (needing full Database pipelines).
- **Clean Session Management**: Both frontend and backend variables automatically reset on page reload or when initiating a new chat, ensuring a secure and clean state every session.
- **Comprehensive E2E Testing**: Extensive test coverage ensuring accuracy on intent routing, entity extraction, boundary conditions, and end-to-end PDF return label generation.

## 🏗️ Architecture

### Multi-Agent System

```
User Message
    ↓
[Triage Agent] → Extracts intent, urgency, order_id
    ↓
[Database Agent] → Fetches order details from PostgreSQL
    ↓
[Policy Agent] → Checks refund/return/exchange eligibility
    ↓
[Resolution Agent] → Generates response & return labels
    ↓
[Guard Agent] → Safety checks & escalation logic
    ↓
Response to User
```

### Agent Responsibilities

| Agent | Purpose | Key Functions |
|-------|---------|---------------|
| **Triage** | Classify user intent and extract entities | `run_triage()` |
| **Database** | Query order information | `fetch_order_details()` |
| **Policy** | Verify policy eligibility | `check_refund_policy()`, `check_return_policy()` |
| **Resolution** | Generate responses and actions | `run_agent_llm()` |
| **Guard** | Safety checks and escalation | `agent_guard()` |

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Orchestration**: LangGraph
- **LLM**: Ollama (local inference)
- **Database**: PostgreSQL with SQLAlchemy
- **Testing**: Pytest
- **Language**: Python 3.11+

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 4
- **State Management**: React Hooks
- **HTTP Client**: Axios
- **UI Components**: Framer Motion, Lucide React

### LLM Models (via Ollama)
- `mistral:instruct` - Primary reasoning model
- `llama3` - Alternative model
- `qwen2.5-7b-instruct` - Additional reasoning
- `mxbai-embed-large` - Embeddings

## 📋 Prerequisites

### Required Software
1. **Python 3.11+** - [Download](https://www.python.org/downloads/)
2. **Node.js 18+** - [Download](https://nodejs.org/)
3. **PostgreSQL 14+** - [Download](https://www.postgresql.org/download/)
4. **Ollama** - [Download](https://ollama.ai/)
5. **Git** - [Download](https://git-scm.com/)

### Ollama Models
After installing Ollama, pull the required models:
```bash
ollama pull llama3.2:latest
ollama pull mxbai-embed-large
ollama pull qwen2.5-7b-instruct
```

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Autonomous-Customer-Success-Swarm
```

### 2. Backend Setup

#### Create Virtual Environment
```bash
cd backend
python -m venv venv
```

#### Activate Virtual Environment
**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

## ⚙️ Configuration

### Database Setup

1. **Create PostgreSQL Database:**
```sql
CREATE DATABASE customer_success;
```

2. **Create Orders Table:**
```sql
CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    product VARCHAR(255),
    status VARCHAR(50),
    order_date DATE,
    delivered_date DATE,
    amount INTEGER,
    size VARCHAR(10)
);
```

3. **Insert Sample Data:**
```sql
INSERT INTO orders VALUES 
('11111', 'Wireless Headphones', 'Delivered', '2026-02-01', '2026-02-11', 2199, 'M'),
('22222', 'Running Shoes', 'Delivered', '2026-01-01', '2026-01-17', 3499, '10'),
('33333', 'Smart Watch', 'Shipped', '2026-02-15', NULL, 4999, 'One Size');
```

### Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cd backend
```

Add the following configuration:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=customer_success
DB_USER=postgres
DB_PASSWORD=Prj@1234

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Optional: HubSpot Integration
HUBSPOT_API_KEY=your_hubspot_key_here
```

**Note:** Update `DB_PASSWORD` and other credentials as needed.

## 🏃 Running the Application

### Start Backend Server

1. **Ensure Ollama is Running:**
```bash
# In a separate terminal
ollama serve
```

2. **Start FastAPI Server:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The frontend will be available at: `http://localhost:5173`

### Production Build (Frontend)

```bash
cd frontend
npm run build
npm run preview
```

## 🧪 Running Tests

### Backend Tests

The project includes unit tests, integration tests, and full End-to-End accuracy evaluation scripts.

#### Run Standard Unit/Integration Tests
```bash
cd backend
pytest tests_new/ -v
```

#### Run Accuracy Evaluations (Golden Dataset & E2E)
We have custom evaluation scripts that test the actual LLM accuracy against a Golden Dataset and run simulated multi-turn conversations against the live API.

**1. Run Triage Agent Accuracy Eval**
```bash
cd backend
python evals/run_evals.py
```
*Outputs triage entity extraction and intent accuracy to `evals/eval_results.csv`*

**2. Run Full System E2E Pipeline Eval**
*(Note: Ensure your uvicorn backend is running in another terminal first!)*
```bash
cd backend
python evals/run_system_evals.py
```
*Outputs End-to-End conversation success rates to `evals/e2e_results.csv`. See the full comprehensive report in `evals/evals_accuracy_report.md`.*

#### Run Specific Test Files
```bash
# Test triage agent
pytest tests_new/test_triage.py -v

# Test database agent
pytest tests_new/test_database.py -v

# Test policy agent
pytest tests_new/test_policy.py -v

# Test resolution agent
pytest tests_new/test_resolution.py -v

# Test memory/storage
pytest tests_new/test_memory.py -v

# Test full API pipeline (requires running server)
pytest tests_new/test_api_pipeline.py -v
```

#### Run Tests with Coverage
```bash
pytest tests_new/ --cov=app --cov-report=html
```

View coverage report: `backend/htmlcov/index.html`

#### Test Categories

| Test File | Coverage |
|-----------|----------|
| `test_triage.py` | Order ID extraction, intent classification |
| `test_database.py` | SQL generation, order fetching |
| `test_policy.py` | Refund/return/exchange eligibility |
| `test_resolution.py` | Response generation, label creation |
| `test_memory.py` | State persistence, history management |
| `test_api_pipeline.py` | End-to-end API workflows |

### Frontend Tests

```bash
cd frontend
npm run lint
```

## 📡 API Endpoints

### Main Endpoints

#### POST `/v1/message`
Submit a customer message for processing.

**Request:**
```json
{
  "conversation_id": "uuid-string",
  "message": "I want to return order 11111"
}
```

**Response:**
```json
{
  "conversation_id": "uuid-string",
  "reply": "I can help you with that return...",
  "status": "completed",
  "intent": "return_request",
  "urgency": "medium",
  "order_id": "11111",
  "order_details": {...},
  "agents_called": ["triage", "database", "policy", "resolution"],
  "return_label_url": "http://localhost:8000/labels/11111_return_label.pdf",
  "buttons": ["Confirm Return", "Cancel"]
}
```

#### GET `/v1/policy-docs`
Retrieve all policy documents.

**Response:**
```json
{
  "policies": {
    "refund": {...},
    "return": {...},
    "exchange": {...}
  }
}
```

#### GET `/labels/{filename}`
Retrieve generated return label PDFs.

## 📁 Project Structure

```
Autonomous-Customer-Success-Swarm/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry
│   │   ├── agents/
│   │   │   ├── triage/                # Intent classification
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   ├── database/              # Order data fetching
│   │   │   │   ├── agent.py
│   │   │   │   ├── db_service.py
│   │   │   │   └── tools/
│   │   │   ├── policy/                # Policy verification
│   │   │   │   ├── agent.py
│   │   │   │   └── data/
│   │   │   └── resolution/            # Response generation
│   │   │       ├── agent.py
│   │   │       ├── core/
│   │   │       ├── crm/
│   │   │       └── static/labels/
│   │   ├── api/
│   │   │   ├── message.py             # Message endpoint
│   │   │   ├── policy.py              # Policy endpoint
│   │   │   └── resolution.py          # Resolution endpoint
│   │   ├── orchestrator/
│   │   │   ├── graph.py               # LangGraph workflow
│   │   │   ├── runner.py              # Orchestration logic
│   │   │   ├── state.py               # State management
│   │   │   ├── guard.py               # Safety checks
│   │   │   └── escalation.py          # Escalation rules
│   │   ├── storage/
│   │   │   └── memory.py              # Conversation persistence
│   │   └── utils/
│   │       └── logger.py              # Logging utilities
│   ├── tests_new/
│   │   ├── conftest.py                # Test fixtures
│   │   ├── test_triage.py
│   │   ├── test_database.py
│   │   ├── test_policy.py
│   │   ├── test_resolution.py
│   │   ├── test_memory.py
│   │   └── test_api_pipeline.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Main app component
│   │   ├── main.jsx                   # Entry point
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx         # Chat interface
│   │   │   ├── MessageBubble.jsx      # Message display
│   │   │   ├── ChatInput.jsx          # Input field
│   │   │   ├── Sidebar.jsx            # Navigation
│   │   │   └── GlassUI.jsx            # Glass morphism UI
│   │   ├── api/
│   │   │   └── client.js              # API client
│   │   └── utils/
│   │       └── logger.js              # Frontend logging
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
└── README.md                          # This file
```

## 🔄 Workflow Example

### Example: Processing a Return Request

1. **User Input:**
   ```
   "I want to return order 11111"
   ```

2. **Triage Agent:**
   - Extracts order_id: `11111`
   - Classifies intent: `return_request`
   - Determines urgency: `high`

3. **Database Agent:**
   - Generates SQL: `SELECT * FROM orders WHERE order_id = 11111`
   - Fetches order details
   - Returns: `{product: "Wireless Headphones", status: "Delivered", ...}`

4. **Policy Agent:**
   - Checks return eligibility
   - Verifies delivery date within 45 days
   - Returns: `{eligible: true, reason: "Within return window"}`

5. **Resolution Agent:**
   - Generates return label PDF
   - Creates confirmation buttons
   - Composes response message

6. **Final Response:**
   ```json
   {
     "reply": "I'll help you return your Wireless Headphones. I've generated a prepaid return label...",
     "return_label_url": "http://localhost:8000/labels/11111_return_label.pdf",
     "buttons": ["Confirm Return", "Cancel"]
   }
   ```

## 🐛 Troubleshooting

### Common Issues

#### 1. Ollama Connection Error
```
Error: Could not connect to Ollama
```
**Solution:** Ensure Ollama is running
```bash
ollama serve
```

#### 2. Database Connection Failed
```
Error: could not connect to server: Connection refused
```
**Solution:** 
- Check PostgreSQL is running
- Verify `.env` database credentials
- Ensure database `customer_success` exists

#### 3. Port Already in Use
```
Error: Address already in use (Port 8000)
```
**Solution:** Kill the process or use a different port
```powershell
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
uvicorn app.main:app --port 8001
```

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Ensure you're in the correct directory
```bash
cd backend
# Set PYTHONPATH if needed
$env:PYTHONPATH = "."
```

#### 5. Frontend Connection Refused
```
Error: Network Error - Connection refused
```
**Solution:** 
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`

#### 6. Test Server Not Running
```
pytest test_api_pipeline.py - All tests skipped
```
**Solution:** Start the backend server before running integration tests
```bash
# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
pytest tests_new/test_api_pipeline.py -v
```

## 📝 Development Notes

### Adding New Agents

1. Create agent directory in `backend/app/agents/`
2. Implement agent logic in `agent.py`
3. Add agent to orchestrator graph in `backend/app/orchestrator/graph.py`
4. Create tests in `backend/tests_new/`

### Environment-Specific Configuration

Create separate `.env` files:
- `.env.development`
- `.env.production`
- `.env.test`

### Database Migrations

For schema changes:
```bash
# Using Alembic (if added)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is part of GlideCloud Internship.

## 👥 Team

Developed during GlideCloud Internship Program.

## 📞 Support

For issues and questions:
1. Check this README
2. Review API documentation at `/docs`
3. Check test cases for examples
4. Review logs in terminal output

## 🔗 Useful Links

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Ollama Documentation**: https://ollama.ai/
- **React Documentation**: https://react.dev/
- **Vite Documentation**: https://vitejs.dev/

---

**Last Updated:** February 2026

**Version:** 1.0.0
