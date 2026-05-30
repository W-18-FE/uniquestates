# Estatelink App

A Django-based estate management application built for managing properties, utilities, services, and community interactions.

## Features
- Admin dashboard for estate management
- Water order management system
- Vendor management and response system
- User notification system
- Bill management
- Lost and found tracking
- Marketplace for estate services
- Security management
- Garbage collection tracking
- Job listings

## Technology Stack
- Django 6.0.5
- Python 3.10+
- PostgreSQL (production)
- SQLite (development)
- Gunicorn (WSGI server)
- WhiteNoise (static files)

## Local Development Setup

### Prerequisites
- Python 3.10 or higher
- pip
- Virtual environment

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/uniquestates.git
cd uniquestates

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Access the Application

- **Web App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions on Render.com

### Default Superuser (Render)
- **Username**: felix
- **Password**: 171630m
- **Email**: felixochieng5785@gmail.com

## Project Structure

```
.
├── config/                 # Django settings and configuration
│   ├── settings.py        # Main settings
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI configuration
├── core/                   # Main application
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   ├── urls.py            # App URL routing
│   ├── templates/         # HTML templates
│   ├── management/        # Custom management commands
│   └── migrations/        # Database migrations
├── static/                # Static files (CSS, JS, images)
├── requirements.txt       # Python dependencies
├── manage.py             # Django management script
├── Procfile              # Render deployment config
└── render.yaml           # Render infrastructure config
```

## Management Commands

### Create Superuser
```bash
python manage.py create_superuser
```

### Run Migrations
```bash
python manage.py migrate
```

### Collect Static Files
```bash
python manage.py collectstatic
```

## Environment Variables

See `.env.example` for all available environment variables.

Key variables:
- `DEBUG` - Django debug mode (False for production)
- `SECRET_KEY` - Django secret key for cryptography
- `DATABASE_URL` - Database connection string
- `ALLOWED_HOSTS` - Comma-separated list of allowed domains

## License

Proprietary

## Support

For deployment issues, see DEPLOYMENT.md
