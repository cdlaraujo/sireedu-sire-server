from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Institution,
    Program,
    Class,
    Student,
    Professor,
    EducationalType,
    EducationalProduct,
    LearningType,
    ProductRating,
    ProfessorRecommendation,
    StudentAnswer,
    FavoriteProduct,
    StudentAnswerLog,
    ClassProduct,
    Study,
    StudyOption,
    Question,
    Answer,
    EmailVerification,
    LearningMethodology,
)


# Inline models for related objects
class StudyOptionInline(admin.TabularInline):
    model = StudyOption
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class StudentInline(admin.TabularInline):
    model = Student
    extra = 0
    readonly_fields = ("user",)


class ClassProductInline(admin.TabularInline):
    model = ClassProduct
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ("acronym", "description", "options_count")
    search_fields = ("acronym", "description")
    inlines = [StudyOptionInline]

    def options_count(self, obj):
        return obj.options.count()

    options_count.short_description = "Number of options"


@admin.register(StudyOption)
class StudyOptionAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "study")
    list_filter = ("study",)
    search_fields = ("code", "description")
    autocomplete_fields = ["study"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("position", "text", "study", "study_option")
    list_filter = ("study", "study_option")
    search_fields = ("text",)
    ordering = ("study", "position")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("text", "value", "questions_count")
    search_fields = ("text",)
    filter_horizontal = ("questions",)

    def questions_count(self, obj):
        return obj.questions.count()

    questions_count.short_description = "Number of questions"


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "initials", "programs_count")
    search_fields = ("name", "initials")

    def programs_count(self, obj):
        return obj.programs.count()

    programs_count.short_description = "Number of programs"


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "classes_count")
    search_fields = ("name",)
    list_filter = ("institution",)

    def classes_count(self, obj):
        return obj.classes.count()

    classes_count.short_description = "Number of classes"


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "abbreviation",
        "description",
        "semester",
        "year",
        "program",
        "students_count",
    )
    search_fields = ("code", "abbreviation", "description")
    list_filter = ("program", "year", "semester")
    inlines = [StudentInline, ClassProductInline]

    def students_count(self, obj):
        return obj.students.count()

    students_count.short_description = "Number of students"


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "sclass", "key", "created_at", "is_valid")
    search_fields = ("user__email", "user__username")
    list_filter = ("created_at", "sclass")
    readonly_fields = ("key", "created_at")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user_full_name", "user_email", "sclass")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("sclass",)
    autocomplete_fields = ["user", "sclass"]

    def user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    user_full_name.short_description = "Name"

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ("user_full_name", "user_email", "get_classes")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    filter_horizontal = ("classes",)
    autocomplete_fields = ["user"]

    def user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    user_full_name.short_description = "Name"

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("student", "study", "question", "answer")
    list_filter = ("study",)
    search_fields = (
        "student__user__email",
        "student__user__first_name",
        "student__user__last_name",
    )
    autocomplete_fields = ["student", "question", "answer"]


@admin.register(StudentAnswerLog)
class StudentAnswerLogAdmin(admin.ModelAdmin):
    list_display = ("student", "study", "submit_datetime")
    list_filter = ("study", "submit_datetime")
    search_fields = ("student__user__email",)
    date_hierarchy = "submit_datetime"


@admin.register(EducationalType)
class EducationalTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "description", "products_count")
    search_fields = ("name", "code", "description")
    filter_horizontal = ("styles", "intelligences")

    def products_count(self, obj):
        return obj.products_type.count()

    products_count.short_description = "Number of products"


@admin.register(EducationalProduct)
class EducationalProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "educational_code",
        "type",
        "content_source",
        "short_description",
        "link_display",
    )
    search_fields = ("name", "educational_code", "info", "type__name")
    list_filter = ("type", "content_source", "activity_type", "media_format")
    filter_horizontal = ("styles", "intelligences")
    list_per_page = 20

    def short_description(self, obj):
        """Returns a shortened version of the product info field"""
        if obj.info:
            if len(obj.info) > 50:
                return f"{obj.info[:50]}..."
            return obj.info
        return "-"
    
    short_description.short_description = "Description"
    
    def link_display(self, obj):
        if obj.link:
            return format_html('<a href="{}" target="_blank">Open link</a>', obj.link)
        return "-"

    link_display.short_description = "Resource link"

    def get_search_results(self, request, queryset, search_term):
        """Custom search to improve searching across multiple fields"""
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        # If no results found and search term looks like a code, try a more direct match
        if not queryset.exists() and search_term:
            queryset |= self.model.objects.filter(
                educational_code__icontains=search_term
            )

        return queryset, use_distinct

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize display in foreign key dropdowns"""
        if db_field.name == "type":
            kwargs["queryset"] = EducationalType.objects.all().order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(LearningType)
class LearningTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "description")
    search_fields = ("name", "code", "description")
    filter_horizontal = ("styles", "intelligences")


@admin.register(LearningMethodology)
class LearningMethodologyAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "link_display")
    search_fields = ("name", "info")
    list_filter = ("type",)
    filter_horizontal = ("styles", "intelligences")

    def link_display(self, obj):
        if obj.link:
            return format_html('<a href="{}" target="_blank">Open link</a>', obj.link)
        return "-"

    link_display.short_description = "Resource link"


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ("student", "product", "rating_display")
    list_filter = ("rating",)
    search_fields = ("student__user__email", "product__name")
    autocomplete_fields = ["student", "product"]

    def rating_display(self, obj):
        if obj.rating == 1:
            return format_html('<span style="color: green;">✓ Positive</span>')
        return format_html('<span style="color: red;">✗ Negative</span>')

    rating_display.short_description = "Rating"


@admin.register(ProfessorRecommendation)
class ProfessorRecommendationAdmin(admin.ModelAdmin):
    list_display = ("product", "class_id")
    list_filter = ("class_id",)
    search_fields = ("product__name", "class_id__description")
    autocomplete_fields = ["product", "class_id"]


@admin.register(FavoriteProduct)
class FavoriteProductAdmin(admin.ModelAdmin):
    list_display = ("student", "product")
    list_filter = ("student",)
    search_fields = ("student__user__email", "product__name")
    autocomplete_fields = ["student", "product"]


@admin.register(ClassProduct)
class ClassProductAdmin(admin.ModelAdmin):
    list_display = ("class_id", "product_with_details")
    list_filter = ("class_id",)
    search_fields = (
        "class_id__description",
        "product__name",
        "product__educational_code",
    )
    autocomplete_fields = ["class_id", "product"]
    list_per_page = 20
    
    def product_with_details(self, obj):
        """Display comprehensive product information in the admin list view"""
        product = obj.product
        details = []
        
        # Add name and code
        if product.educational_code:
            details.append(f"<strong>{product.name}</strong> ({product.educational_code})")
        else:
            details.append(f"<strong>{product.name}</strong>")
        
        # Add type
        details.append(f"Type: {product.type.name}")
        
        # Add content source if available
        if product.content_source:
            details.append(f"Source: {product.content_source}")
            
        # Add activity type if available
        if product.activity_type:
            details.append(f"Activity: {product.activity_type}")
            
        # Add short description
        if product.info:
            desc = product.info[:40] + "..." if len(product.info) > 40 else product.info
            details.append(f"Info: {desc}")
            
        return format_html("<br>".join(details))

    product_with_details.short_description = "Product Details"


# Admin site customization
admin.site.site_header = "SIRE Administration"
admin.site.site_title = "SIRE Admin Portal"
admin.site.index_title = "Welcome to SIRE Admin Portal"
