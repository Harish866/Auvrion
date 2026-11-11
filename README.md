# AUVRION
### Where AI Agents Collaborate, Execute, and Deliver.

AUVRION is an AI-powered multi-agent platform that transforms complex user requests into coordinated workflows. Instead of relying on a single AI assistant, AUVRION uses an intelligent planner to divide tasks and delegate them to specialized AI agents.

The platform brings together AI task planning, specialized agent execution, data processing, visualization, report generation, and integrated PayPal Sandbox payments.

---

## 🚀 Overview

AUVRION introduces an AI Agent Economy where specialized agents can perform different tasks as part of a coordinated workflow.

A user submits a task, the AI planner analyses the request, determines the required operations, and coordinates the appropriate agents.

Each agent has a specific responsibility and an associated service cost. The platform calculates the total task cost and integrates PayPal Sandbox to demonstrate payment for agent-based services.

## ⚙️ How AUVRION Works

The platform follows a multi-agent orchestration workflow.

### 1. User Request
The user submits a task through the AUVRION web interface.

### 2. AI Planning
The Groq-powered AI planner analyses the request and determines the steps required to complete it.

### 3. Agent Selection
The planner identifies suitable specialized agents and assigns responsibilities based on the task.

### 4. Task Execution
The selected agents perform their assigned operations and return their results to the orchestration system.

### 5. Result Processing
The system collects the outputs and prepares the results for presentation.

### 6. Visualization and Reporting
The generated results can be presented through structured data views, visualizations, and reports.

### 7. Payment Integration
AUVRION integrates PayPal Sandbox to demonstrate payment processing for agent-based services.

---

## 🧠 Specialized AI Agents

AUVRION uses specialized agents with different responsibilities.

| Agent | Responsibility | Service Cost |
|---|---|---:|
| Data Analyst | Analyses and processes data | $5 |
| Visualization Specialist | Creates data visualizations | $3 |
| Report Writer | Generates structured reports | $4 |

The AI planner coordinates these agents according to the requirements of the submitted task.

---

## 🏗️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Django | Backend web framework |
| Groq API | AI-powered task planning |
| AG Grid | Structured data presentation |
| HTML, CSS, JavaScript | Frontend development |
| SQLite | Database |
| PayPal Sandbox | Payment integration |
| Pandas | Data processing |

---

## 📂 Project Structure

```text
Auvrion/
│
├── auvrion/              # Main Django application
│
├── operations/           # Agent operations and execution logic
│
├── static/               # CSS, JavaScript and static assets
│
├── templates/            # HTML templates
│
├── media/                # Uploaded media files
│
├── manage.py             # Django management entry point
│
├── requirements.txt      # Python dependencies
│
├── env.example           # Example environment configuration
│
├── .gitignore            # Git ignored files
│
├── LICENSE               # MIT License
│
└── README.md             # Project documentation
```

---

# 💻 Installation and Setup

Follow these instructions to run AUVRION locally on Windows.

### Prerequisites

Install the following:

- Python 3.13 or compatible version
- Git
- Visual Studio Code (recommended)
- Groq API key
- PayPal Sandbox credentials (for payment testing)

### Step 1: Clone the Repository

Open Command Prompt or the VS Code terminal.

```bash
git clone https://github.com/Harish866/Auvrion.git
```

Navigate into the project directory:

```bash
cd Auvrion
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
```

Install the required packages:

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a copy of `env.example` and name it `.env`.

On Windows Command Prompt:

```cmd
copy env.example .env
```

Open `.env` and enter your credentials:

```env
DJANGO_SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

GROQ_API_KEY=your-groq-api-key

PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your-paypal-sandbox-client-id
PAYPAL_CLIENT_SECRET=your-paypal-sandbox-client-secret
```

**Important:**

- Obtain your Groq API key from https://console.groq.com/
- Obtain PayPal Sandbox API credentials from https://developer.paypal.com/
- Never upload your actual `.env` file or API credentials to GitHub.
- Use Sandbox credentials for testing.

### Step 5: Apply Database Migrations

```bash
python manage.py migrate
```

### Step 6: Create an Administrator Account (Optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to create your account.

### Step 7: Start the Development Server

```bash
python manage.py runserver
```

Open your browser:

http://127.0.0.1:8000/

AUVRION should now be running locally.

---

## 💳 PayPal Sandbox Testing

AUVRION integrates PayPal Sandbox to demonstrate payment processing for AI agent services.

To test the payment workflow:

1. Configure your PayPal Sandbox Client ID and Secret in `.env`.
2. Use the PayPal Sandbox environment.
3. Create or use a Sandbox buyer account through the PayPal Developer Dashboard.
4. Test the payment process using the Sandbox buyer account.

**Note:** Sandbox transactions are simulated and do not involve real money.

---

## 🔐 Security

- API credentials are stored in environment variables.
- The actual `.env` file is excluded from version control.
- PayPal Sandbox is used for payment testing.
- Database files and local development artifacts should not be committed.

---

## 🎯 Project Goals

AUVRION explores how multiple specialized AI agents can work together as an intelligent service ecosystem.

Its primary goals are:

- Simplify complex tasks through AI-powered planning.
- Enable collaboration between specialized AI agents.
- Automate task delegation and execution.
- Present results in structured and understandable formats.
- Demonstrate an AI Agent Economy with service-based pricing.
- Integrate payment infrastructure for agent services.

---

## 🔮 Future Scope

Potential improvements include:

- Dynamic agent discovery and registration.
- More specialized agents.
- Improved multi-agent communication.
- Advanced workflow monitoring.
- Expanded analytics and visualization.
- Production-ready payment integration.
- Scalable agent orchestration.

---

## 👨‍💻 Developer

**Harish J**

GitHub: https://github.com/Harish866

Project: AUVRION

---

## 📜 License

This project is licensed under the MIT License.

---

* AUVRION — Turning complex tasks into coordinated intelligence. *
