from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import redirect, get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

import sisen.survey.businesses as business
import sisen.survey.models as models
from sisen.survey.dto import Link, AvailableStudy, SurveyAnswering
from sisen.survey.exceptions import Conflict, NotFound
from sisen.survey.permissions import IsStudent
from sisen.survey.serializers import AvailableStudySerializer, SurveyAnsweringSerializer, StudentAnswerSerializer, \
    StudyWithMessageAndStudentOptionScoreSerializer
from sisen.survey.serializers import UserSerializer, StudentSerializer
from sisen.survey.views.main import get_object_or_not_found
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from decouple import config


@api_view(['POST'])
@transaction.atomic
@permission_classes([])
@authentication_classes([])
def register_student(request, format=None):
    try:
        class_id = request.data.pop('class')
    except KeyError:
        raise NotFound('O id da turma do aluno sendo cadastrado é obrigatório.')
    
    email = request.data.get('email', None)
    if email and User.objects.filter(email=email).exists():
        return Response({'email': ['Este e-mail já está em uso.']}, status=status.HTTP_400_BAD_REQUEST)

    sclass = get_object_or_not_found(models.Class, class_id, 'A turma enviada não existe (ID=%s)' % class_id)
    serializer = UserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    verification = models.EmailVerification.objects.create(user=user, sclass=sclass)

    context = {
        'current_user': user,
        'verify_email_url': f"{settings.CLIENT_EMAIL_VERIFICATION_URL}/?token={verification.key}",
        # 'invalidate_token_url': f"http://127.0.0.1:8000/api/v1/survey/student-view/email-verification/invalidate-token/{verification.key}",
        'invalidate_token_url': f"https://sire-api-96a0e5dd3acc.herokuapp.com/api/v1/survey/student-view/email-verification/invalidate-token/{verification.key}",
    }

    email_html_message = render_to_string('email/verify_email.html', context)
    email_plaintext_message = render_to_string('email/verify_email.txt', context)

    message = Mail(
        from_email='sireedu.tec@gmail.com',
        to_emails=email,
        subject='Sireedu - Registro de estudante',
        plain_text_content=email_plaintext_message,
        html_content=email_html_message)

    try:
        sg = SendGridAPIClient(config('SENDGRID_API_KEY'))
        response = sg.send(message)
    except Exception as e:
        print("Ocorreu um erro ao tentar enviar"
              " e-mail de registro"
              " para o usuário %s" % email)
        print(e)

    return Response({'detail': 'Usuário registrado com sucesso. Verifique seu e-email para concluir o registro.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@transaction.atomic
@permission_classes([])
@authentication_classes([])
def verify_email(request, token, format=None):
    try:
        verification = get_object_or_404(models.EmailVerification, key=token)
        
        if verification.is_valid():

            student_group = Group.objects.get(name='Student')
            student_group.user_set.add(verification.user)

            student = models.Student(user=verification.user, sclass=verification.sclass)
            student.save()

            verification.delete()

            return Response({'message': 'E-mail verificado com sucesso!'}, status=status.HTTP_200_OK)
        
        else:
            User.objects.get(id=verification.user.id).delete()
            return Response({'error': 'Token inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)

    except models.EmailVerification.DoesNotExist:
        return Response({'error': 'Token não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([])
def delete_verification_token(request, token, format=None):
    try:
        verification = get_object_or_404(models.EmailVerification, key=token)
        User.objects.get(id=verification.user.id).delete()
        return Response("Token invalidado com sucesso.")

    except models.EmailVerification.DoesNotExist:
        return Response({'error': 'Token não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsStudent))
def student_home(request, format=None):
    student = request.user.student
    available_studies = models.Study.objects.all()
    answered_studies = set(map(lambda e: e.study, models.StudentAnswer.objects.filter(student=student)))
    studies = []
    for study in available_studies:
        study_dto = AvailableStudy(study, [])
        study_dto.links.append(Link('self', reverse('student_home', request=request)))
        if study in answered_studies:
            study_dto.links.append(Link('result', reverse('survey_report', args=[study.id], request=request)))
        else:
            study_dto.links.append(Link('answer', reverse('answer', args=[study.id], request=request)))
        studies.append(study_dto)
    return Response(AvailableStudySerializer(studies, many=True, context={'student': student}).data)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsStudent))
def answer(request, study_id, format=None):
    study = get_object_or_not_found(models.Study, study_id,
        'O estudo solicitado não existe (ID=%i)' % study_id)
    student = request.user.student
    study_not_answered_or_error(student, study)

    survey_answering = SurveyAnswering(study.description, study.questions.all(), [])
    survey_answering.links.append(Link('self', reverse('answer', args=[study_id], request=request)))
    survey_answering.links.append(Link('home', reverse('student_home', request=request)))
    survey_answering.links.append(Link('process', reverse('process_answer', args=[study_id], request=request), 'POST'))
    return Response(SurveyAnsweringSerializer(survey_answering).data)


@api_view(['POST'])
@transaction.atomic
@permission_classes((IsAuthenticated, IsStudent))
def process_answer(request, study_id, format=None):
    study = get_object_or_not_found(models.Study, study_id,
        'O estudo solicitado não existe (ID=%i)' % study_id)
    student = request.user.student
    study_not_answered_or_error(student, study)

    answers = list(filter(lambda e: e != None, request.data.get('answers', [])))
    validate_answers(study, answers)
    for answer in answers:
        answer.update({ 'study': study.id, 'student': student.id })
    serializer = StudentAnswerSerializer(data=answers, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    models.StudentAnswerLog(student=student, study=study).save()
    return redirect('survey_report', study_id=study.id)


@api_view(['GET'])
@permission_classes((IsAuthenticated, IsStudent))
def survey_report(request, study_id, format=None):
    study = get_object_or_not_found(models.Study, study_id,
        'O estudo solicitado não existe (ID=%i)' % study_id)
    student = request.user.student
    study_answered_or_error(student, study)

    study_option_scores = business.process_answer(study, student)
    study_option_scores.links.append(Link('self', reverse('survey_report', args=[study.id], request=request)))
    study_option_scores.links.append(Link('home', reverse('student_home', request=request)))
    return Response(StudyWithMessageAndStudentOptionScoreSerializer(study_option_scores).data)


def study_not_answered_or_error(student, study):
    if models.StudentAnswer.objects.filter(student=student, study=study).exists():
        raise Conflict('O estudo \'%s\' já foi respondido' % study.description)


def study_answered_or_error(student, study):
    if not models.StudentAnswer.objects.filter(student=student, study=study).exists():
        raise Conflict('O estudo \'%s\' ainda não foi respondido' % study.description)


def study_answered(student, study):
    return models.StudentAnswer.objects.filter(student=student, study=study).exists()


def validate_answers(study, answers):
    # TODO: Should also validate the answers of each question?
    expected = set(map(lambda s: s.id, study.questions.all()))
    received = set(map(lambda s: s.get('question'), answers))
    if len(expected - received) != 0:
        raise Conflict('Todas as questões do estudo devem ser respondidas')
