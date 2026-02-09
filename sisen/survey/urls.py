from django.urls import path
from sisen.survey.views import (
    main, 
    student, 
    professor, 
    admin, 
    institution, 
    program, 
    sclass, 
    recommendation, 
    product_rating,
    suggestion, # New Import
)

from sisen.survey.tools import export_data

urlpatterns = [
    path(r'switcher/role/<slug:role>', main.home_page_switcher, name='home_page_switcher'),

    path(r'signup', student.register_student, name='register_student'),

    path(r'student-view', student.student_home, name='student_home'),
    path(r'student-view/email-verification/verify/<str:token>', student.verify_email, name='verify-email'),
    path(r'student-view/email-verification/invalidate-token/<str:token>', student.delete_verification_token, name='invalidate_verification_token'),

    path(r'study/<int:study_id>/answer', student.answer, name='answer'),
    path(r'study/<int:study_id>/process', student.process_answer, name='process_answer'),
    path(r'study/<int:study_id>/report', student.survey_report, name='survey_report'),

    path(r'professor-view', professor.professor_home, name='professor_home'),
    path(r'class/<int:class_id>/study/<int:study_id>/synthetic-report', professor.survey_synthetic_report, name='survey_synthetic_report'),
    path(r'class/<int:class_id>/study/<int:study_id>/analytical-report', professor.survey_analytical_report, name='survey_analytical_report'),

    path(r'institution', institution.list, name='list_institution'),
    path(r'institution/<int:institution_id>', institution.detail, name='institution_detail'),
    path(r'institution/<int:institution_id>/program', program.list, name='list_program'),
    path(r'institution/<int:institution_id>/program/<int:program_id>', program.detail, name='program_detail'),
    path(r'institution/<int:institution_id>/program/<int:program_id>/class', sclass.list, name='list_class'),
    path(r'institution/<int:institution_id>/program/<int:program_id>/class/<int:class_id>', sclass.detail, name='class_detail'),


    # Recommendation views
    path(r"products/all/<int:class_id>", recommendation.get_all_educational_products_for_professor, name="get_all_educational_products_for_professor"),
    path(r"products/all", recommendation.get_all_educational_products_for_students, name="get_all_educational_products_for_students"),
    path(r"products/student", recommendation.get_student_educational_products, name="get_student_educational_products"),
    path(r"products/professor/<int:class_id>", recommendation.get_professor_educational_products, name="get_professor_educational_products"),
    path(r"products/<str:product_name>", recommendation.get_specific_educational_products, name="get_specific_educational_products"),
    
    # Methodology views
    path(r"methodology/professor", recommendation.get_professor_methodology, name="get_professor_methodology"),
    path(r"methodology/all", recommendation.get_all_teaching_methodology, name="get_all_teaching_methodology"),
    path(r"methodology/<str:methodology_name>", recommendation.get_specific_teaching_methodology, name="get_specific_teaching_methodology"),
    
    # Rating views
    path(r"rating/register", product_rating.register_rating, name="register_rating"),
    
    # Favorite views
    path(r"favorite/register", product_rating.register_favorite, name="register_favorite"),
    
    # Recommendation Professor to Student
    path(r"recommendation-to-student", product_rating.register_recommendation_professor_to_student, name="register_recommendation_professor_to_student"),
    
    # NEW: Suggestion and Review views
    path(r"product/suggest", suggestion.suggest_product, name="suggest_product"),
    path(r"educational-types", suggestion.get_educational_types, name="get_educational_types"),
    path(r"admin/pending-products", suggestion.get_pending_products, name="get_pending_products"),
    path(r"admin/product/<int:product_id>/review", suggestion.review_product, name="review_product"),

    # Export CSV data
    path(r'export-survey-data', export_data.export_survey_csv, name='export_survey_csv'),
    
    path(r'admin-view', admin.admin_home, name='admin_home'),
]