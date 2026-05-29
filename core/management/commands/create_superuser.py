from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates a superuser if one does not already exist'

    def handle(self, *args, **options):
        if User.objects.filter(username='felix').exists():
            self.stdout.write(self.style.WARNING('Superuser "felix" already exists'))
        else:
            User.objects.create_superuser(
                username='felix',
                email='felixochieng5785@gmail.com',
                password='171630m@felix'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created superuser "felix"'))
