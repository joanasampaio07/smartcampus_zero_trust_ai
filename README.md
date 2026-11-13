# SmartCampus Zero Trust AI — v2.0

Plataforma demonstrativa de gestão acadêmica, matrículas e atendimento inteligente.

## Stack
React + TypeScript + Vite | Python + FastAPI | SQLAlchemy | PostgreSQL | Redis (infra preparada) | Google Gemini | Docker Compose | Pytest.

## Executar
1. Copie `.env.example` para `.env` e altere `SECRET_KEY`, `ADMIN_EMAIL` e `ADMIN_PASSWORD`.
2. Execute `docker compose up --build`.
3. Frontend: http://localhost:5173
4. API: http://localhost:8000
5. Swagger: http://localhost:8000/docs

O administrador inicial é criado apenas se as variáveis ADMIN_EMAIL e ADMIN_PASSWORD estiverem configuradas.

## Sem Docker
Backend:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./smartcampus.db"
uvicorn app.main:app --reload
```
Frontend, em outro terminal:
```powershell
cd frontend
npm install
npm run dev
```
Crie `frontend/.env.local` com `VITE_API_URL=http://localhost:8000/api/v1`.

## Funcionalidades MVP
- Cadastro de aluno, login JWT e consulta do perfil.
- Perfis ADMIN, SUPPORT e STUDENT.
- Cadastro/listagem de cursos.
- Solicitação e acompanhamento de matrículas.
- Atualização administrativa de status e auditoria básica.
- Assistente Gemini opcional (GEMINI_API_KEY configurada somente no backend).
- Documentação OpenAPI e testes iniciais.

## Endpoints
- POST `/api/v1/auth/register`
- POST `/api/v1/auth/login` (form OAuth2: username=email, password)
- GET `/api/v1/auth/me`
- GET/POST `/api/v1/courses`
- POST/GET `/api/v1/enrollments`
- PATCH `/api/v1/enrollments/{id}/status`
- POST `/api/v1/ai/chat`
- GET `/health`

## Segurança e limites
Este é um MVP de portfólio, não uma implantação pronta para dados reais. Implementa hash Argon2, JWT com expiração, RBAC no servidor, verificação de propriedade das matrículas, ORM/validação, CORS por allowlist e auditoria de mudança de status. O limitador incluso é em memória e serve apenas para desenvolvimento.

Antes de produção: refresh tokens rotativos/revogáveis, recuperação de senha com token de uso único e e-mail, rate limiting distribuído Redis, Alembic, cookies HttpOnly/Secure/SameSite ou estratégia de token revisada, CSRF conforme autenticação, TLS, backups, gestão de segredos, logs/alertas, storage privado, validação de arquivos, controles LGPD e revisão de segurança. O RAG ainda não está conectado; a IA informa que não há base institucional configurada e não deve ser tratada como fonte oficial.

Zero Trust é uma estratégia de verificação contínua e menor privilégio, não apenas login. Não há garantia de ausência de vulnerabilidades.

## Testes
```bash
cd backend
pytest -q
```

## Deploy
Vercel: root `frontend`, build `npm run build`, output `dist`, variável `VITE_API_URL`.
Render: root `backend`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
Configure banco PostgreSQL gerenciado e variáveis secretas no painel do Render. Nunca envie `.env` ou chaves ao Git.
