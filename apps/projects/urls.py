from django.urls import path
from .views import (
    CategoryListView,
    ProjectListCreateView,
    ProjectDetailView,
    ProjectSubmitForReviewView,
    ProjectModerationView,
)

app_name = 'projects'

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('projects/', ProjectListCreateView.as_view(), name='project_list_create'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/submit/', ProjectSubmitForReviewView.as_view(), name='project_submit'),
    path('projects/<int:pk>/moderate/', ProjectModerationView.as_view(), name='project_moderate'),
]
