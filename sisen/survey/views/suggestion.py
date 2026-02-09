from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from sisen.survey.permissions import IsProfessor, IsRevisor
from sisen.survey.models import EducationalProduct, EducationalType, StudyOption, Class, ClassProduct
from sisen.survey.serializers import EducationalProductSerializer, EducationalTypeSerializer
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

@api_view(['POST'])
@permission_classes((IsAuthenticated, IsProfessor))
@transaction.atomic
def suggest_product(request):
    data = request.data
    
    try:
        product_type = EducationalType.objects.get(id=data.get('type_id'))
        
        # Get class if provided
        class_id = data.get('class_id')
        suggested_class = None
        if class_id:
            try:
                suggested_class = Class.objects.get(id=class_id)
            except Class.DoesNotExist:
                pass

        # Create unique code based on name if not provided
        base_code = data.get('name').upper().replace(' ', '-')[:20]
        educational_code = f"SUGGESTION-{base_code}"
        
        product = EducationalProduct.objects.create(
            name=data.get('name'),
            link=data.get('link'),
            info=data.get('description', ''),
            type=product_type,
            status='PENDING',
            suggested_by=request.user.professor,
            suggested_for_class=suggested_class,
            educational_code=educational_code
        )
        
        # Add Styles
        if 'styles' in data and data['styles']:
            styles = StudyOption.objects.filter(code__in=data['styles'])
            product.styles.set(styles)
            
        # Add Intelligences
        if 'intelligences' in data and data['intelligences']:
            intelligences = StudyOption.objects.filter(code__in=data['intelligences'])
            product.intelligences.set(intelligences)
            
        product.save()
        
        return Response({"message": "Sugestão enviada para análise!"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsRevisor))
def get_pending_products(request):
    products = EducationalProduct.objects.filter(status='PENDING').order_by('-id')
    serializer = EducationalProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes((IsAuthenticated, IsRevisor))
@transaction.atomic
def review_product(request, product_id):
    try:
        product = EducationalProduct.objects.get(id=product_id)
        action = request.data.get('action')
        
        if action == 'APPROVE':
            product.status = 'APPROVED'
            product.rejection_reason = None
            
            # --- Apply Edits ---
            if 'name' in request.data: product.name = request.data['name']
            if 'link' in request.data: product.link = request.data['link']
            if 'description' in request.data: product.info = request.data['description']
            if 'type_id' in request.data: 
                product.type = EducationalType.objects.get(id=request.data['type_id'])
            
            # --- Update Tags ---
            if 'styles' in request.data:
                styles = StudyOption.objects.filter(code__in=request.data['styles'])
                product.styles.set(styles)
            if 'intelligences' in request.data:
                intelligences = StudyOption.objects.filter(code__in=request.data['intelligences'])
                product.intelligences.set(intelligences)

            # --- Handle Scope (Global vs Restricted) ---
            # If restrict_to_class is TRUE, we create a ClassProduct link.
            # If FALSE, we allow it to be global (by NOT creating a link and relying on exclude logic in get_specific_products)
            
            restrict_to_class = request.data.get('restrict_to_class', False)
            
            if restrict_to_class and product.suggested_for_class:
                # Create the Exclusive Link
                ClassProduct.objects.get_or_create(
                    class_id=product.suggested_for_class,
                    product=product
                )
            # If restrict_to_class is False, we do nothing. The product is APPROVED and has no ClassProduct link,
            # so it will show up for everyone in the "Generic" list.
            
        elif action == 'REJECT':
            product.status = 'REJECTED'
            product.rejection_reason = request.data.get('reason', '')
        else:
            return Response({"detail": "Ação inválida. Use APPROVE ou REJECT."}, status=status.HTTP_400_BAD_REQUEST)
            
        product.save()
        return Response({"message": f"Produto {action.lower()} com sucesso."})
        
    except EducationalProduct.DoesNotExist:
        return Response({"detail": "Produto não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes((IsAuthenticated, IsProfessor | IsRevisor))
def get_educational_types(request):
    types = EducationalType.objects.all().order_by('name')
    serializer = EducationalTypeSerializer(types, many=True)
    return Response(serializer.data)