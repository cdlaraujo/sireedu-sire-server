from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from sisen.survey.permissions import IsProfessor
from rest_framework.permissions import IsAuthenticated
import sisen.survey.models as models
from sisen.survey.views.main import get_object_or_not_found
from sisen.survey.views.student import study_answered
import sisen.survey.businesses as business
from rest_framework.response import Response
from sisen.survey.businesses import LEARNING_STYLES_ID, INTELLIGENCES_ID
from pandas import DataFrame


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessor])
def export_survey_csv(request):
    df = create_csv(save=False)
    response = Response(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="data.csv"'
    df.to_csv(path_or_buf=response, index=False)
    return response


def create_csv(save=False):
    exporter = SurveyDataExporter()
    for student in models.Student.objects.all():
        exporter.add_student(student)
    df = exporter.build_dataframe()

    if save:
        df.to_csv("data.csv", index=False)

    return df


class SurveyDataExporter:
    def __init__(self):
        self.data = {
            "Aluno": [],
            "Ano": [],
            "Turma": [],
            "Ativo (%)": [],
            "Reflexivo (%)": [],
            "Teorico (%)": [],
            "Pragmatico (%)": [],
            "Cinestesico Corporal (%)": [],
            "Interpessoal (%)": [],
            "Intrapessoal (%)": [],
            "Logica-matematica (%)": [],
            "Naturalista (%)": [],
            "Ritmica Musical (%)": [],
            "Verbal Linguistica (%)": [],
            "Visual Espacial (%)": [],
            "1ª EA mais aflorada": [],
            "2ª EA mais aflorada": [],
            "3ª EA mais aflorada": [],
            "1ª IM mais aflorada": [],
            "2ª IM mais aflorada": [],
            "3ª IM mais aflorada": [],
        }

    def _populate_learning_style_scores(self, student):
        study = get_object_or_not_found(
            models.Study,
            LEARNING_STYLES_ID,
            "O estudo solicitado não existe (ID=%i)" % LEARNING_STYLES_ID,
        )
        scores = {}
        if study_answered(student, study):
            scores = {
                obj.code: obj.value
                for obj in business.process_answer(study, student).study_option_scores
            }
        else:
            scores = {"ATIVO": 0, "REFLEXIVO": 0, "TEORICO": 0, "PRAGMATICO": 0}

        self.data["Ativo (%)"].append(scores["ATIVO"] * 100)
        self.data["Reflexivo (%)"].append(scores["REFLEXIVO"] * 100)
        self.data["Teorico (%)"].append(scores["TEORICO"] * 100)
        self.data["Pragmatico (%)"].append(scores["PRAGMATICO"] * 100)

        learning_styles = sorted(scores, key=scores.get, reverse=True)
        self.data["1ª EA mais aflorada"].append(learning_styles[0])
        self.data["2ª EA mais aflorada"].append(learning_styles[1])
        self.data["3ª EA mais aflorada"].append(learning_styles[2])

    def _populate_intelligence_scores(self, student):
        study = get_object_or_not_found(
            models.Study,
            INTELLIGENCES_ID,
            "O estudo solicitado não existe (ID=%i)" % INTELLIGENCES_ID,
        )
        scores = {}
        if study_answered(student, study):
            scores = {
                obj.code: obj.value
                for obj in business.process_answer(study, student).study_option_scores
            }
        else:
            default_keys = [
                "LOGICA_MATEMATICA",
                "NATURALISTA",
                "RITMICA_MUSICAL",
                "VERBAL_LINGUISTICA",
                "VISUAL_ESPACIAL",
                "INTERPESSOAL",
                "INTRAPESSOAL",
                "CINESTESICA_CORPORAL",
            ]
            scores = {k: 0 for k in default_keys}

        self.data["Logica-matematica (%)"].append(scores["LOGICA_MATEMATICA"] * 100)
        self.data["Naturalista (%)"].append(scores["NATURALISTA"] * 100)
        self.data["Ritmica Musical (%)"].append(scores["RITMICA_MUSICAL"] * 100)
        self.data["Verbal Linguistica (%)"].append(scores["VERBAL_LINGUISTICA"] * 100)
        self.data["Visual Espacial (%)"].append(scores["VISUAL_ESPACIAL"] * 100)
        self.data["Interpessoal (%)"].append(scores["INTERPESSOAL"] * 100)
        self.data["Intrapessoal (%)"].append(scores["INTRAPESSOAL"] * 100)
        self.data["Cinestesico Corporal (%)"].append(
            scores["CINESTESICA_CORPORAL"] * 100
        )

        intelligences = sorted(scores, key=scores.get, reverse=True)
        self.data["1ª IM mais aflorada"].append(intelligences[0])
        self.data["2ª IM mais aflorada"].append(intelligences[1])
        self.data["3ª IM mais aflorada"].append(intelligences[2])

    def add_student(self, student):
        self.data["Aluno"].append(student.user.get_full_name())
        self.data["Ano"].append(student.sclass.year)
        self.data["Turma"].append(student.sclass.description)
        self._populate_learning_style_scores(student)
        self._populate_intelligence_scores(student)

    def build_dataframe(self):
        return DataFrame(self.data)


if __name__ == "__main__":
    create_csv(save=True)
