# 🏗️ Crowdfunding Platform

Plateforme de crowdfunding professionnelle construite avec **Django**, **Django REST Framework**, **PostgreSQL**, **JWT**, **Celery** et **Redis**.

Ce document permet de configurer l'environnement de développement **de zéro** sur une nouvelle machine (Windows) et de retrouver exactement l'état actuel du projet.

---

## 📋 Sommaire

1. [Prérequis](#1-prérequis)
2. [Cloner le projet](#2-cloner-le-projet)
3. [Environnement virtuel Python](#3-environnement-virtuel-python)
4. [Installation des dépendances](#4-installation-des-dépendances)
5. [Base de données PostgreSQL](#5-base-de-données-postgresql)
6. [Fichier `.env`](#6-fichier-env)
7. [Redis via Docker](#7-redis-via-docker)
8. [Migrations](#8-migrations)
9. [Créer le superutilisateur](#9-créer-le-superutilisateur)
10. [Créer le compte plateforme](#10-créer-le-compte-plateforme)
11. [Lancer le serveur Django](#11-lancer-le-serveur-django)
12. [Lancer le worker Celery](#12-lancer-le-worker-celery)
13. [Documentation API](#13-documentation-api)
14. [Lancer les tests](#14-lancer-les-tests)
15. [Structure du projet](#15-structure-du-projet)
16. [Dépannage (erreurs fréquentes)](#16-dépannage-erreurs-fréquentes)

---

## 1. Prérequis

Installer sur la machine, dans cet ordre :

| Outil | Version recommandée | Lien |
|---|---|---|
| **Python** | 3.11+ | https://www.python.org/downloads/ (cocher "Add Python to PATH") |
| **Git** | dernière version | https://git-scm.com/download/win |
| **PostgreSQL** | 16 ou 17 | https://www.postgresql.org/download/windows/ |
| **Docker Desktop** | dernière version | https://www.docker.com/products/docker-desktop/ |
| **VS Code** (recommandé) | dernière version | https://code.visualstudio.com/ |

> 💡 Toutes les commandes ci-dessous sont écrites pour **PowerShell** (Windows).

---

## 2. Cloner le projet

```powershell
cd C:\Users\<votre_nom>\Documents
git clone <URL_DU_DEPOT> crowdfunding_platform
cd crowdfunding_platform
```

---

## 3. Environnement virtuel Python

```powershell
python -m venv venv
```

Activer le venv (à faire à **chaque nouvelle session** de terminal) :

```powershell
venv\Scripts\Activate.ps1
```

> ⚠️ Si PowerShell bloque l'exécution du script, lancez une fois (en administrateur) :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Vous devez voir `(venv)` apparaître devant votre invite de commande.

---

## 4. Installation des dépendances

```powershell
pip install -r requirements\base.txt
```

Si le fichier n'existe pas encore ou est incomplet, installez manuellement l'ensemble des paquets utilisés par le projet :

```powershell
pip install django djangorestframework psycopg2-binary python-decouple ^
    djangorestframework-simplejwt Pillow celery redis django-celery-results ^
    drf-spectacular

pip freeze > requirements\base.txt
```

---

## 5. Base de données PostgreSQL

### 5.1 Vérifier l'installation

```powershell
psql --version
```

Si la commande n'est pas reconnue, ajoutez le dossier `bin` de PostgreSQL au PATH système (ex: `C:\Program Files\PostgreSQL\17\bin`), puis rouvrez le terminal.

### 5.2 Se connecter et créer la base + l'utilisateur

```powershell
psql -U postgres
```

Dans le prompt `postgres=#` :

```sql
CREATE DATABASE crowdfunding_db;
CREATE USER crowdfunding_user WITH PASSWORD 'crowdfunding_pass';
ALTER ROLE crowdfunding_user SET client_encoding TO 'utf8';
ALTER USER crowdfunding_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE crowdfunding_db TO crowdfunding_user;
\q
```

### 5.3 Accorder les droits sur le schéma public (obligatoire depuis PostgreSQL 15+)

```powershell
psql -U postgres -d crowdfunding_db
```

```sql
GRANT ALL ON SCHEMA public TO crowdfunding_user;
ALTER SCHEMA public OWNER TO crowdfunding_user;
\q
```

> ⚠️ **Conflit de port possible** : si vous avez plusieurs versions de PostgreSQL installées, vérifiez le port réel du service actif :
> ```powershell
> Get-Content "C:\Program Files\PostgreSQL\<version>\data\postgresql.conf" | Select-String "^port"
> ```
> Adaptez `DB_PORT` dans le fichier `.env` (étape suivante) en conséquence. Le port standard est `5432`.

---

## 6. Fichier `.env`

Créez le fichier `.env` à la racine du projet :

```powershell
New-Item .env -ItemType File
```

### 6.1 Générer des clés secrètes robustes

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Exécutez la deuxième commande **deux fois** (une clé pour `SECRET_KEY`, une autre différente pour `JWT_SECRET_KEY`).

### 6.2 Contenu complet du `.env`

```env
# Django
SECRET_KEY=<coller la clé générée avec get_random_secret_key>
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# CORS (frontend futur)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000

# JWT
JWT_ACCESS_MINUTES=10
JWT_REFRESH_DAYS=5
JWT_SECRET_KEY=<coller une clé différente générée avec secrets.token_urlsafe>

# Base de données PostgreSQL
DB_NAME=crowdfunding_db
DB_USER=crowdfunding_user
DB_PASSWORD=crowdfunding_pass
DB_HOST=localhost
DB_PORT=5432

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# Commission plateforme (% prélevé sur les intérêts versés aux investisseurs)
PLATFORM_COMMISSION_RATE=10.00
```

> 🔐 **Ce fichier ne doit JAMAIS être commité sur Git** — il est déjà listé dans `.gitignore`. Ne partagez jamais son contenu réel.

---

## 7. Redis via Docker

Le broker Celery nécessite Redis. Le plus simple sous Windows est de le lancer via Docker :

```powershell
docker run -d --name crowdfunding-redis -p 6379:6379 redis:7-alpine
```

Vérifier que Redis répond :

```powershell
docker exec -it crowdfunding-redis redis-cli ping
```

→ Doit répondre `PONG`.

> 💡 Ce conteneur persiste entre les redémarrages de session. Si Docker Desktop a été relancé et que le conteneur n'apparaît plus dans `docker ps`, redémarrez-le avec :
> ```powershell
> docker start crowdfunding-redis
> ```

---

## 8. Migrations

```powershell
python manage.py migrate
```

Cette commande applique **toutes** les migrations de toutes les apps (accounts, wallets, projects, transactions, investments, repayments, notifications, django_celery_results...).

---

## 9. Créer le superutilisateur

```powershell
python manage.py createsuperuser
```

Renseignez un **email** (pas de username, le projet utilise l'email comme identifiant), puis un mot de passe robuste.

> ⚠️ Après création, connectez-vous à `/admin/` et vérifiez/définissez manuellement le champ **Rôle** sur `SUPERADMIN` et **Email vérifié** sur `True` — ces champs ne sont pas positionnés automatiquement par `createsuperuser`.

---

## 10. Créer le compte plateforme

Nécessaire pour que les commissions (Étape 12) soient perçues :

```powershell
python manage.py create_platform_account
```

Ce compte est unique, n'a pas de mot de passe utilisable, et reçoit automatiquement un wallet.

---

## 11. Lancer le serveur Django

```powershell
python manage.py runserver
```

L'API est accessible sur **http://127.0.0.1:8000/**.

---

## 12. Lancer le worker Celery

Dans un **terminal séparé** (venv activé) :

```powershell
celery -A config worker --loglevel=info --pool=solo
```

> ⚠️ `--pool=solo` est **obligatoire sous Windows** (Celery ne supporte pas nativement le mode `prefork` basé sur `fork()` sous Windows).

Le worker doit rester actif pour que les emails d'activation et les notifications soient traités.

---

## 13. Documentation API

Une fois le serveur lancé :

| Interface | URL |
|---|---|
| Swagger UI (interactif) | http://127.0.0.1:8000/api/docs/ |
| Redoc (lecture) | http://127.0.0.1:8000/api/redoc/ |
| Schéma OpenAPI brut | http://127.0.0.1:8000/api/schema/ |

---

## 14. Lancer les tests

Suite complète du projet :

```powershell
python manage.py test apps.accounts apps.investors apps.companies apps.projects apps.wallets apps.transactions apps.investments apps.repayments apps.notifications --verbosity=2
```

Tests d'une seule app :

```powershell
python manage.py test apps.wallets --verbosity=2
```

> 💡 En mode test, `CELERY_TASK_ALWAYS_EAGER=True` est automatiquement activé — les tâches Celery s'exécutent en synchrone, sans dépendre de Redis ni du worker.

---

## 15. Structure du projet

```
crowdfunding_platform/
├── config/
│   ├── settings/
│   │   ├── base.py          # Configuration commune
│   │   └── dev.py           # Configuration développement
│   ├── urls.py               # Routeur principal
│   └── celery.py             # Configuration Celery
├── apps/
│   ├── accounts/              # Authentification JWT, activation, RBAC
│   ├── investors/             # Profils investisseurs (KYC)
│   ├── companies/             # Profils entreprises (KYB)
│   ├── projects/               # Campagnes de crowdfunding
│   ├── wallets/                # Portefeuilles financiers
│   ├── transactions/           # Dépôts, retraits, investissements
│   ├── investments/            # Portefeuille d'investissements
│   ├── repayments/              # Plans et échéances de remboursement
│   └── notifications/           # Notifications in-app (Celery)
├── requirements/
│   └── base.txt
├── .env                        # Secrets (jamais commité)
├── .gitignore
└── manage.py
```

---

## 16. Dépannage (erreurs fréquentes)

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ImproperlyConfigured: SECRET_KEY` | `.env` manquant ou mal rempli | Vérifier le contenu de `.env`, section 6 |
| `permission denied for schema public` | Droits PostgreSQL manquants | Refaire la section 5.3 |
| `Got an error creating the test database` | Utilisateur PostgreSQL sans droit `CREATEDB` | `ALTER USER crowdfunding_user CREATEDB;` |
| `django.db.utils.InconsistentMigrationHistory` | Migrations appliquées dans le mauvais ordre après changement de `AUTH_USER_MODEL` | Réinitialiser le schéma : `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` puis refaire 5.3 et 8 |
| Le worker Celery n'a aucune tâche listée dans `[tasks]` | Le worker a été lancé avant l'ajout des tâches | Redémarrer le worker (`Ctrl+C` puis relancer) |
| `CommandError: No module named 'apps'` | `manage.py`/`wsgi.py` mal configuré | Vérifier que `apps/__init__.py` existe |
| Accents mal affichés dans PowerShell (`Ã©`) | Encodage d'affichage du terminal, pas un bug applicatif | Les données sont correctement stockées en UTF-8 ; ignorer ou lancer `chcp 65001` |
| `redis.exceptions.ConnectionError` | Conteneur Redis arrêté | `docker start crowdfunding-redis` |
| PostgreSQL sur un port inattendu (ex: 8000) | Conflit entre plusieurs installations locales | Vérifier `postgresql.conf`, ajuster `DB_PORT` dans `.env` |

---

## ✅ Checklist de vérification finale

- [ ] `python manage.py check` → `System check identified no issues`
- [ ] `python manage.py migrate` → toutes les migrations appliquées
- [ ] `docker exec -it crowdfunding-redis redis-cli ping` → `PONG`
- [ ] `python manage.py runserver` → démarre sans erreur
- [ ] `celery -A config worker --loglevel=info --pool=solo` → `ready.`
- [ ] http://127.0.0.1:8000/api/docs/ → Swagger UI s'affiche
- [ ] Suite de tests complète → `OK`

