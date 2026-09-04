<div align="center">

<br/>

<a href="https://git.io/typing-svg">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=30&pause=1000&color=0B3D66&center=true&vCenter=true&width=520&lines=Vaggio;Collect.+Score.+Follow+up." alt="Typing SVG" />
</a>

<br/>

<p>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white"/>
  <img src="https://img.shields.io/badge/DRF-3.15-A30000?style=flat-square&logo=django&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-19-20232A?style=flat-square&logo=react&logoColor=61DAFB"/>
  <img src="https://img.shields.io/badge/TypeScript-5-007ACC?style=flat-square&logo=typescript&logoColor=white"/>
  <img src="https://img.shields.io/badge/Tailwind-4-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white"/>
</p>

</div>

<br/>

---

## `~/about`

```ts
const vaggio = {
  type:        "Full-Stack Web Application",
  backend:     ["Python 3.13", "Django 5.2", "Django REST Framework", "PostgreSQL", "pytest"],
  frontend:    ["React 19", "TypeScript", "Vite", "Tailwind CSS v4", "TanStack Query", "React Router"],
  features:    ["Job radar", "Profile scoring", "Kanban funnel", "AI cover letters", "Dynamic RBAC", "TOTP 2FA"],
  sources:     "Brazil-first — GitHub Issues · Gupy",
  author:      "Mauro Junior · github.com/mj01px",
} as const;
```

**Vaggio** collects developer jobs from public sources, scores every one of them
against your own profile, and tracks the applications through a funnel. It solves
two concrete problems of a job hunt: **finding the right postings inside the noise**
and **never dropping a follow-up**.

Jobs are ingested from GitHub Issues boards and the public Gupy portal, ranked by a
scoring engine you can tune, and turned into a personal cover letter by Gemini using
a dossier only you write. All served by a Django REST API with session auth,
role-based access control and a second factor.

```
vaggio/
├── backend/     # Django REST API   →  http://localhost:8000
└── frontend/    # React + Vite SPA  →  http://localhost:5173
```

---

## `~/features`

<table>
  <tr>
    <td valign="top" width="50%">
      <b>🎯 Job hunting</b><br/><br/>
      <ul>
        <li>Radar: a triage queue ranked by your profile</li>
        <li>Date range, source and minimum score filters</li>
        <li>Manual entry for what the collectors miss</li>
        <li>Kanban funnel — drag on desktop and on touch</li>
        <li>Overdue follow-ups surfaced on the dashboard</li>
        <li>Closed applications kept for the history</li>
        <li>AI cover letter per job, written from your dossier</li>
      </ul>
    </td>
    <td valign="top" width="50%">
      <b>🛠️ Admins</b><br/><br/>
      <ul>
        <li>Dynamic roles & permissions (RBAC)</li>
        <li>User management, invite only</li>
        <li>Collection history per run</li>
        <li>Job editing straight from the Radar</li>
      </ul>
      <br/>
      <b>🔒 Access & security</b><br/><br/>
      <ul>
        <li>No public sign-up — accounts start from an invite</li>
        <li>Password recovery by e-mail, single-use links</li>
        <li>E-mail change confirmed on the <i>new</i> address</li>
        <li>TOTP second factor with backup codes</li>
        <li>Rate limiting on every public route</li>
      </ul>
    </td>
  </tr>
</table>

---

## `~/getting-started`

### Backend

```bash
cd backend

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/development.txt

copy .env.example .env          # then fill in the values

python manage.py migrate
python manage.py createsuperuser   # the e-mail it asks for is the login
python manage.py runserver 8000    # → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install && npm run dev      # → http://localhost:5173
```

On Windows, `scripts\dev.bat` starts both at once and `scripts\collect.bat` runs a
collection. The database defaults to SQLite with nothing to configure; fill in the
`DB_*` variables to use PostgreSQL instead.

---

## `~/environment`

Create `.env` inside `backend/`:

```env
# Django signing key
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=your_secret_key_here

# Personal GitHub token, public scope is enough
# Without it the API allows 60 requests/hour, with it 5000
GITHUB_TOKEN=your_github_token_here

# Google AI Studio key, used to write the cover letters
# Free tier, no card: https://aistudio.google.com
GEMINI_API_KEY=your_gemini_key_here
```

<details>
<summary><b>Optional overrides</b></summary>
<br/>

```env
# PostgreSQL — fill DB_NAME to use it instead of SQLite
DB_NAME=
DB_USER=postgres
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432

# E-mail. Without EMAIL_HOST Django prints the message to the console, so the
# recovery link shows up in the runserver terminal and development needs no SMTP.
# On Brevo, EMAIL_HOST_USER is NOT the account e-mail: it is the dedicated SMTP
# login, on the same page where the key is generated.
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Vaggio <no-reply@example.dev>

# Base of every link sent by e-mail. This is the FRONTEND address, not the API:
# whoever clicks lands on a screen. In production it MUST be the real domain.
FRONTEND_URL=http://localhost:5173

# Single-use link lifetimes, in hours
PRAZO_LINK_SENHA_HORAS=2
PRAZO_LINK_CONVITE_HORAS=72
PRAZO_LINK_EMAIL_HORAS=2

# Rate limits on the public routes
THROTTLE_LOGIN=10/min
THROTTLE_RECUPERACAO=5/hour
THROTTLE_2FA=10/min

# Collectors
GUPY_API=https://employability-portal.gupy.io/api/v1/jobs
GEMINI_MODEL=gemini-3.7-flash

# CORS (the Vite dev server runs on 5173)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

</details>

---

## `~/commands`

```bash
python manage.py collect              # run every source now
python manage.py collect --dry-run    # show what would be saved, save nothing
python manage.py rescore              # reapply the scoring to what is stored
python manage.py pitch <job_id>       # write a cover letter from the terminal
python manage.py sync_permissoes      # load new permission slugs into the table
```

---

## `~/how-it-works`

<details>
<summary><b>Scoring — what makes a job good for you</b></summary>
<br/>

The whole criterion lives in `apps/jobs/scoring/profile.py`, the only file to edit
to change what counts. Terms are grouped by weight: the stack you want, the domain
where your experience is worth more, the seniority that fits, and penalties for the
ones that do not.

Three rules keep it honest: a hit in the **title counts double**, since that is the
most reliable signal; **one hit per group is enough**, so repetition cannot inflate a
score; and asking for **too many years of experience subtracts**. After editing,
`manage.py rescore` reapplies it to everything already stored.

A profile can also override the terms from the app itself, in `/perfil`, without a
deploy.

</details>

<details>
<summary><b>Collectors — and what the Gupy API really accepts</b></summary>
<br/>

A source receives configuration, goes to the origin and returns `RawJob`. It never
touches the database and never scores: that belongs to the collection service, which
is what keeps each source small and testable without Django.

The Gupy module documents what was **measured**, not assumed:

- `pagination.total` lies when `limit` is high, so the stop condition is the short
  page, never the counter. Trusting it cost 550 jobs on a single term;
- there is no date or sort parameter, so recency is cut on our side;
- spelling variants (`back end`, `back-end`, `backend`) return **zero** new jobs
  over each other;
- broad terms poison the queue. `estagio` alone returns 1.760 postings, ~80% of them
  outside tech, and the score does not protect you: seniority terms are worth points,
  so an unrelated internship lands *above* a real developer job;
- prefix matching is a trap. `programacao` also matches "**Programa** de Estágio".

A page that fails is retried before giving up, and a search that never answers is
recorded on the run, so a collection that lost jobs to an outage does not pass for a
quiet day.

</details>

<details>
<summary><b>Access — roles, invites and the second factor</b></summary>
<br/>

Permissions live in a table instead of the code, so granting or revoking access is
data, not a deploy. A **Cargo** groups permissions and a profile points at one. No
role is seeded with everything: total access comes from `is_superuser`, which skips
the check entirely.

Recovery, invitation and e-mail change are one machine: a single-use token sent by
e-mail that authorizes exactly one action. For anything touching the password it is
Django's `PasswordResetTokenGenerator`, whose token hashes the user's current state,
so saving the new password invalidates the link by itself.

Two decisions worth keeping: **the admin never knows anyone's password**, since an
invited account is created with `set_unusable_password()`; and the **e-mail change
link goes to the new address**, because that is the only way to prove it exists and
belongs to the person before it becomes their credential.

The second factor is TOTP, with eight backup codes generated at activation and
stored hashed. Preparing does not enable anything, so whoever opens the screen and
gives up halfway is not locked out.

</details>

<details>
<summary><b>API</b></summary>
<br/>

Everything under `/api/v1/`. Every failure answers in the same envelope
`{ error: { code, message, details } }`.

| Route | What it does |
|---|---|
| `GET /jobs/` | The triage queue. `?queue=`, `?q=`, `?source=`, `?min_score=`, `?published_after=` |
| `POST /jobs/` · `PATCH /jobs/{id}/` | Manual entry, and correcting what the collector got wrong |
| `POST /jobs/{id}/discard/` · `/restore/` | Triage |
| `GET/POST /jobs/{id}/pitch/` | Cover letters already written, and writing one more |
| `GET /applications/board/` | The whole board: columns, overdue and counters |
| `GET /applications/closed/` | Rejected and withdrawn together |
| `POST /collections/run/` | Run a collection now |
| `GET/POST/DELETE /sessao/` | Who is logged in, enter, leave |
| `POST /sessao/codigo/` | Second step of the login, with 2FA on |
| `GET/PATCH /perfil/` | Dossier, scoring terms and preferences |
| `POST /perfil/senha/` · `/email/` · `/2fa/` | Password, e-mail and second factor |
| `POST /senha/esqueci/` · `/redefinir/` | Password recovery. **Public** |
| `POST /email/confirmar/` | Applies the e-mail change. **Public** |
| `GET/POST /usuarios/` · `/cargos/` | Users and roles |

Apart from `/health/`, the only routes answering without a session are the public
ones above, and every one of them starts from a link sent by e-mail.

</details>

---

## `~/tests`

```bash
cd backend && pytest              # 237 tests
cd frontend && npx tsc -b && npx eslint src/ && npm run build
```

The suite covers the API, the scoring engine, the collectors and the security flows,
including what must **not** work: a recovery link used twice, a token aimed at
another account, the same backup code entering twice, and the rate limit answering
429.

---

## `~/stack`

<div align="center">

| Layer | Technologies |
|-------|-------------|
| **Backend** | ![Python](https://img.shields.io/badge/Python_3.13-3776AB?style=flat-square&logo=python&logoColor=white) ![Django](https://img.shields.io/badge/Django_5.2-092E20?style=flat-square&logo=django&logoColor=white) ![DRF](https://img.shields.io/badge/DRF-A30000?style=flat-square&logo=django&logoColor=white) ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) |
| **Frontend** | ![React](https://img.shields.io/badge/React_19-20232A?style=flat-square&logo=react&logoColor=61DAFB) ![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat-square&logo=typescript&logoColor=white) ![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind_v4-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white) ![React Query](https://img.shields.io/badge/TanStack_Query-FF4154?style=flat-square&logo=reactquery&logoColor=white) |
| **Database** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white) |
| **AI** | ![Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white) |
| **Sources** | ![GitHub](https://img.shields.io/badge/GitHub_Issues-181717?style=flat-square&logo=github&logoColor=white) ![Gupy](https://img.shields.io/badge/Gupy-00B37E?style=flat-square&logoColor=white) |

</div>

---

<div align="center">
  <br/>
  <sub>
    Built by <a href="https://github.com/mj01px"><strong>Mauro Junior</strong></a>
    &nbsp;·&nbsp;
    <a href="https://www.linkedin.com/in/mauroapjunior/">LinkedIn</a>
  </sub>
  <br/><br/>
</div>
