from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrSuperAdmin
from .models import InvestorProfile
from .permissions import IsProfileOwnerOrAdmin
from .serializers import InvestorProfileSerializer, InvestorProfileAdminUpdateSerializer


class MyInvestorProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint GET/PUT/PATCH /api/v1/investors/profile/me/
    Permet à l'investisseur connecté de consulter et modifier SON PROPRE profil.
    Ne nécessite aucun paramètre d'ID dans l'URL : get_object() retourne
    toujours le profil lié à request.user.
    """
    serializer_class = InvestorProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """
        Surcharge de get_object() : au lieu de chercher un objet par son ID
        dans l'URL (comportement par défaut de RetrieveUpdateAPIView),
        on retourne systématiquement le profil du user connecté.
        get_or_create évite un 404 si le profil n'a pas encore été créé.
        """
        profile, _ = InvestorProfile.objects.get_or_create(user=self.request.user)
        return profile


class InvestorProfileListView(generics.ListAPIView):
    """
    Endpoint GET /api/v1/investors/profiles/
    Réservé à l'administration : liste tous les profils investisseurs,
    utile pour la revue des dossiers KYC.
    """
    queryset = InvestorProfile.objects.all().select_related('user').order_by('-created_at')
    serializer_class = InvestorProfileSerializer
    permission_classes = (IsAdminOrSuperAdmin,)


class InvestorProfileDetailView(generics.RetrieveAPIView):
    """
    Endpoint GET /api/v1/investors/profiles/<id>/
    Consultation d'un profil précis par son ID.
    Autorisé pour : le propriétaire du profil OU un admin (IsProfileOwnerOrAdmin).
    """
    queryset = InvestorProfile.objects.all().select_related('user')
    serializer_class = InvestorProfileSerializer
    permission_classes = (IsAuthenticated, IsProfileOwnerOrAdmin)


class InvestorProfileVerificationView(APIView):
    """
    Endpoint PATCH /api/v1/investors/profiles/<id>/verify/
    Réservé à l'administration : approuve ou rejette un dossier KYC.
    """
    permission_classes = (IsAdminOrSuperAdmin,)

    def patch(self, request, pk):
        try:
            profile = InvestorProfile.objects.get(pk=pk)
        except InvestorProfile.DoesNotExist:
            return Response(
                {"detail": "Profil introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = InvestorProfileAdminUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            InvestorProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )