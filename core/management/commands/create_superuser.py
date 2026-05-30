from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates a superuser if one does not already exist'

    def handle(self, *args, **options):
        if User.objects.filter(username='felix').exists():
            self.stdout.write(self.style.WARNING('Superuser "felix" already exists'))
            user = User.objects.get(username='felix')
            if user.email != 'felixochieng5785@gmail.com':
                user.email = 'felixochieng5785@gmail.com'
                user.save()
                self.stdout.write(self.style.SUCCESS('Updated email for superuser "felix"'))
            user.set_password('171630m')
            user.save()
            self.stdout.write(self.style.SUCCESS('Updated password for superuser "felix"'))
        else:
            User.objects.create_superuser(
                username='felix',
                email='felixochieng5785@gmail.com',
                password='171630m'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created superuser "felix"'))
