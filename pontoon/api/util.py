from graphql.language.ast import FragmentSpread


def get_fields(info):
    """Return a list of composite field names.

    Parse a GraphQL query into a flat list of all paths and leaves.

    For example the following query:

        {
          projects {
            name
            slug
            ...stats
          }
        }

        fragment stats on Project {
          totalStrings
          missingStrings
        }

    Will result in an array:

        [
            'projects',
            'projects.name',
            'projects.slug',
            'projects.totalStrings',
            'projects.missingStrings'
        ]
    """

    def iterate_field_names(prefix, field):
        name = field.name.value
        
        # isinstance(a, A): a가 A의 인스턴스인지 Boolean
        # field가 FragmentSpread(graphql.language.ast에서 임포트) 타입일 경우
        if isinstance(field, FragmentSpread):
            results = []
            new_prefix = prefix
            sub_selection = info.fragments[name].selection_set.selections
            # 새로운 필드 생성(?)
        else:
            # 인스턴스가 아닐 경우 prefix("")+field name으로 리스트 생성
            results = [prefix + name]
            new_prefix = prefix + name + "."
            if field.selection_set:
                sub_selection = field.selection_set.selections
            else:
                sub_selection = []

        for sub_field in sub_selection:
            results += iterate_field_names(new_prefix, sub_field)

        return results
    
    # info(get_field 호출 시 주어지는 인자. resolve 메서드에 전달된 유용한 정보context 등이 있음.)
    # 이 info에서 field_asts를 꺼내 사용 - info의 field_asts에 있는 field_ast를 하나씩 꺼내 iterate_field_names(prefix, field_ast)-필드 하나씩 꺼내 리스트로 저장하는 메서드- 메서드 실행
    results = []
    for field_ast in info.field_asts:
        results.extend(iterate_field_names("", field_ast))

    return results
