from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError

User = get_user_model()


class Command(BaseCommand):
    """
    Commande : python manage.py create_platform_account

    Cree LE compte systeme representant la plateforme elle-meme dans le
    systeme comptable (percoit les commissions). Ne doit etre execute
    QU'UNE SEULE FOIS par environnement (dev, staging, prod).

    Ce compte n'est JAMAIS accessible via l'inscription publique
    (verrouille par RegisterSerializer.validate_role()).
    """
    help = "Cree le compte systeme PLATFORM (une seule instance doit exister)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='platform@crowdfunding.internal',
            help="Email du compte plateforme (par defaut: platform@crowdfunding.internal)"
        )

    def handle(self, *args, **options):
        email = options['email']

        if User.objects.filter(role=User.Role.PLATFORM).exists():
            self.stdout.write(self.style.WARNING(
                "Un compte PLATFORM existe deja. Aucune action effectuee."
            ))
            return

        try:
            # set_unusable_password() : ce compte ne doit JAMAIS pouvoir se
            # connecter via login/mot de passe -- il n'est utilise QUE comme
            # entite comptable interne, jamais comme session utilisateur reelle.
            user = User(
                email=email,
                first_name="Plateforme",
                last_name="Crowdfunding",
                role=User.Role.PLATFORM,
                is_email_verified=True,  # Pas de flux d'activation pour ce compte systeme
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
        except IntegrityError:
            self.stdout.write(self.style.ERROR(f"Un compte avec l'email '{email}' existe deja."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Compte PLATFORM cree avec succes : {email} (id={user.pk})"
        ))
