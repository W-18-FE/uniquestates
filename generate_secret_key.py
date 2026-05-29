#!/usr/bin/env python
"""
Generate a secure SECRET_KEY for Django
Run this to get a strong secret key for your Render environment variables
"""

from django.core.management.utils import get_random_secret_key

if __name__ == '__main__':
    secret_key = get_random_secret_key()
    print("\n" + "="*60)
    print("GENERATED SECRET KEY FOR DJANGO")
    print("="*60)
    print(secret_key)
    print("="*60)
    print("\nCopy this value to your Render environment variables")
    print("Variable name: SECRET_KEY")
    print("="*60 + "\n")
