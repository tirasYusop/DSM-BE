from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()



class Command(BaseCommand):

    help = "Seed initial system users"


    def handle(self, *args, **kwargs):

        users = [

            {
                "username":"management",
                "email":"management@system.com",
                "password":"Admin12345",
                "role":"management",
                "is_staff":True,
            },

            {
                "username":"kolej_mustapha",
                "email":"tun@system.com",
                "password":"Admin12345",
                "role":"volunteer",
                "is_staff":False,
            },

            {
                "username":"kolej_fuad",
                "email":"fuad@system.com",
                "password":"Admin12345",
                "role":"volunteer",
                "is_staff":False,
            },

        ]


        for data in users:


            if User.objects.filter(
                username=data["username"]
            ).exists():

                self.stdout.write(
                    self.style.WARNING(
                        f"{data['username']} already exists"
                    )
                )

                continue



            user = User.objects.create_user(

                username=data["username"],

                email=data["email"],

                password=data["password"],

                role=data["role"]

            )


            user.is_staff = data["is_staff"]

            user.save()



            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {user.username}"
                )
            )