# Estatelink - Deployment Guide

## Overview
This Django application is ready to be deployed on Render.com. All necessary configurations have been added for production deployment with an inbuilt superuser.

## Deployment Steps

### Step 1: Push to GitHub

#### If you don't have GitHub:
1. Go to https://github.com/join and create a free account
2. Use your email: felixochieng5785@gmail.com

#### Push your code to GitHub:

```bash
# Create a new repository on GitHub at https://github.com/new
# Name it: uniquestates

# Then run these commands:
git remote add origin https://github.com/YOUR_USERNAME/uniquestates.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render.com

1. **Create a Render account** at https://render.com
   - Sign up with your email: felixochieng5785@gmail.com

2. **Connect GitHub Repository**
   - Go to Render Dashboard → New → Web Service
   - Connect your GitHub account
   - Select `uniquestates` repository
   - Choose branch: `main`

3. **Configure Build and Deploy Settings**
   - **Name**: uniquestates (or any name you prefer)
   - **Runtime**: Python 3.10
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py create_superuser`
   - **Start Command**: `gunicorn config.wsgi:application`

4. **Environment Variables** (Already configured in .env file, but you can override on Render if needed)
   ```
   DEBUG = False
   SECRET_KEY = (from .env - django-insecure-9x#@$%^&*()_+-=[]{}|;:,.<>?/~`felixestatelink2026)
   ALLOWED_HOSTS = uniquestates.onrender.com,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS = https://uniquestates.onrender.com,http://localhost
   ```

5. **Add PostgreSQL Database** (optional but recommended)
   - In Render Dashboard, click New → PostgreSQL
   - Name it: `estatelink-db`
   - The DATABASE_URL will be automatically set
   - Click "Create Database"

6. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

### Step 3: Access Your Deployed App

After deployment completes:

1. **Access the app**: https://uniquestates.onrender.com (replace with your actual URL)

2. **Login to Admin Panel**
   - Go to: https://uniquestates.onrender.com/admin/
   - **Username**: felix
   - **Password**: 171630m
   - **Email**: felixochieng5785@gmail.com

## Important Notes

### Inbuilt Superuser
- The superuser is automatically created during the build process
- If it already exists, the creation command silently skips it
- You can later change the password from the admin panel

### Database
- Currently configured to use SQLite locally
- For production, PostgreSQL is recommended
- Add `DATABASE_URL` environment variable if using PostgreSQL on Render

### Static Files
- WhiteNoise is configured to serve static files
- Collected automatically during build

### Security Settings
- SSL redirect is enabled in production
- HTTPS is enforced for production domains
- CSRF protection is configured

## Troubleshooting

### Deployment Fails
1. Check build logs on Render Dashboard
2. Ensure all environment variables are set
3. Verify database connection (if using PostgreSQL)

### Admin Page Not Loading
- Clear browser cache
- Verify static files were collected (check build logs)
- Ensure DEBUG is set to False in production

### Can't Login with Superuser
- The management command creates superuser if it doesn't exist
- You can manually create it with: `python manage.py createsuperuser`
- Or run the custom command: `python manage.py create_superuser`

## Update Process

To update your app:
1. Make changes locally
2. Commit: `git add . && git commit -m "Your message"`
3. Push: `git push origin main`
4. Render automatically redeploys

## Quick Secret Key Generator
Run this Python code to generate a secure secret key:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## Support
For issues with Render, visit: https://render.com/docs
For Django issues, visit: https://docs.djangoproject.com
