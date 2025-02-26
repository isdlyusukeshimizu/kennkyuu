from azure.search.documents.indexes.models import (
  HnswAlgorithmConfiguration,
  SearchableField,
  SearchField,
  SearchFieldDataType,
  SearchIndex,
  SemanticConfiguration,
  SemanticField,
  SemanticPrioritizedFields,
  SemanticSearch,
  SimpleField,
  VectorSearch,
  VectorSearchProfile,
)


def template_index(index_name):
  fields = [
    SimpleField(name="Index", type=SearchFieldDataType.String, key=True),
    SimpleField(name="URL", type=SearchFieldDataType.String),
    SearchableField(
      name="Title",
      type=SearchFieldDataType.String,
      retrievable=True,
      analyzer="ja.microsoft",
    ),
    SearchableField(
      name="Content",
      type=SearchFieldDataType.String,
      retrievable=True,
      analyzer="ja.microsoft",
    ),
    SearchableField(
      name="Category",
      type=SearchFieldDataType.String,
      filterable=True,
      retrievable=True,
    ),
    SearchableField(
      name="Instructions",
      type=SearchFieldDataType.String,
      retrievable=True,
      analyzer="ja.microsoft",
    ),
    SearchField(
      name="titleVector",
      type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
      searchable=True,
      vector_search_dimensions=1536,
      vector_search_profile_name="hnsw-profile",
    ),
    SearchField(
      name="contentVector",
      type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
      searchable=True,
      vector_search_dimensions=1536,
      vector_search_profile_name="hnsw-profile",
    ),
  ]

  vector_search_settings = VectorSearch(
    algorithms=[
      HnswAlgorithmConfiguration(
        name="vector-search-algorithm-config",
        kind="hnsw",
      )
    ],
    profiles=[
      VectorSearchProfile(
        name="hnsw-profile",
        algorithm_configuration_name="vector-search-algorithm-config",
      )
    ],
  )

  semantic_config = SemanticConfiguration(
    name="semantic-search-config",
    prioritized_fields=SemanticPrioritizedFields(
      title_field=SemanticField(field_name="Title"),
      keywords_fields=[SemanticField(field_name="Title")],
      content_fields=[SemanticField(field_name="Content")],
    ),
  )

  semantic_search_settings = SemanticSearch(configurations=[semantic_config])

  search_index = SearchIndex(
    name=index_name,
    fields=fields,
    vector_search=vector_search_settings,
    semantic_search=semantic_search_settings,
  )

  return search_index
