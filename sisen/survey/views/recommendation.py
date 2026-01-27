from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sisen.survey.exceptions import Conflict
from sisen.survey.permissions import IsStudent, IsStudentOrProfessor, IsProfessor
from random import sample
from sisen.survey.products_methodologies import (
    get_methodology_by_name,
    get_products,
    get_methodologies,
    get_specific_methodologies_by_scores,
    find_value_by_description2,
    get_specific_products,
    add_score_to_methodology,
    get_products_sorted_by_similarity_score,
)
import sisen.survey.models as models
from sisen.survey.views.main import get_object_or_not_found
import sisen.survey.businesses as business
from sisen.survey.businesses import LEARNING_STYLES_ID, INTELLIGENCES_ID
from sisen.survey.views.student import study_answered_or_error, study_answered
from django.db.models import Avg
from sisen.survey.views.product_rating import (
    get_user_votes,
    get_professors_to_student_recommendations,
    get_if_professor_recommended,
    get_if_student_favorite,
)
from rest_framework.pagination import LimitOffsetPagination
from math import ceil


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsStudent))
def get_student_educational_products(request):
    """
    Retrieve educational products recommended for a student based on their scores for learning styles and intelligences.
    Use the student's scores to calculate the similarity between the student and the educational products.
    """
    student_score = []
    student = request.user.student
    for study_id in [LEARNING_STYLES_ID, INTELLIGENCES_ID]:
        study = get_object_or_not_found(
            models.Study, study_id, "O estudo solicitado não existe (ID=%i)" % study_id
        )
        study_answered_or_error(student, study)
        student_score.append(business.process_answer(study, student))

    styles_score = student_score[0].study_option_scores
    intelligences_score = student_score[1].study_option_scores

    student_score_by_code = {obj.code: obj.value for obj in styles_score}
    student_score_by_code.update({obj.code: obj.value for obj in intelligences_score})

    products_list = get_products_sorted_by_similarity_score(
        student_score_by_code, get_products()
    )

    # get all educational products with score greater than 0.85
    products_sorted_by_score = sorted(
        products_list, key=lambda x: x["score"], reverse=True
    )
    selected_products = [
        product for product in products_sorted_by_score if product["score"] > 0.85
    ]

    # The amount of recommended products is determined by the total number of products.
    recommended_count = ceil(0.5 * len(products_sorted_by_score) - 0.5)

    # If there are not enough highly scored products, take the top products overall.
    if len(selected_products) < recommended_count:
        selected_products = products_sorted_by_score[:recommended_count]
    else:
        selected_products = selected_products[:recommended_count]

    return Response({"selectedProducts": selected_products})


# TODO - Refactor this function to use the new similarity score calculation
def generate_teaching_methodology_score_for_professor(request):
    styles_score = {}
    intelligences_score = {}
    total_students = 0
    for sclass in request.user.professor.classes.all():
        for student in sclass.students.all():
            student_score = {}
            for study_id in [LEARNING_STYLES_ID, INTELLIGENCES_ID]:
                study = get_object_or_not_found(
                    models.Study,
                    study_id,
                    "O estudo solicitado não existe (ID=%i)" % study_id,
                )
                if study_answered(student, study):
                    student_score[study_id] = business.process_answer(study, student)

            # Check if the student has answered the study for Learning Styles and Intelligences
            if len(student_score) == 2:
                if total_students == 0:  # First student
                    styles_score = {
                        obj.code: obj.value
                        for obj in student_score[LEARNING_STYLES_ID].study_option_scores
                    }
                    intelligences_score = {
                        obj.code: obj.value
                        for obj in student_score[INTELLIGENCES_ID].study_option_scores
                    }
                else:
                    # Sum the scores for each student
                    for obj in student_score[LEARNING_STYLES_ID].study_option_scores:
                        styles_score[obj.code] += obj.value
                    for obj in student_score[INTELLIGENCES_ID].study_option_scores:
                        intelligences_score[obj.code] += obj.value

                total_students += 1
    
    methodologies = all_teaching_methodology()
    recommendation = []
    if total_students > 0:
        for methodology in methodologies:
            score = 0
            total_features = len(methodology["learning_intelligences"]) + len(
                methodology["learning_styles"]
            )
            for intelligence in methodology["learning_intelligences"]:
                score += (
                    find_value_by_description2(intelligences_score, intelligence)
                    / total_features
                )

            for style in methodology["learning_styles"]:
                score += find_value_by_description2(styles_score, style) / total_features
            recommendation.append((methodology["name"], score / 100))
        recommendation.sort(
            key=lambda x: x[1], reverse=True
        )  # Ordenar produtos por pontuação decrescente
        return recommendation
    
    # if there are no students, return the list of educational products without scores
    for methodology in methodologies:
        methodology["score"] = 0
        recommendation.append((methodology["name"], 0))
    return recommendation


def generate_educational_products_score_for_professor(request, class_id):
    """
    Calculate recommendation based on students' scores for learning styles and intelligences.

    Parameters:
    - request: Request object containing user information

    Returns:
    - List of tuples containing product name and calculated score, sorted in descending order based on score

    Raises:
    - Conflict: If there are not enough students to calculate style and intelligence scores
    """
    styles_score = {}
    intelligences_score = {}
    total_students = 0
    
    selected_class = get_object_or_not_found(
        models.Class,
        class_id,
        "A turma solicitada não existe (ID=%i)" % class_id,
    )
    if selected_class not in request.user.professor.classes.all():
        raise Conflict("A turma solicitada não pertence ao professor logado.")
    
    for student in selected_class.students.all():
        student_score = {}
        for study_id in [LEARNING_STYLES_ID, INTELLIGENCES_ID]:
            study = get_object_or_not_found(
                models.Study,
                study_id,
                "O estudo solicitado não existe (ID=%i)" % study_id,
            )
            if study_answered(student, study):
                student_score[study_id] = business.process_answer(study, student)

        # Check if the student has answered the study for Learning Styles and Intelligences
        if len(student_score) == 2:
            if total_students == 0:  # First student
                styles_score = {
                    obj.code: obj.value
                    for obj in student_score[LEARNING_STYLES_ID].study_option_scores
                }
                intelligences_score = {
                    obj.code: obj.value
                    for obj in student_score[INTELLIGENCES_ID].study_option_scores
                }
            else:
                # Sum the scores for each student
                for obj in student_score[LEARNING_STYLES_ID].study_option_scores:
                    styles_score[obj.code] += obj.value
                for obj in student_score[INTELLIGENCES_ID].study_option_scores:
                    intelligences_score[obj.code] += obj.value

            total_students += 1

    # Check if no student has answered the study for Learning Styles or Intelligences
    if total_students > 0:
        student_score_by_code = dict(styles_score, **intelligences_score)

        for key in student_score_by_code:
            student_score_by_code[key] = student_score_by_code[key] / total_students

        products_list = get_products_sorted_by_similarity_score(
            student_score_by_code, get_products(class_id)
        )
    
        return products_list    

    # if there are no students, return the list of educational products without scores
    products_list = sorted(get_products(class_id), key=lambda x: x["name"])
    for product in products_list:
        product["score"] = 0

    return products_list


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsProfessor))
def get_professor_educational_products(request, class_id):
    """
    Retrieve educational products recommended for a professor based on students' scores.

    Parameters:
    - request: Request object containing user information

    Returns:
    - Response with selected educational products for the professor

    Raises:
    - Conflict: If there are not enough students to calculate style and intelligence scores
    """
    recommendation = generate_educational_products_score_for_professor(request, class_id)

    # get all educational products with score greater than 0.75]
    selected_products = [
        product for product in recommendation if product["score"] > 0.85
    ]

    # The amount of recommended products is determined by the total number of products.
    recommended_count = ceil(0.5 * len(recommendation) - 0.5)

    # If there are not enough highly scored products, take the top products overall.
    if len(selected_products) < recommended_count:
        selected_products = recommendation[:recommended_count]
    else:
        selected_products = selected_products[:recommended_count]

    return Response({"selectedProducts": selected_products})


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsStudent))
def get_all_educational_products_for_students(request, format=None):
    return Response({"allProducts": all_educational_products()})


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsProfessor))
def get_all_educational_products_for_professor(request, class_id, format=None):
    return Response({"allProducts": generate_educational_products_score_for_professor(request, class_id)})

def all_educational_products():
    return get_products()


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsStudentOrProfessor))
def get_specific_educational_products(request, product_name):
    """
    Retrieve specific educational products based on the user's scores and preferences.

    Parameters:
    - request: The HTTP request object.
    - product_name: The name of the specific educational product to retrieve.

    Returns:
    - Response: A JSON response containing the list of specific educational products based on the user's scores and preferences.
    """
    
    # --- 1. IDENTIFY THE CLASS CONTEXT ---
    class_obj = None
    
    # If Professor: Get class_id from URL
    if request.user.groups.filter(name="Professor").exists():
        class_id = request.query_params.get('class_id')
        if class_id:
            try:
                class_obj = models.Class.objects.get(id=class_id)
                # Security: Verify professor owns this class
                if not request.user.professor.classes.filter(id=class_id).exists():
                    class_obj = None
            except models.Class.DoesNotExist:
                pass
                
    # If Student: Get class from their profile
    elif request.user.groups.filter(name="Student").exists():
        if hasattr(request.user, 'student') and request.user.student.sclass:
            class_obj = request.user.student.sclass

    if request.user and request.user.groups.filter(name__in=["Professor"]):
        styles_score = {}
        intelligences_score = {}
        total_students = 0
        
        # Calculate scores based on the specific class context if available
        target_classes = [class_obj] if class_obj else request.user.professor.classes.all()

        for sclass in target_classes:
            for student in sclass.students.all():
                student_score = {}
                for study_id in [LEARNING_STYLES_ID, INTELLIGENCES_ID]:
                    study = get_object_or_not_found(
                        models.Study,
                        study_id,
                        "O estudo solicitado não existe (ID=%i)" % study_id,
                    )
                    if study_answered(student, study):
                        student_score[study_id] = business.process_answer(
                            study, student
                        )

                # Check if the student has answered the study for Learning Styles and Intelligences
                if len(student_score) == 2:
                    if total_students == 0:
                        styles_score = {
                            obj.code: obj.value
                            for obj in student_score[
                                LEARNING_STYLES_ID
                            ].study_option_scores
                        }
                        intelligences_score = {
                            obj.code: obj.value
                            for obj in student_score[
                                INTELLIGENCES_ID
                            ].study_option_scores
                        }
                    else:
                        for obj in student_score[
                            LEARNING_STYLES_ID
                        ].study_option_scores:
                            styles_score[obj.code] += obj.value
                        for obj in student_score[INTELLIGENCES_ID].study_option_scores:
                            intelligences_score[obj.code] += obj.value

                    total_students += 1

        if total_students > 0:
            student_score_by_code = dict(styles_score, **intelligences_score)

            for key in student_score_by_code:
                student_score_by_code[key] = student_score_by_code[key] / total_students

            # --- PASS CLASS OBJECT HERE ---
            specific_product_list = get_products_sorted_by_similarity_score(
                student_score_by_code, get_specific_products(product_name, class_obj)
            )
        else:
            # --- PASS CLASS OBJECT HERE TOO ---
            specific_product_list = sorted(get_specific_products(product_name, class_obj), key=lambda x: x["name"])
            for product in specific_product_list:
                product["score"] = 0

        for product in specific_product_list:
            product["professor_recommendation"] = get_if_professor_recommended(
                request.user, product["id"]
            )

    # if the user is a student
    else:
        student_score = []
        student = request.user.student
        for study_id in [LEARNING_STYLES_ID, INTELLIGENCES_ID]:
            study = get_object_or_not_found(
                models.Study,
                study_id,
                "O estudo solicitado não existe (ID=%i)" % study_id,
            )
            study_answered_or_error(student, study)
            student_score.append(business.process_answer(study, student))
        styles_score = student_score[0].study_option_scores
        intelligences_score = student_score[1].study_option_scores

        recommendation = {obj.code: obj.value for obj in styles_score}
        recommendation.update({obj.code: obj.value for obj in intelligences_score})

        specific_product_list = get_products_sorted_by_similarity_score(
            recommendation, get_specific_products(product_name, request.user.student.sclass)
        )

        for product in specific_product_list:
            # get if the user has voted for these educational products
            product["user_vote"] = get_user_votes(request.user, product["id"])

            # get if the professor has recommended these educational products
            product["professor_recommendation"] = (
                get_professors_to_student_recommendations(request.user, product["id"])
            )

            # get if the student has marked these educational products as favorites
            product["favorite"] = get_if_student_favorite(request.user.student, product["id"])

    for i, product in enumerate(specific_product_list):
        product["relevance"] = i + 1
    
    favorites_only = request.query_params.get('favorites_only') == 'true'

    if favorites_only and not request.user.groups.filter(name__in=["Professor"]):
        specific_product_list = [
            p for p in specific_product_list if p.get('favorite') is True
        ]

    search_term = request.query_params.get('search', None)
    sort_by = request.query_params.get('sort', 'relevance')

    # 1. Apply Search Filter
    if search_term:
        search_term = search_term.lower()
        specific_product_list = [
            p for p in specific_product_list if
            search_term in p.get('name', '').lower() or
            search_term in p.get('info', '').lower()
        ]

    # 2. Apply Sorting
    if sort_by == 'rating':
        # Sort by net rating (positive votes - negative votes) in descending order
        specific_product_list.sort(
            key=lambda p: p.get('pos_rating', 0) - p.get('neg_rating', 0),
            reverse=True
        )
    elif sort_by == "alphabetical": # 'default' sort
        # Sort by product name in ascending (alphabetical) order
        # This is now the default for all cases unless 'relevance' is specified.
        specific_product_list.sort(key=lambda p: p.get('name', ''))

    paginator = LimitOffsetPagination()

    # The 'paginate_queryset' method handles the slicing based on 'limit' and 'offset' query params
    paginated_product_list = paginator.paginate_queryset(specific_product_list, request)

    # The 'get_paginated_response' method formats the response with 'count', 'next', 'previous', and 'results'
    if paginated_product_list is not None:
        # Note: The data is now in a 'results' key inside the response
        response = paginator.get_paginated_response(paginated_product_list)
        response.data['specificProducts'] = response.data.pop('results') # Rename 'results' to 'specificProducts'

        return response

    return Response({"specificProducts": specific_product_list})


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsProfessor))
def get_professor_methodology(request):
    """
    Retrieve and return a list of 3 randomly selected teaching methodologies for professors. Requires authentication and professor permissions.
    """
    recommendation = generate_teaching_methodology_score_for_professor(request)
    methodologies = all_teaching_methodology()
    # get all educational products with score greater than 0.75]
    selected_methodologies = [
        add_score_to_methodology(
            get_methodology_by_name(methodologies, methodology_name), score
        )
        for methodology_name, score in recommendation
        if score > 0.85
    ]
    # if the number of selected products is less than 2, get the top 2 products with the highest scores
    if len(selected_methodologies) < 2:
        selected_methodologies = [
            add_score_to_methodology(
                get_methodology_by_name(methodologies, methodology_name), score
            )
            for methodology_name, score in recommendation[:2]
        ]
    return Response({"selectedMethodology": selected_methodologies})


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsProfessor))
def get_all_teaching_methodology(request):
    """
    Retrieve all teaching methodologies available for access by authenticated professors.
    """
    teaching_methodology = all_teaching_methodology()
    if request.user and request.user.groups.filter(name__in=["Professor"]):
        recommendation = generate_teaching_methodology_score_for_professor(request)
        teaching_methodology = [
            add_score_to_methodology(
                get_methodology_by_name(teaching_methodology, methodology_name), score
            )
            for methodology_name, score in recommendation
        ]
    return Response({"allMethodology": teaching_methodology})


def all_teaching_methodology():
    """
    Return a list of dictionaries representing different teaching methodologies.
    Each dictionary contains the name, description, and URL of a specific teaching methodology.
    """
    return get_methodologies()


@api_view(["GET"])
@permission_classes((IsAuthenticated, IsProfessor))
def get_specific_teaching_methodology(request, methodology_name):
    # Send a response with error saying that this api doesnt work for now

    return Conflict("This API is not working for now.")

    """
    Retrieve a list of specific teaching methodologies along with their information and links.
    Parameters:
    - request: Request object
    - methodology_name: Name of the teaching methodology
    Returns:
    - Response containing a list of dictionaries with keys 'name', 'info', and 'link' for each specific methodology.
    """
    average_scores = {}
    for sclass in request.user.professor.classes.all():
        total_students = len(sclass.students.all())
        for student in sclass.students.all():
            if study_answered(student, LEARNING_STYLES_ID):
                student_score = business.process_answer(LEARNING_STYLES_ID, student)

                for row in student_score.study_option_scores:
                    if row.code not in average_scores:
                        average_scores[row.code] = 0
                    average_scores[row.code] += row.value / total_students

    # if any of the scores is None, set it to 0
    average_scores = {
        key: value if value is not None else 0 for key, value in average_scores.items()
    }

    sorted_average_scores = sorted(
        average_scores.items(), key=lambda item: item[1], reverse=True
    )

    sorted_styles = []
    for item in sorted_average_scores:
        sorted_styles.append(item[0])

    specific_methodology_list = get_specific_methodologies_by_scores(
        sorted_styles, methodology_name
    )

    return Response({"specificMethodology": specific_methodology_list})