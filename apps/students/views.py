from rest_framework import viewsets


from .models import (Student,)
from .api.serializers import (StudentSerializer)

class StudentViewSet(viewsets.ModelViewSet):

    queryset = Student.objects.all()
    serializer_class = StudentSerializer