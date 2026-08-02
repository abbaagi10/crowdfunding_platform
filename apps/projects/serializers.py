from rest_framework import serializers
from .models import Category, Project


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'slug')
        read_only_fields = ('slug',)


class ProjectSerializer(serializers.ModelSerializer):
    """
    Serializer principal du projet, utilise pour la creation et la consultation
    par l'entreprise proprietaire.
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
        read_only_fields = (
            'company', 'slug', 'current_amount', 'status', 'admin_feedback',
            'created_at', 'updated_at',
        )

    def validate(self, attrs):
        """
        Reutilise la validation du modele (clean()) au niveau serializer.
        Utilise une COPIE de l'instance existante (update) ou une instance
        vide (create), puis applique les nouveaux champs avec setattr,
        pour eviter de reconstruire l'objet via le constructeur (qui rejette
        les attributs internes Django comme _state).
        """
        import copy

        if self.instance:
            instance = copy.copy(self.instance)
        else:
            instance = Project()

        for field_name, value in attrs.items():
            setattr(instance, field_name, value)

        try:
            instance.clean()
        except Exception as e:
            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError(str(e))
        return attrs


class ProjectModerationSerializer(serializers.ModelSerializer):
    """
    Serializer reserve a l'administration pour la moderation d'un projet.
    """

    class Meta:
        model = Project
        fields = ('status', 'admin_feedback')

    def validate_status(self, value):
        allowed_moderation_statuses = (
            Project.Status.APPROVED,
            Project.Status.REJECTED,
            Project.Status.NEEDS_CORRECTION,
        )
        if value not in allowed_moderation_statuses:
            raise serializers.ValidationError(
                f"Un moderateur ne peut assigner que : {', '.join(allowed_moderation_statuses)}."
            )
        return value
