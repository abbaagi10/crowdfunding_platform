from rest_framework import serializers
from .models import Category, Project


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'slug')
        read_only_fields = ('slug',)


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer principal du projet, utilisé pour la création et la consultation
    par l'entreprise propriétaire.
    """

    company_name = serializers.CharField(source='company.company_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    funding_percentage = serializers.ReadOnlyField()
    is_open_for_investment = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = (
            'id', 'company', 'company_name', 'category', 'category_name',
            'title', 'slug', 'short_description', 'full_description', 'cover_image',
            'funding_goal', 'current_amount', 'funding_percentage',
            'start_date', 'end_date',
            'status', 'admin_feedback', 'is_open_for_investment',
            'created_at', 'updated_at',
        )
        # company : assigné automatiquement dans la vue (jamais fourni par le client, voir perform_create)
        # current_amount : mis à jour uniquement par le futur module Investment, jamais manuellement
        # status et admin_feedback : gérés par un endpoint de modération séparé (voir ProjectModerationView)
        read_only_fields = (
            'company', 'slug', 'current_amount', 'status', 'admin_feedback',
            'created_at', 'updated_at',
        )

    def validate(self, attrs):
        """
        Réutilise la validation du modèle (clean()) au niveau serializer,
        pour que les erreurs remontent proprement en JSON via l'API,
        plutôt que de lever une exception Python brute.
        """
        instance = Project(**{**(self.instance.__dict__ if self.instance else {}), **attrs})
        try:
            instance.clean()
        except Exception as e:
            # Convertit les erreurs Django ValidationError (dict) en erreurs DRF
            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError(str(e))
        return attrs


class ProjectModerationSerializer(serializers.ModelSerializer):
    """
    Serializer réservé à l'administration pour la modération d'un projet :
    valider, refuser, ou demander des corrections.
    """

    class Meta:
        model = Project
        fields = ('status', 'admin_feedback')

    def validate_status(self, value):
        """
        Restreint les statuts qu'un modérateur peut assigner via CET endpoint.
        Un modérateur ne doit pas pouvoir mettre un projet en 'DRAFT' par exemple
        (ça n'a pas de sens dans le contexte de modération).
        """
        allowed_moderation_statuses = (
            Project.Status.APPROVED,
            Project.Status.REJECTED,
            Project.Status.NEEDS_CORRECTION,
        )
        if value not in allowed_moderation_statuses:
            raise serializers.ValidationError(
                f"Un modérateur ne peut assigner que : {', '.join(allowed_moderation_statuses)}."
            )
        return value
