# BRUNCLIENTPortal

Minimal Node.js-based skeleton for a multilingual client portal.

## Features
- Three languages: Estonian, Finnish and English.
- In-memory users with roles: admin, worker, client.
- Simple login and dashboard demonstrating role-based access.

## Usage
```bash
npm start
```
Visit <http://localhost:3000/?lang=en> (or `lang=et`, `lang=fi`).

Sample credentials:
- admin / admin123
- worker / worker123
- client / client123

`npm test` simply starts the server for quick verification.
