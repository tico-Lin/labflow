# LabFlow Architecture

This document outlines the technical architecture, design principles, and implementation details for LabFlow.

## 1. Guiding Principles

- **Modularity**: Each core function (file management, reasoning engine, etc.) is designed as a separate module with clean interfaces. This allows for independent development, testing, and replacement.
- **Scalability**: The system is designed to evolve from a single-user local application to a multi-user, cloud-native platform. This is achieved through a flexible architecture that supports different database and storage backends.
- **Configuration over Code**: Features and parameters are driven by configuration files where possible, allowing for easier adaptation to different environments without code changes.
- **Security First**: Data security is paramount, with considerations for access control, data encryption (in transit and at rest), and audit logging.

## 2. System Architecture

The system follows a classic multi-tier architecture, with clear separation between the presentation, application, and data layers.

```
┌─────────────────────────────────────────────┐
│            Frontend Layer (Replaceable)       │
│  ┌─────────────┐      ┌─────────────┐      │
│  │ Web UI      │      │ Desktop App │      │
│  │ (React)     │      │ (Electron)  │      │
│  └─────────────┘      └─────────────┘      │
└──────────────┬──────────────────────────────┘
               │ REST API / WebSocket
┌──────────────▼──────────────────────────────┐
│            Backend Layer (Business Logic)     │
│  ┌──────────────────────────────────────┐  │
│  │ FastAPI (Python)                     │  │
│  │ ├── Routing: Files/Tags/Conclusions   │  │
│  │ ├── Services: ReasoningEngine/Scripts │  │
│  │ └── Middleware: Auth/Logging/Errors   │  │
│  └──────────────────────────────────────┘  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│          Data Layer (Switchable)            │
│  ┌─────────────┐      ┌─────────────┐      │
│  │ SQLAlchemy  │      │ FileStorage │      │
│  │ ORM         │      │ (Abstracted)│      │
│  └──────┬──────┘      └──────┬──────┘      │
│         │                    │              │
│  ┌──────▼──────┐      ┌──────▼──────┐      │
│  │ SQLite /    │      │ Local /     │      │
│  │ PostgreSQL  │      │ S3 / MinIO  │      │
│  └─────────────┘      └─────────────┘      │
└─────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│        Task Queue Layer (Optional)          │
│  ┌──────────────────────────────────────┐  │
│  │ Celery + Redis                       │  │
│  │ - Long-running calculations           │  │
│  │ - Batch processing                    │  │
│  │ - Scheduled synchronization         │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 2.1. Technology Stack

- **Backend**: **FastAPI** on Python 3.9+. It provides automatic documentation, data validation with Pydantic, and native asynchronous support, which is ideal for I/O-bound operations like file handling and long-running analysis tasks.
- **Database**: **SQLAlchemy (ORM)** provides an abstraction layer that allows seamless switching between **SQLite** (for simple, local-first deployment) and **PostgreSQL** (for robust, multi-user production environments).
- **Frontend**: **React** with a component library like **Ant Design**. This combination offers a rich set of pre-built components for building enterprise-grade interfaces, including tables, forms, and graphs. It can also be packaged into a desktop application using **Electron**.
- **Task Queue**: **Celery** with a **Redis** broker is used for handling long-running, asynchronous tasks such as batch processing, complex calculations, and scheduled jobs. This prevents blocking the main API and improves responsiveness.
- **File Storage**: A custom **Storage Abstraction Layer** allows the application to use different storage backends interchangeably. Implementations for **local filesystem** and cloud-based object storage (like **Amazon S3** or a self-hosted **MinIO**) are planned.

## 3. Deployment Strategy & Scalability Path

The architecture is designed to support three deployment models, allowing the project to scale from a local tool to a full-fledged cloud service.

- **Phase 1: Local-First (Current)**
  - **Setup**: FastAPI backend, SQLite database, and local file storage, all running on a single machine.
  - **Use Case**: Perfect for individual researchers. Zero-cost, full data privacy, and no internet dependency.

- **Phase 2: Hybrid Mode**
  - **Setup**: The local application remains the primary interface, but it gains the ability to sync metadata (and optionally files) to a central cloud backend (PostgreSQL DB, S3/MinIO storage).
  - **Use Case**: Small teams or labs that need to share data and results while still retaining the performance and offline capabilities of a local application.

- **Phase 3: Full Cloud**
  - **Setup**: The entire application is hosted in the cloud. The backend runs on scalable infrastructure (e.g., AWS Lambda, Google Cloud Run), the database is a managed service (e.g., RDS), and all files reside in object storage. Users access the system via a web browser or a lightweight desktop client.
  - **Use Case**: Large organizations or cross-institutional collaborations requiring centralized data management, real-time collaboration, and access from anywhere.

## 4. v0.3 Feature: The Reasoning Engine

The core feature of v0.3 is the **Reasoning Engine**, a system for creating, executing, and managing automated analysis workflows.

### 4.1. Concept

A "Reasoning Chain" is a Directed Acyclic Graph (DAG) where each node represents a specific operation (e.g., loading data, performing a calculation, applying a condition). Users can visually construct these chains to automate complex, multi-step analysis tasks that are common in scientific research.

### 4.2. Node Types

The engine supports several types of nodes:
- **`DATA_INPUT`**: Selects a file or dataset to be processed.
- **`TRANSFORM`**: Performs data manipulation, like unit conversion or smoothing.
- **`CALCULATE`**: Executes a Python script to perform a specific analysis (e.g., peak fitting, impedance modeling).
- **`CONDITION`**: Creates branches in the workflow based on the output of a previous node (e.g., `if R_ct > 100`).
- **`OUTPUT`**: Saves the results, generates a plot, or writes a conclusion to the database.

### 4.3. Execution

The `ReasoningEngine` service executes a chain by performing a topological sort of the nodes and running them in order of dependency. Results from parent nodes are passed as inputs to their children. The engine is designed to be fault-tolerant, with error handling and result caching to prevent re-computation of unchanged steps.
