from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from datetime import timedelta
from django.utils import timezone

class Study(models.Model):
    acronym = models.CharField(unique=True, max_length=2)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class StudyOption(models.Model):
    code = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name='options')

    def __str__(self):
        return "%s: %s" % (self.study, self.description)

    class Meta:
       unique_together = ("study", "code")


class Question(models.Model):
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name='questions')
    study_option = models.ForeignKey(StudyOption, on_delete=models.PROTECT, related_name='questions')
    position = models.IntegerField()
    text = models.CharField(max_length=2000)

    def __str__(self):
        return "%s - %s" % (self.position, self.text)

    class Meta:
       unique_together = ("study", "study_option", "position")


class Answer(models.Model):
    value = models.IntegerField()
    text = models.CharField(max_length=100)
    questions = models.ManyToManyField(Question, related_name='answers')

    def __str__(self):
        return self.text

    class Meta:
       unique_together = ("value", "text")


class Institution(models.Model):
    name = models.CharField(max_length=300, unique=True)
    initials = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return "%s (%s)" % (self.name, self.initials)


class Program(models.Model):
    name = models.CharField(max_length=100)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name='programs')

    def __str__(self):
        return self.name

    class Meta:
       unique_together = ("name", "institution")


class Class(models.Model):
    code = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    semester = models.IntegerField()
    year = models.IntegerField()
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name='classes')

    def __str__(self):
        return self.description

    class Meta:
       unique_together = ("program", "code", "abbreviation", "year", "semester")


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sclass = models.ForeignKey(Class, on_delete=models.CASCADE)
    key = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email

    def is_valid(self):
        expiration_time = self.created_at + timedelta(hours=2)
        return timezone.now() < expiration_time


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    sclass = models.ForeignKey(Class, on_delete=models.PROTECT, related_name='students')

    def __str__(self):
        return "%s: %s %s, %s" % (self.user.email, self.user.first_name, self.user.last_name, self.sclass)


class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    classes = models.ManyToManyField(Class, related_name='professors')

    def __str__(self):
        return "%s: %s %s, %s" % (self.user.email, self.user.first_name, self.user.last_name, self.classes)

    def get_classes(self):
        return ", ".join([classe.description for classe in self.classes.all()])
        
    get_classes.short_description = "Turmas"


class StudentAnswer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='student_answers')
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name='student_answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='student_answers')
    answer = models.ForeignKey(Answer, on_delete=models.PROTECT, related_name='student_answers')

    def __str__(self):
        return "%s: (%i, %i, %i)" % (self.student.user.email, self.study.id, self.question.id, self.answer.id)

    class Meta:
       unique_together = ("student", "study", "question")

class StudentAnswerLog(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='student_answer_logs')
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name='student_answer_logs')
    submit_datetime = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        unique_together = ("student", "study")


class EducationalType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    styles = models.ManyToManyField(StudyOption, related_name="styles")
    intelligences = models.ManyToManyField(StudyOption, related_name="intelligences")

    def __str__(self):
        return self.name


class EducationalProduct(models.Model):
    STATUS_CHOICES = [
        ('APPROVED', 'Aprovado'),
        ('PENDING', 'Pendente'),
        ('REJECTED', 'Rejeitado')
    ]

    name = models.CharField(max_length=255)
    info = models.CharField(max_length=255)
    link = models.CharField(max_length=255)
    type = models.ForeignKey(
        EducationalType, on_delete=models.PROTECT, related_name="products_type"
    )
    styles = models.ManyToManyField(StudyOption, related_name="styles_products")
    intelligences = models.ManyToManyField(
        StudyOption, related_name="intelligences_products"
    )
    content_source = models.CharField(max_length=255, default='')
    activity_type = models.CharField(max_length=255, default='')
    media_format = models.CharField(max_length=255, default='')
    educational_code = models.CharField(max_length=255, default='')

    # Suggestions Fields
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='APPROVED'
    )
    suggested_by = models.ForeignKey(
        Professor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="suggested_products"
    )
    # NEW: Identify which class this was suggested for
    suggested_for_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_suggestions"
    )
    rejection_reason = models.TextField(null=True, blank=True)
    
    def __str__(self):
        if self.educational_code:
            return f"{self.name} ({self.educational_code}) - {self.type.name}"
        return f"{self.name} - {self.type.name}"
    
class LearningType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    styles = models.ManyToManyField(StudyOption, related_name="learning_styles")
    intelligences = models.ManyToManyField(StudyOption, related_name="learning_intelligences")

    def __str__(self):
        return self.name
    
class LearningMethodology(models.Model):
    name = models.CharField(max_length=255)
    info = models.CharField(max_length=255)
    link = models.CharField(max_length=255)
    type = models.ForeignKey(
        LearningType, on_delete=models.PROTECT, related_name="methodologies_type"
    )
    styles = models.ManyToManyField(StudyOption, related_name="styles_methodologies")
    intelligences = models.ManyToManyField(
        StudyOption, related_name="intelligences_methodologies"
    )

    def __str__(self):
        return self.name


class ProductRating(models.Model):
    POSITIVE = 1
    NEGATIVE = 0
    RATING_CHOICES = [
        (POSITIVE, "Positive"),
        (NEGATIVE, "Negative"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="product_ratings"
    )
    product = models.ForeignKey(
        EducationalProduct, on_delete=models.PROTECT, related_name="product_ratings"
    )
    rating = models.IntegerField(choices=RATING_CHOICES)

    def __str__(self):
        return "%s: %s (%s)" % (
            self.student.user.email,
            self.product.name,
            "Positive" if self.rating == self.POSITIVE else "Negative",
        )

    class Meta:
        unique_together = ("student", "product")

# Create a class to store the professor recommendation to the student
class ProfessorRecommendation(models.Model):   
    product = models.ForeignKey(
        EducationalProduct, on_delete=models.PROTECT, related_name="product_recommendations"
    )
    class_id = models.ForeignKey(
        Class, on_delete=models.PROTECT, related_name="class_recommendations"
    )

    def __str__(self):
        return "%s: %s" % (
            self.product.name,
            self.class_id, 
        )

    class Meta:
        unique_together = ("product", "class_id")

class FavoriteProduct(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="favorite_students"
    )
    product = models.ForeignKey(
        EducationalProduct, on_delete=models.PROTECT, related_name="favorite_products"
    )

    def __str__(self):
        return "%s: %s" % (
            self.student.user.email,
            self.product.name,
        )

    class Meta:
        unique_together = ("student", "product")
        

# Create a new model that will select educational products for each class
class ClassProduct(models.Model):
    class_id = models.ForeignKey(
        Class, on_delete=models.PROTECT, related_name="class_products"
    )
    product = models.ForeignKey(
        EducationalProduct, on_delete=models.PROTECT, related_name="products"
    )

    def __str__(self):
        return "%s: %s" % (
            self.class_id,
            self.product.name,
        )

    class Meta:
        unique_together = ("class_id", "product")