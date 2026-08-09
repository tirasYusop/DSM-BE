from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = "page_size"  # optional but useful
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get("page") is None:
            return None
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page_size": self.page_size,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })