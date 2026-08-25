from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from apps.accounts.permissions import IsAdminOrSuperAdmin
from .models import CompanyProfile
from .permissions import IsCompanyProfileOwnerOrAdmin
from .serializers import CompanyProfileSerializer, CompanyProfileAdminUpdateSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from apps.companies.models import CompanyProfile
from apps.companies.serializers import CompanyProfileSerializer


class MyCompanyProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint GET/PUT/PATCH /api/v1/companies/profile/me/
    Permet à l'entreprise connectée de consulter et modifier SON PROPRE profil.
    """
    serializer_class = CompanyProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        profile, created = CompanyProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'company_name': f"Entreprise de {self.request.user.email}",
                'registration_number': f"TEMP-{self.request.user.pk}",
            }
        )
        return profile


class CompanyProfileListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/companies/profiles/
    Réservé à l'administration : liste tous les profils entreprises.
    """
    queryset = CompanyProfile.objects.all().select_related('user').order_by('-created_at')
    serializer_class = CompanyProfileSerializer
    permission_classes = (IsAdminOrSuperAdmin,)


class CompanyProfileDetailView(generics.RetrieveAPIView):
    """
    Endpoint GET /api/v1/companies/profiles/<id>/
    Consultation d'un profil précis : propriétaire OU admin uniquement.
    """
    queryset = CompanyProfile.objects.all().select_related('user')
    serializer_class = CompanyProfileSerializer
    permission_classes = (IsAuthenticated, IsCompanyProfileOwnerOrAdmin)


@extend_schema(
    tags=['companies'],
    request=CompanyProfileAdminUpdateSerializer,
    responses={200: CompanyProfileSerializer}
)
class CompanyProfileVerificationView(APIView):
    """
    Endpoint PATCH /api/v1/companies/profiles/<id>/verify/
    Réservé à l'administration : approuve ou rejette un dossier KYB.
    """
    permission_classes = (IsAdminOrSuperAdmin,)

    def patch(self, request, pk):
        try:
            profile = CompanyProfile.objects.get(pk=pk)
        except CompanyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CompanyProfileAdminUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            CompanyProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )


# ============ ENDPOINTS D'UPLOAD DE FICHIERS ============

class UploadCompanyLogoView(APIView):
    """
    POST /api/v1/companies/profile/upload-logo/
    Upload du logo de l'entreprise
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            profile = CompanyProfile.objects.get(user=request.user)
        except CompanyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil entreprise non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )

        if 'logo' not in request.FILES:
            return Response(
                {"detail": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.company_logo = request.FILES['logo']
        profile.save()
        
        serializer = CompanyProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UploadRegistrationDocumentView(APIView):
    """
    POST /api/v1/companies/profile/upload-registration/
    Upload du document d'enregistrement (Kbis)
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            profile = CompanyProfile.objects.get(user=request.user)
        except CompanyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil entreprise non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )

        if 'document' not in request.FILES:
            return Response(
                {"detail": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.registration_document = request.FILES['document']
        profile.save()
        
        serializer = CompanyProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UploadIdentityDocumentView(APIView):
    """
    POST /api/v1/companies/profile/upload-identity/
    Upload de la pièce d'identité du représentant
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            profile = CompanyProfile.objects.get(user=request.user)
        except CompanyProfile.DoesNotExist:
            return Response(
                {"detail": "Profil entreprise non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )

        if 'document' not in request.FILES:
            return Response(
                {"detail": "Aucun fichier fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.legal_representative_id_document = request.FILES['document']
        profile.save()
        
        serializer = CompanyProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompanyProfileListView(ListAPIView):
    """
    Vue réservée à l'administration pour lister tous les profils entreprises.
    GET /api/v1/companies/profiles/
    """
    permission_classes = [IsAdminUser]
    queryset = CompanyProfile.objects.all()
    serializer_class = CompanyProfileSerializer
    
    def get_queryset(self):
        # Filtrer pour ne montrer que les profils en attente ou récents
        return super().get_queryset().order_by('-created_at')
    