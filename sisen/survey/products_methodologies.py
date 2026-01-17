from sisen.survey.models import (
    EducationalType,
    EducationalProduct,
    LearningMethodology,
    LearningType,
    StudyOption,
    ClassProduct,
    Class,
)
from collections import defaultdict
from random import sample
import numpy as np
from numpy.linalg import norm
from sisen.survey.views.product_rating import (
    get_positive_total_rating,
    get_negative_total_rating,
)


def get_all_possible_styles_and_intelligences():
    return sorted(StudyOption.objects.values_list("code", flat=True))


def cosine_similarity(a, b):
    """
    Calculate the cosine similarity between two vectors.

    Parameters:
    - a (list): The first vector.
    - b (list): The second vector.

    Returns:
    - float: The cosine similarity between the two vectors.
    """

    div = norm(a) * norm(b)
    
    if div == 0:
        return 0
    
    return np.dot(a, b) / div


def sort_products_by_similarity(specific_products, reference_styles):
    """
    Sorts the specific products by similarity to a reference list of learning styles.
    :param specific_products: A dictionary containing specific products categorized by type.
    :param reference_styles: A list of learning styles to compare the products against.
    :return: A dictionary with the specific products sorted by similarity to the reference styles.
    """

    all_styles_and_intelligences = get_all_possible_styles_and_intelligences()

    user_arr = np.array(
        [
            reference_styles[style_or_intelligence]
            for style_or_intelligence in all_styles_and_intelligences
        ]
    )

    # Convert the reference styles to a vector
    for product in specific_products:
        # Get the classification of the product
        product_styles_and_intelligences = product["styles"] + product["intelligences"]

        product_arr = np.array(
            [
                1 if style_or_intelligence in product_styles_and_intelligences else 0
                for style_or_intelligence in all_styles_and_intelligences
            ]
        )
        product["score"] = cosine_similarity(user_arr, product_arr)

    sorted_products = sorted(specific_products, key=lambda x: x["score"], reverse=True)

    return sorted_products


def sort_methodologies_by_similarity(specific_methodologies, reference_styles):
    raise NotImplementedError(
        "Methodologies are not yet implemented with cosine similarity"
    )

    """
    Sorts the specific products by similarity to a reference list of learning styles.
    :param specific_products: A dictionary containing specific products categorized by type.
    :param reference_styles: A list of learning styles to compare the products against.
    :return: A dictionary with the specific products sorted by similarity to the reference styles.
    """

    # if not specific_products:
    #     return []

    sorted_methodologies = []

    sorted_products = sorted(
        specific_methodologies,
        key=lambda x: kendall_distance(reference_styles, x["learning_styles"]),
    )

    return sorted_methodologies


def get_products_sorted_by_similarity_score(recommendation, products_list):
    """
    Get all products sorted by similarity to a recommendation list.
    :param recommendation: A list of learning styles to compare the products against.
    :return: A dictionary with all products sorted by similarity to the recommendation list.
    """
    sorted_products = sort_products_by_similarity(products_list, recommendation)
    return sorted_products


def get_specific_methodologies_by_scores(recommendation, methodology_name):
    """
    Get a specific product by its name based on a recommendation list.
    :param recommendation: A list of learning styles to compare the products against.
    :param product_name: The name of the specific product to retrieve.
    :return: The specific product sorted by similarity to the recommendation list.
    """
    sorted_specific_products = sort_methodologies_by_similarity(
        get_specific_methodologies(methodology_name), recommendation
    )
    return sorted_specific_products


def get_methodologies():
    educational_types_raw = LearningType.objects.select_related(
        "learning_styles", "learning_intelligences"
    ).values(
        "id",
        "code",
        "name",
        "description",
        "styles__code",
        "intelligences__code",
    )

    educational_types = defaultdict(
        lambda: {"learning_styles": [], "learning_intelligences": []}
    )

    for et in educational_types_raw:
        et_id = et["id"]
        if "id" not in educational_types[et_id]:
            educational_types[et_id].update(
                {
                    "id": et_id,
                    "name": et["name"],
                    "description": et["description"],
                    "code": et["code"],
                }
            )
        if et["styles__code"] not in educational_types[et_id]["learning_styles"]:
            educational_types[et_id]["learning_styles"].append(et["styles__code"])
        if (
            et["intelligences__code"]
            not in educational_types[et_id]["learning_intelligences"]
        ):
            educational_types[et_id]["learning_intelligences"].append(
                et["intelligences__code"]
            )

    educational_types_list = list(educational_types.values())

    return educational_types_list


def get_products():

    educational_types_raw = EducationalType.objects.select_related(
        "styles", "intelligences"
    ).values("id", "code", "name", "description", "styles__code", "intelligences__code")

    educational_types = defaultdict(lambda: {"styles": [], "intelligences": []})

    for et in educational_types_raw:
        et_id = et["id"]
        if "id" not in educational_types[et_id]:
            educational_types[et_id].update(
                {
                    "id": et_id,
                    "name": et["name"],
                    "description": et["description"],
                    "code": et["code"],
                }
            )
        if et["styles__code"] not in educational_types[et_id]["styles"]:
            educational_types[et_id]["styles"].append(et["styles__code"])
        if et["intelligences__code"] not in educational_types[et_id]["intelligences"]:
            educational_types[et_id]["intelligences"].append(et["intelligences__code"])

    educational_types_list = list(educational_types.values())

    return educational_types_list


def get_specific_products(product_name, class_object: Class = None):
    # Start with a queryset filtered by the product type code (case-insensitive)
    qs = (
        EducationalProduct.objects.select_related("type")
        .prefetch_related("styles", "intelligences")
        .filter(type__code__iexact=product_name)
    )

    # If a class_object is provided, check if there are any ClassProduct entries.
    # If so, filter the products to only those associated with the given class.
    if class_object:
        if ClassProduct.objects.filter(class_id=class_object.id).exists():
            qs = qs.filter(products__class_id=class_object.id).distinct()

    # Build the list of products with aggregated styles and intelligences
    products = []
    for product in qs:
        products.append(
            {
                "id": product.id,
                "name": product.name,
                "info": product.info,
                "link": product.link,
                "pos_rating": get_positive_total_rating(product.id),
                "neg_rating": get_negative_total_rating(product.id),
                "styles": list(
                    product.styles.values_list("code", flat=True)
                ),
                "intelligences": list(
                    product.intelligences.values_list("code", flat=True)
                ),
            }
        )
    return products


def get_specific_methodologies(product_name):

    # TODO Filter by the type code instead of going through all the products
    learning_methodologies_raw = LearningMethodology.objects.select_related(
        "type", "styles", "intelligences"
    ).values(
        "id",
        "name",
        "info",
        "link",
        "type__code",
        "styles__code",
        "intelligences__code",
    )

    learning_methodologies = defaultdict(lambda: {"styles": [], "intelligences": []})

    for ep in learning_methodologies_raw:
        if ep["type__code"].casefold() == product_name.casefold():
            if ep["name"] not in learning_methodologies:
                learning_methodologies[ep["name"]].update(
                    {
                        "id": ep["id"],
                        "name": ep["name"],
                        "info": ep["info"],
                        "link": ep["link"],
                        "pos_rating": get_positive_total_rating(ep["id"]),
                        "neg_rating": get_negative_total_rating(ep["id"]),
                    }
                )
            if ep["styles__code"] not in learning_methodologies[ep["name"]]["styles"]:
                learning_methodologies[ep["name"]]["styles"].append(ep["styles__code"])
            if (
                ep["intelligences__code"]
                not in learning_methodologies[ep["name"]]["intelligences"]
            ):
                learning_methodologies[ep["name"]]["intelligences"].append(
                    ep["intelligences__code"]
                )

    learning_methodologies_list = list(learning_methodologies.values())

    return learning_methodologies_list


def get_methodology_by_name(methodologies, methodology_name):
    for methodology in methodologies:
        if methodology["name"] == methodology_name:
            return methodology
    return None


def find_value_by_description2(objects, target_code):
    """
    Find a value in a dictionary by searching for a specific key and returning the corresponding value if found, otherwise return None.

    Parameters:
        objects (dict): A dictionary containing key-value pairs to search through.
        target_code (str): The key to search for in the dictionary.

    Returns:
        The value corresponding to the target_code if found, otherwise None.
    """
    for obj in objects:
        if obj == target_code:
            return objects[obj]
    return None


def add_score_to_methodology(methodology, score):
    """
    Add a score to a methodology.

    Parameters:
    methodology (dict): The methodology to which the score will be added.
    score (int): The score to be added to the methodology.

    Returns:
    dict: The methodology with the added score.
    """
    methodology["score"] = score
    return methodology
