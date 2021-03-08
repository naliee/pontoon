import graphene
from graphene_django import DjangoObjectType
from graphene_django.debug import DjangoDebug
# Graphene: 파이썬에서 GraphQL API를 구축하기 위해 사용하는 라이브러리

# pontoon/api 폴더 내 util.py의 get_fields(info) 모듈 사용 
from pontoon.api.util import get_fields
# 필드명 구성 목록을 반환하는 모듈

# pontoon/base 폴더 내 models.py 에서 Locale, Project, ProjectLocale 모듈 사용 - pontoon사이트의 locale,Project,projectLocale 데이터 구조 정의된 파일
from pontoon.base.models import (
    Locale as LocaleModel,
    Project as ProjectModel,
    ProjectLocale as ProjectLocaleModel,
)

# pontoon/tags 폴더 내 models.py 에서 Tag 사용 - pontoon사이트의 tag정보 데이터 구조 정의된 파일
from pontoon.tags.models import Tag as TagModel


class Stats:
    missing_strings = graphene.Int()    # 비 분수, 부호 있는 정수 값(부호 있는 32비트 정수)
    complete = graphene.Boolean()       # 참/거짓


# 클라이언트가 서비스를 통해 쿼리할 가능성이 있는 모든 데이터 설명

# graphene에서 import한 DjangoObjectType
class Tag(DjangoObjectType):    
    class Meta:
        convert_choices_to_enum = False
        model = TagModel
        fields = (
            "slug",
            "name",
            "priority",
        )


# Stats: mmissing_strings, complete가 정의된 (상단의) 클래스
class ProjectLocale(DjangoObjectType, Stats):
    # class Meta: Inner class로 사용하여 상위 클래스에게 meta data(데이터를 위한 데이터. 다른 데이터를 설명해주는 데이터.) 제공
    class Meta:
        model = ProjectLocaleModel
        fields = (
            "project",
            "locale",
            "total_strings",
            "approved_strings",
            "fuzzy_strings",
            "strings_with_errors",
            "strings_with_warnings",
            "unreviewed_strings",
        )


class Project(DjangoObjectType, Stats):
    class Meta:
        convert_choices_to_enum = False
        model = ProjectModel
        fields = (
            "name",
            "slug",
            "disabled",
            "sync_disabled",
            "pretranslation_enabled",
            "visibility",
            "system_project",
            "info",
            "deadline",
            "priority",
            "contact",
            "total_strings",
            "approved_strings",
            "fuzzy_strings",
            "strings_with_errors",
            "strings_with_warnings",
            "unreviewed_strings",
        )

    localizations = graphene.List(ProjectLocale)    #위에 정의된 ProjectLocale을 리스트로 받아 localizations에 저장
    tags = graphene.List(Tag)                       #위에 정의된 Tag를 리스트로 받아 tags에 저장

    def resolve_localizations(obj, info):
        return obj.project_locale.all()

    def resolve_tags(obj, info):
        return obj.tag_set.all()


class Locale(DjangoObjectType, Stats):
    class Meta:
        model = LocaleModel
        fields = (
            "name",
            "code",
            "direction",
            "cldr_plurals",
            "plural_rule",
            "script",
            "population",
            "total_strings",
            "approved_strings",
            "fuzzy_strings",
            "strings_with_errors",
            "strings_with_warnings",
            "unreviewed_strings",
            "google_translate_code",
            "ms_translator_code",
            "systran_translate_code",
            "ms_terminology_code",
        )

    localizations = graphene.List(
        ProjectLocale,
        include_disabled=graphene.Boolean(False),
        include_system=graphene.Boolean(False),
    )

    def resolve_localizations(obj, info, include_disabled, include_system):
        projects = obj.project_locale.visible_for(info.context.user)

        records = projects.filter(
            project__disabled=False, project__system_project=False
        )

        if include_disabled:
            records |= projects.filter(project__disabled=True)

        if include_system:
            records |= projects.filter(project__system_project=True)

        return records.distinct()

# Query는 데이터를 조회하는 데에 사용되며, 각 필드는 데이터의 집합
class Query(graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name="__debug")

    # include_disabled=True will return both active and disabled projects.
    # include_system=True will return both system and non-system projects.
    # project(위에서 ProjectModel(models.py의 project)로 생성한 클래스)를 graphene.List로 불러와 projects에 담음 
    projects = graphene.List(
        Project,
        include_disabled=graphene.Boolean(False),
        include_system=graphene.Boolean(False),
    )
    project = graphene.Field(Project, slug=graphene.String()) # project는 Project의 필드들과 slug

    locales = graphene.List(Locale) # graphene.List는 여러 개의 결과를(리스트로) 반환. (locales 변수에 locale의 리스트 저장)
    locale = graphene.Field(Locale, code=graphene.String()) # graphene.Field는 한 개의 결과를 반환. locale은 Locale의 필드들과 code

    def resolve_projects(obj, info, include_disabled, include_system):  #obj, info, disabled여부(프로젝트 실행 중지 여부), 비활성 시스템 여부
        fields = get_fields(info)   #api/util.py의 get_fields 메서드: 필드명 구성 목록을 반환하는 메서드
    
        # ProjectModel.objects = ProjectQuerySet.as_manager()
        # ProjectModel.objects.visible_for(info.context.user) = ProjectQuerySet.visible_for(self, user) 메서드 실행
        projects = ProjectModel.objects.visible_for(info.context.user)
        records = projects.filter(disabled=False, system_project=False)

        if include_disabled:
            # |= : a|=b일 경우 a와 b의 비트를 or연산한 후 결과를 a에 할당
            records |= projects.filter(disabled=True) # include_disabled가 True일 경우 records도 True

        if include_system:
            records |= projects.filter(system_project=True)

        if "projects.localizations" in fields:
            records = records.prefetch_related("project_locale__locale")

        if "projects.localizations.locale.localizations" in fields:
            raise Exception("Cyclic queries are forbidden")

        return records.distinct()
    
    
    def resolve_project(obj, info, slug):
        qs = ProjectModel.objects.visible_for(info.context.user)
        fields = get_fields(info)

        if "project.localizations" in fields:
            qs = qs.prefetch_related("project_locale__locale")

        if "project.tags" in fields:
            qs = qs.prefetch_related("tag_set")

        if "project.localizations.locale.localizations" in fields:
            raise Exception("Cyclic queries are forbidden")

        return qs.get(slug=slug)
    
    
    # DB에서 모든 LocaleModel 목록 조회
    def resolve_locales(obj, info):
        qs = LocaleModel.objects
        fields = get_fields(info)

        if "locales.localizations" in fields:
            qs = qs.prefetch_related("project_locale__project")

        if "locales.localizations.project.localizations" in fields:
            raise Exception("Cyclic queries are forbidden")

        return qs.all()

    def resolve_locale(obj, info, code):
        qs = LocaleModel.objects
        fields = get_fields(info)

        if "locale.localizations" in fields:
            qs = qs.prefetch_related("project_locale__project")

        if "locale.localizations.project.localizations" in fields:
            raise Exception("Cyclic queries are forbidden")

        return qs.get(code=code)

# schema 생성(GraphQL의 전체 데이터 구조 의미. ObjectType, Query, Mutation 등 포함)
schema = graphene.Schema(query=Query)
