from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from sisen.survey.exceptions import Conflict, NotFound
from sisen.survey.serializers import UserSerializer, StudentSerializer
from sisen.survey.views.main import get_object_or_not_found
from rest_framework.permissions import IsAuthenticated
from sisen.survey.permissions import IsStudent, IsProfessor
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)

import sisen.survey.models as models


def get_positive_total_rating(product_id):
    """
    Get the total rating of a product from the database.

    Parameters:
    - product (int): The code of the product to get the rating from.

    Returns:
    - int: The total rating of the product.
    """

    # the model stores a float nuumber that represents a binary value
    # 1 means positive rating and 0 means negative rating

    # Count the number of positive ratings for a product
    positive_rating = models.ProductRating.objects.filter(
        product=product_id, rating=1
    ).count()

    return positive_rating


def get_negative_total_rating(product_id):
    """
    Get the total rating of a product from the database.

    Parameters:
    - product (int): The code of the product to get the rating from.

    Returns:
    - int: The total rating of the product.
    """

    # the model stores a float nuumber that represents a binary value
    # 1 means positive rating and 0 means negative rating

    # Count the number of negative ratings for a product
    negative_rating = models.ProductRating.objects.filter(
        product=product_id, rating=0
    ).count()

    return negative_rating


@api_view(["POST"])
@transaction.atomic
@permission_classes((IsAuthenticated, IsStudent))
def register_rating(request, format=None):
    """
    Register a student's rating for a specific educational product.

    Parameters:
    - request: The HTTP request object containing data for the rating.

    Returns:
    - Response: JSON response with the rating data if successful, or error messages if the data is invalid.
    """
    try:
        product_id = request.data["product_id"]
        rating_value = request.data["rating"]
    except KeyError:
        return Response(
            {"detail": "ID do produto e classificação são obrigatórios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_id,
        "O produto especificado não existe (ID=%s)" % product_id,
    )

    student = request.user.student

    if rating_value not in [
        models.ProductRating.POSITIVE,
        models.ProductRating.NEGATIVE,
    ]:
        return Response(
            {"detail": "Valor de classificação inválido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if the same vote already exists
    existing_same_rating = models.ProductRating.objects.filter(
        student=student, product=product, rating=rating_value
    ).first()

    if existing_same_rating:
        # If the same rating already exists, delete it (decrement)
        existing_same_rating.delete()
        return Response(
            {"detail": "Seu voto foi removido com sucesso."},
            status=status.HTTP_200_OK,
        )

    rating, created = models.ProductRating.objects.update_or_create(
        student=student,
        product=product,
        defaults={"rating": rating_value},
    )

    if created:
        return Response(
            {
                "detail": "Muito obrigado por sua contribuição. Sua opinião é importante para nós."
            },
            status=status.HTTP_201_CREATED,
        )
    else:
        return Response(
            {"detail": "Seu voto foi alterado com sucesso!"}, status=status.HTTP_200_OK
        )


def get_user_votes(student, product_type_id, format=None):
    """
    Get the rating of a product by a student.
    """

    # Check if the user is a student
    product = get_object_or_not_found(
        models.EducationalProduct,
        product_type_id,
        "O produto especificado não existe (ID=%s)" % product_type_id,
    )
    student = student.student
    query = models.ProductRating.objects.filter(product=product, student=student)

    if query:
        rating = query.get().rating
        if rating == models.ProductRating.POSITIVE:
            return "Positive"
        else:
            return "Negative"
    return None


# ================================================ #
# ==== Professor Recomendation to the Student ==== #
# ================================================ #


@api_view(["POST"])
@transaction.atomic
@permission_classes((IsAuthenticated, IsProfessor))
def register_recommendation_professor_to_student(request, format=None):

    try:
        product_id = request.data["product_id"]
    except KeyError:
        return Response(
            {"detail": "ID do produto é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_id,
        "O produto especificado não existe (ID=%s)" % product_id,
    )

    professor = request.user.professor
    class_id = request.user.professor.classes.all().first().id

    class_obj = get_object_or_not_found(
        models.Class,
        class_id,
        "A turma especificada não existe (ID=%s)" % class_id,
    )

    # Check if the same vote already exists
    existing_recommendation = models.ProfessorRecommendation.objects.filter(
        product=product, class_id=class_obj
    ).first()

    if existing_recommendation:
        # If the recommendation already exists, delete it
        existing_recommendation.delete()
        return Response(
            {
                "detail": "Recomendação removida com sucesso! Seus alunos não verão mais essa recomendação."
            },
            status=status.HTTP_200_OK,
        )

    existing_recommendation, created = (
        models.ProfessorRecommendation.objects.update_or_create(
            product=product,
            class_id=class_obj,
        )
    )

    if not created:
        raise Conflict(
            "Algum erro ocorreu ao tentar realizar a recomendação. Por favor, tente novamente."
        )

    return Response(
        {
            "detail": "Recomendação realizada com sucesso! Seus alunos verão essa recomendação."
        },
        status=status.HTTP_201_CREATED,
    )


def get_if_professor_recommended(professor, product_type_id):
    """
    Get the recommendations of a professor to a student.
    """

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_type_id,
        "O produto especificado não existe (ID=%s)" % product_type_id,
    )

    class_id = professor.professor.classes.all().first().id

    class_obj = get_object_or_not_found(
        models.Class,
        class_id,
        "A turma especificada não existe (ID=%s)" % class_id,
    )

    query = models.ProfessorRecommendation.objects.filter(
        product=product, class_id=class_obj
    )

    if query:
        return True
    return False


def get_professors_to_student_recommendations(student, product_type_id):
    """
    Get the recommendations of a professor to a student.
    """

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_type_id,
        "O produto especificado não existe (ID=%s)" % product_type_id,
    )

    class_obj = student.student.sclass

    query = models.ProfessorRecommendation.objects.filter(
        product=product, class_id=class_obj
    )

    if query:
        return True
    return False


# ================================================ #
# ==== Favorite Product Register ==== #
# ================================================ #
@api_view(["POST"])
@transaction.atomic
@permission_classes((IsAuthenticated, IsStudent))
def register_favorite(request, format=None):
    """
    Register a student's favorite educational product.

    Parameters:
    - request: The HTTP request object containing data for the favorite product.

    Returns:
    - Response: JSON response with the favorite product data if successful, or error messages if the data is invalid.
    """
    try:
        product_id = request.data["product_id"]
    except KeyError:
        return Response(
            {"detail": "ID do produto é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_id,
        "O produto especificado não existe (ID=%s)" % product_id,
    )

    student = request.user.student

    # Check if the same vote already exists
    existing_favorite = models.FavoriteProduct.objects.filter(
        student=student, product=product
    ).first()

    if existing_favorite:
        # If the favorite already exists, delete it
        existing_favorite.delete()
        return Response(
            {"detail": "Produto removido com sucesso de sua lista de favoritos."},
            status=status.HTTP_200_OK,
        )

    favorite, created = models.FavoriteProduct.objects.update_or_create(
        student=student,
        product=product,
    )

    if not created:
        raise Conflict(
            "Algum erro ocorreu ao tentar adicionar o produto em sua lista de favoritos. Por favor, tente novamente."
        )

    return Response(
        {"detail": "Produto adicionado com sucesso em sua lista de favoritos."},
        status=status.HTTP_201_CREATED,
    )


def get_if_student_favorite(student, product_type_id):
    """
    Get the favorite of a student.
    """

    product = get_object_or_not_found(
        models.EducationalProduct,
        product_type_id,
        "O produto especificado não existe (ID=%s)" % product_type_id,
    )

    query = models.FavoriteProduct.objects.filter(student=student, product=product)

    if query:
        return True
    return False
