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
    If class_id is provided, it checks if that class has specific products assigned.
    - If YES: Returns ONLY the types of those assigned products.
    - If NO: Returns ALL product types (default behavior).
    """
    educational_types_raw = EducationalType.objects.select_related(
        "styles", "intelligences"
    ).values("id", "code", "name", "description", "styles__code", "intelligences__code")

    # --- FILTERING LOGIC ---
    allowed_product_type_ids = None
    if class_id:
        # Check if there are any specific links for this class
        linked_products = ClassProduct.objects.filter(class_id=class_id)
        if linked_products.exists():
            allowed_product_type_ids = linked_products.values_list('product__type__id', flat=True)

    educational_types = defaultdict(lambda: {"styles": [], "intelligences": []})

    for et in educational_types_raw:
        et_id = et["id"]

        # Apply Filter if it exists
        if allowed_product_type_ids is not None and et_id not in allowed_product_type_ids:
            continue

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
    Retrieves specific products of a given type (e.g. APPS).
    
    EXCLUSIVE FILTERING LOGIC:
    1. If a Class is provided...
    2. And that Class has links specifically for this product type (e.g. they linked 'Khan Academy' in 'APPS')...
    3. Then return ONLY those linked products.
    4. Otherwise (no links for this type), return the defaults.
    """
    qs = (
        EducationalProduct.objects.select_related("type")
        .prefetch_related("styles", "intelligences")
        .filter(type__code__iexact=product_name)
    )

    # --- FILTERING LOGIC ---
    if class_object:
        # Check if there are specific links for this class AND this product type
        linked_ids = list(ClassProduct.objects.filter(
            class_id=class_object.id,
            product__type__code__iexact=product_name 
        ).values_list('product_id', flat=True))

        if linked_ids:
            # EXCLUSIVE MODE: The professor curated this list. Show ONLY these.
            qs = qs.filter(id__in=linked_ids)
        # Else: No specific links found for 'APPS' in this class? 
        # Show all 'APPS' (standard behavior).

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