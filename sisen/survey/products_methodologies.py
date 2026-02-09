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
    div = norm(a) * norm(b)
    if div == 0:
        return 0
    return np.dot(a, b) / div


def sort_products_by_similarity(specific_products, reference_styles):
    all_styles_and_intelligences = get_all_possible_styles_and_intelligences()

    user_arr = np.array(
        [
            reference_styles[style_or_intelligence]
            for style_or_intelligence in all_styles_and_intelligences
        ]
    )

    for product in specific_products:
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


def get_products_sorted_by_similarity_score(recommendation, products_list):
    sorted_products = sort_products_by_similarity(products_list, recommendation)
    return sorted_products


def get_specific_methodologies_by_scores(recommendation, methodology_name):
    sorted_specific_products = sort_methodologies_by_similarity(
        get_specific_methodologies(methodology_name), recommendation
    )
    return sorted_specific_products


def get_methodologies():
    educational_types_raw = LearningType.objects.select_related(
        "learning_styles", "learning_intelligences"
    ).values(
        "id", "code", "name", "description", "styles__code", "intelligences__code"
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


def get_products(class_id=None):
    """
    Retrieves educational products (Types).
    Returns ALL product types (Apps, Books, etc) regardless of class configuration.
    Filtering of content happens in get_specific_products.
    """
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
    """
    Retrieves specific products of a given type (e.g. APPS) with Exclusivity Logic.
    
    1. If the class has specific links for this category:
       - Show ONLY those linked products (Curated View).
       
    2. If the class has NO links for this category:
       - Show "Generic" products.
       - EXCLUDE any product that is linked to ANY other class.
       - This ensures custom products for Class A do not leak into Class B.

    3. **IMPORTANT**: Only return products with status='APPROVED'.
    """
    qs = (
        EducationalProduct.objects.select_related("type")
        .prefetch_related("styles", "intelligences")
        .filter(type__code__iexact=product_name)
        .filter(status='APPROVED') # Added Status Filter
    )

    is_curated_view = False

    if class_object:
        # Check if there are specific links for THIS class and THIS product type
        linked_ids = list(ClassProduct.objects.filter(
            class_id=class_object.id,
            product__type__code__iexact=product_name,
            product__status='APPROVED' # Ensure only approved products are considered
        ).values_list('product_id', flat=True))

        if linked_ids:
            # EXCLUSIVE CURATED MODE: The professor curated this list. Show ONLY these.
            qs = qs.filter(id__in=linked_ids)
            is_curated_view = True

    # DEFAULT / GENERIC MODE
    if not is_curated_view:
        # If we are not in a curated view (either no class provided or no links for this class),
        # we must ensure we don't show "Private" products belonging to other classes.
        
        # Get IDs of ALL products that are linked to ANY class in the system
        all_private_linked_ids = ClassProduct.objects.values_list('product_id', flat=True)
        
        # Exclude them. We only want "Public/Generic" products here.
        qs = qs.exclude(id__in=all_private_linked_ids)

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
    learning_methodologies_raw = LearningMethodology.objects.select_related(
        "type", "styles", "intelligences"
    ).values(
        "id", "name", "info", "link", "type__code", "styles__code", "intelligences__code"
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
    for obj in objects:
        if obj == target_code:
            return objects[obj]
    return None


def add_score_to_methodology(methodology, score):
    methodology["score"] = score
    return methodology