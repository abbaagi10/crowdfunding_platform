from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from .models import CompanyProfile
from .permissions import IsCompanyProfileOwnerOrAdmin
from .serializers import CompanyProfileSerializer, CompanyProfileAdminUpdateSerializer


class MyCompanyProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint GET/PUT/PATCH /api/v1/companies/profile/me/
    Permet à l'entreprise connectée de consulter et modifier SON PROPRE profil.

    Contrairement à InvestorProfile, on ne peut PAS utiliser get_or_create ici
    sans argument supplémentaire : company_name et registration_number sont
    des champs obligatoires (pas de valeur par défaut sensée). Le profil doit
    donc être créé explicitement via un POST, pas silencieusement au premier GET.
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
