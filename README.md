# RETROIQ — Edge-AI Smart Retail Intelligence Platform

> **Smarter checkout. Safer carts. Better store operations.**

RETROIQ is a smart-retail prototype that connects a customer-facing trolley experience with store operations, inventory data, and an edge backend. The goal is to reduce checkout friction, improve visibility into cart activity, and give store teams useful operational signals without making the trolley depend on a camera.

**Project status:** Active prototype / development. Validate payment, inventory, MQTT security, and recovery behaviour in a controlled test environment before using real payments or a live store.

---

## Contents

- [What RETROIQ does](#what-retroiq-does)
- [Key modules](#key-modules)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Run locally](#run-locally)
- [Environment configuration](#environment-configuration)
- [MQTT message topics](#mqtt-message-topics)
- [API health checks](#api-health-checks)
- [Deployment notes](#deployment-notes)
- [Security checklist](#security-checklist)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

## What RETROIQ does

RETROIQ is designed around a **retrofit-first smart retail system**: the concept is to upgrade existing carts rather than manufacture a completely new smart trolley for every store.

The platform brings together:

- **Customer Trolley:** product selection, cart totals, and checkout flow.
- **Product & Inventory Management:** product records, stock visibility, and inventory operations.
- **Live Store:** operational visibility for store staff.
- **Retail Guardian:** item-verification and cart-integrity signals. Alerts should be neutral and evidence-based, such as *Verification required* or *Unexpected weight change*.
- **Transactions:** records of completed checkout activity.
- **AI Insights & Shopper Analytics:** analytical modules for store operations and shopper/queue intelligence.
- **Edge Connectivity:** MQTT messages for trolley scans, weight readings, and status updates.
- **QR Payment Flow:** Razorpay dynamic UPI QR creation, payment-status handling, and webhook integration in the backend.

> The availability and maturity of an individual module depend on the current branch, hardware, environment variables, and backend configuration. This repository is an evolving prototype, not a claim of production certification.

## Key modules

### 1. Customer trolley and checkout

The frontend provides a trolley-oriented shopping flow where products can be added to a cart and the total can be calculated before payment. The backend owns the persistent cart and transaction operations.

### 2. Edge event processing

The FastAPI backend subscribes to MQTT topics for trolley scans, weight events, and trolley status. The current backend configuration expects a Mosquitto broker on `localhost:1883` on the same host as the API.

### 3. Store and inventory operations

The dashboard provides views for products, inventory, stock orders, transactions, notifications, and store intelligence. SQLite is used by the backend through the project database module.

### 4. Razorpay integration

The backend contains endpoints for creating a dynamic single-use UPI QR and for receiving Razorpay webhook events. A successful payment must be validated on the server; a QR being displayed or a client-side message is not proof of payment.

**Before real-money use:** verify the complete captured-payment → checkout → transaction → inventory decrement → cart clear sequence in Razorpay Test Mode, and confirm webhook configuration and idempotency. Do not treat this README as a payment certification.

## Architecture

```text
Customer / Store Staff
          |
          v
React + Vite frontend (hosted separately, e.g. Vercel)
          |
          | HTTPS / REST API
          v
FastAPI backend (dedicated application service on VPS)
     |            |                |
     v            v                v
 SQLite DB     Mosquitto MQTT   Razorpay API/Webhook
                    ^
                    |
            ESP32 / trolley devices
            (secure broker access required)
```

The frontend, API, database, and message broker are separate responsibilities. A public frontend must call the **public HTTPS API hostname**; it must not point to `localhost` or `127.0.0.1`, because those addresses refer to the device running the browser.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, JavaScript, CSS, Lucide icons |
| Backend API | Python, FastAPI, Uvicorn, Pydantic |
| Data | SQLite via the backend database module |
| Device messaging | MQTT / Paho MQTT, with Mosquitto as broker |
| Payments | Razorpay dynamic UPI QR and webhook integration |
| Intelligence modules | Project-local `ai_engine` module |
| Hosting target | Vercel frontend + isolated Hostinger KVM VPS API deployment |

## Repository layout

The exact files may vary by branch, but the application is organised around these areas:

```text
.
├── src/                    # React frontend and styles
├── backend/
│   ├── main.py             # FastAPI routes, MQTT handling, payment flow
│   ├── database.py         # Database connection and persistence helpers
│   ├── ai_engine.py        # Store/AI intelligence functions
│   ├── .env                # Local secrets only; do not commit
│   └── ...                 # Other backend modules and data files
├── public/                 # Static frontend assets (if present)
├── package.json            # Frontend scripts and dependencies
└── README.md
```

Keep all Python modules imported by `backend/main.py` (including `database.py` and `ai_engine.py`) alongside the deployment. Do not deploy only `main.py`.

## Run locally

### Prerequisites

- Git
- Node.js and npm
- Python 3.10+ (use the Python version supported by the project's dependencies)
- Mosquitto MQTT broker for trolley-event testing
- Razorpay credentials only if testing the payment integration

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <REPOSITORY_FOLDER>
```

Replace the placeholders with your actual Git repository URL and folder name.

### 2. Start the backend

Open a terminal in the repository root, then:

**Windows PowerShell**

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If `backend/requirements.txt` exists, install the pinned project dependencies:

```powershell
python -m pip install -r requirements.txt
```

If that file is not present yet, install the dependencies listed by the backend project and create a maintained `requirements.txt` before deploying. The backend imports project-local modules such as `database` and `ai_engine`, so keep those files in place.

Create `backend/.env` for local-only credentials (see [Environment configuration](#environment-configuration)), ensure Mosquitto is running on the configured local broker, then start FastAPI from inside `backend/`:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open a second terminal for other commands. Do not start multiple Uvicorn instances on the same port; `WinError 10048` means the port is already in use.

### 3. Start the frontend

In a separate terminal from the repository root:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

**API base URL note:** the current frontend source has an API base URL defined in `src/main.jsx`. Before running or building the frontend for another environment, verify that this value points to the correct backend. For local development it should point to the local API; for a public deployment it must point to the API's public HTTPS hostname. Never expose a Razorpay secret in frontend code.

## Environment configuration

Create `backend/.env` locally and on the server with the credentials required by the backend. A typical Razorpay setup uses:

```dotenv
RAZORPAY_KEY_ID=replace_with_key_id
RAZORPAY_KEY_SECRET=replace_with_secret
RAZORPAY_WEBHOOK_SECRET=replace_with_webhook_secret
```

- Use Razorpay **Test Mode** credentials for development and end-to-end testing.
- Configure the webhook URL in Razorpay to the public HTTPS endpoint, for example `https://<API_HOST>/webhook/razorpay`.
- Keep `.env` out of Git. Never paste secrets into README files, source code, screenshots, issues, or chat messages.
- Confirm the deployed service loads the `.env` file from the intended backend directory. The app must be restarted after changing server-side environment variables.

## MQTT message topics

The backend subscribes to these topic patterns:

| Topic | Intended event |
|---|---|
| `cart/+/scan` | Item/RFID scan event for a trolley |
| `cart/+/weight` | Trolley weight measurement/update |
| `cart/+/status` | Trolley status event |

MQTT payloads should be valid JSON. Example scan payload shape:

```json
{"rfid":"RFID-MILK-001"}
```

The exact fields accepted by each topic are defined by the backend handlers. Do not expose an unauthenticated MQTT broker to the public internet. Configure authentication, network restrictions, and TLS as appropriate for the deployment.

## API health checks

When the backend is running, use these endpoints to confirm basic availability:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Basic API health response |
| `GET /system-status` | FastAPI, MQTT, and database component status |
| `GET /docs` | Interactive FastAPI API documentation |
| `POST /payment/create-qr` | Creates a dynamic payment QR for an eligible trolley cart |
| `POST /webhook/razorpay` | Receives and verifies Razorpay webhook notifications |

The exact route list is defined by the deployed version of `backend/main.py`. Use `/docs` on the deployed API to inspect that version. Do not rely on the presence of an endpoint in README text if it is absent from the running build.

## Deployment notes

The target architecture is a public frontend backed by a continuously running API on a VPS. The laptop should not be required for the deployed system to remain online.

### Deploy safely on a shared/senior-owned Hostinger VPS

**Use an isolated application deployment. Do not overwrite, restart, or reconfigure another project.** Before deploying:

1. Confirm explicit permission to use the VPS for this application and identify an unused subdomain/hostname.
2. Use a dedicated directory such as `/opt/retroiq` and a dedicated Linux service such as `retroiq-backend.service`.
3. Use a dedicated Nginx site file and hostname for RETROIQ. Do not overwrite the default site or another project's configuration.
4. Keep RETROIQ's logs, environment file, database, and backups in its own application paths with restricted permissions.
5. Keep Mosquitto configuration changes separate and review existing listeners/users before changing broker or firewall settings.
6. Do not reboot the VPS, run broad process-kill commands, stop unrelated Docker containers, or edit global firewall rules as part of this app deployment.
7. Test the API health endpoints and a payment in Razorpay Test Mode before switching the frontend to the VPS API.

For a reliable deployment, run FastAPI as a managed service (for example, systemd or a dedicated Docker Compose project), place Nginx in front of it, enable HTTPS for the API hostname, and configure restarts and logs. Keep the SQLite database on persistent storage and take backups before any schema or deployment change.

### Production connectivity checklist

- Frontend API base points to the new public HTTPS API hostname.
- CORS allows the exact deployed frontend origin.
- FastAPI runs continuously under a dedicated service/container.
- Mosquitto runs on the same VPS if the backend retains `localhost:1883` configuration.
- Any trolley devices connect to the correct broker hostname with authentication; `localhost` on a device means the device itself, not the VPS.
- SQLite database path is persistent and writable by the dedicated app user.
- Razorpay webhook secret is configured and signatures are verified.
- HTTPS certificate is active and renewals are managed.
- Logs, backups, health checks, and rollback steps are documented.

## Security checklist

- [ ] No `.env`, API secrets, passwords, private keys, or production database are committed.
- [ ] Razorpay Test Mode is used during development.
- [ ] Payment is confirmed server-side; UI state alone never marks an order as paid.
- [ ] Webhook signatures are verified and repeated events cannot create duplicate checkouts.
- [ ] MQTT access is authenticated and restricted to trusted devices/network paths.
- [ ] Production API is served over HTTPS.
- [ ] CORS contains only the required frontend origins.
- [ ] The database is backed up before deployment or schema changes.
- [ ] RETROIQ service/configuration is isolated from other VPS applications.
- [ ] Credentials shown in screenshots or messages are rotated immediately.

## Troubleshooting

| Symptom | First check |
|---|---|
| `WinError 10048` when starting Uvicorn | Port 8000 is already occupied. Check the listener and reuse the healthy process or stop only the verified RETROIQ process. |
| `/system-status` shows MQTT disconnected | Confirm Mosquitto is running on the backend host and listening on the configured port. |
| MQTT logs show invalid JSON | Publish valid JSON; use double quotes around JSON property names and string values. |
| Frontend loads but API calls fail | Confirm `API_BASE`, backend uptime, HTTPS certificate, and CORS origin. |
| QR appears but checkout does not finish | Check server logs, Razorpay payment status/webhook delivery, and transaction/inventory/cart state before retrying payment. |
| Laptop-offline requirement is not met | Check that the API, MQTT broker, database, and any required background processes are running on the VPS—not on the laptop. |

## Roadmap

- Complete and verify QR payment → captured status → idempotent checkout → transaction → inventory update → cart reset.
- Move frontend API configuration to an environment-specific build setting rather than manually editing source between environments.
- Establish secure MQTT authentication/TLS for trolley devices.
- Add repeatable deployment, backup, and rollback procedures for the dedicated VPS service.
- Validate the retrofit hardware workflow with real RFID and weight sensor events.
- Document test coverage and measured operational results as they become available.

## Contributing

1. Create a feature branch.
2. Make a focused change and test it locally.
3. Check backend syntax and frontend build/lint scripts before opening a pull request.
4. Never include secrets, real payment data, or production database files in commits.
5. Describe changes, tests performed, and any known limitations.

## License

No license has been specified in this repository yet. Until a license is added, reuse and redistribution permissions should not be assumed.
