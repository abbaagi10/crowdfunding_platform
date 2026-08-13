from django.db import transaction as db_transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsAdminOrSuperAdmin
from apps.notifications.tasks import create_notification
from apps.notifications.models import Notification
from .models import Category, Project
from .permissions import IsProjectOwnerOrAdminOrReadOnly, IsEntrepriseRole
from .serializers import CategorySerializer, ProjectSerializer, ProjectModerationSerializer


class CategoryListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/projects/categories/
    Liste publique des catégories (nécessaire pour construire un formulaire
    de création de projet côté frontend, par exemple).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)


class ProjectListCreateView(generics.ListCreateAPIView):
    """
    Endpoint GET/POST /api/v1/projects/projects/

    GET : liste des projets, filtrée selon le rôle de l'utilisateur :
        - Investisseur / non-authentifié : uniquement les projets ACTIFS (publics)
        - Entreprise : ses propres projets (tous statuts confondus)
        - Admin : tous les projets, tous statuts

    POST : création d'un nouveau projet, réservée aux Entreprises (IsEntrepriseRole).
    """
    serializer_class = ProjectSerializer

    def get_permissions(self):
        """
        Permissions différentes selon la méthode HTTP :
        - GET : accessible à tous (même non authentifié, pour parcourir les projets publics)
        - POST : réservé aux entreprises
        """
        if self.request.method == 'POST':
            return [IsEntrepriseRole()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user

        # Utilisateur non authentifié : uniquement les projets actifs et publics
        if not user.is_authenticated:
            return Project.objects.filter(status=Project.Status.ACTIVE).select_related('company', 'category')

        # Admin : voit tout, sans filtre
        if user.role in (user.Role.USERADMIN, user.Role.SUPERADMIN):
            return Project.objects.all().select_related('company', 'category')

        # Entreprise : voit UNIQUEMENT ses propres projets, tous statuts confondus
        if user.role == user.Role.ENTREPRISE:
            return Project.objects.filter(company__user=user).select_related('company', 'category')

        # Investisseur (et tout autre rôle) : uniquement les projets actifs et publics
        return Project.objects.filter(status=Project.Status.ACTIVE).select_related('company', 'category')

    def perform_create(self, serializer):
        """
        Assigne automatiquement l'entreprise du user connecté au nouveau projet.
        Empêche qu'une entreprise crée un projet au nom d'une AUTRE entreprise
        en manipulant le champ 'company' dans la requête (d'ailleurs read_only
        dans le serializer, donc double protection).
        """
        company_profile = self.request.user.company_profile
        serializer.save(company=company_profile, status=Project.Status.DRAFT)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Endpoint GET/PUT/PATCH/DELETE /api/v1/projects/projects/<id>/
    Consultation libre (si le projet est public), modification/suppression
    réservée au propriétaire ou à l'administration.
    """
    queryset = Project.objects.all().select_related('company', 'category')
    serializer_class = ProjectSerializer
    permission_classes = (IsProjectOwnerOrAdminOrReadOnly,)



@extend_schema(
    tags=['projects'],
    request=None,
    responses={200: ProjectSerializer}
)
class ProjectSubmitForReviewView(APIView):
    """
    Endpoint POST /api/v1/projects/projects/<id>/submit/
    Permet à l'entreprise propriétaire de soumettre son projet (DRAFT -> PENDING)
    pour validation par l'administration.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"detail": "Projet introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Seul le propriétaire peut soumettre SON projet
        if project.company.user != request.user:
            return Response(
                {"detail": "Vous ne pouvez soumettre que vos propres projets."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Transition contrôlée : on ne peut soumettre que depuis DRAFT ou NEEDS_CORRECTION
        if project.status not in (Project.Status.DRAFT, Project.Status.NEEDS_CORRECTION):
            return Response(
                {"detail": f"Impossible de soumettre un projet au statut '{project.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        project.status = Project.Status.PENDING
        project.save()

        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

@extend_schema(
    tags=['projects'],
    request=ProjectModerationSerializer,
    responses={200: ProjectSerializer}
)
class ProjectModerationView(APIView):
    """
    Endpoint PATCH /api/v1/projects/projects/<id>/moderate/
    Réservé à l'administration : Valider / Refuser / Demander correction.
    """
    permission_classes = (IsAdminOrSuperAdmin,)

    def patch(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response({"detail": "Projet introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # On ne modère que les projets en attente de validation
        if project.status != Project.Status.PENDING:
            return Response(
                {"detail": f"Seuls les projets 'En attente de validation' peuvent être modérés (statut actuel : '{project.get_status_display()}')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProjectModerationSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        # Si APPROVED, on active directement le projet (démarre la collecte)
        if new_status == Project.Status.APPROVED:
            serializer.save(status=Project.Status.ACTIVE)
        else:
            serializer.save()
            
        notification_title = {
            Project.Status.ACTIVE: "Projet approuvé",
            Project.Status.REJECTED: "Projet refusé",
            Project.Status.NEEDS_CORRECTION: "Corrections demandées",
        }.get(project.status, "Mise à jour de votre projet")

        db_transaction.on_commit(lambda: create_notification.delay(
            user_id=project.company.user.pk,
            notification_type=Notification.NotificationType.PROJECT_APPROVED if project.status == Project.Status.ACTIVE else Notification.NotificationType.PROJECT_REJECTED,
            title=notification_title,
            message=f"Le statut de votre projet '{project.title}' est maintenant : {project.get_status_display()}.",
        ))    

        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)
