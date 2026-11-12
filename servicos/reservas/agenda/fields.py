from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import Func


class TimestampLocal(models.DateTimeField):
    """Timestamp sem timezone, mas que é convertido para UTC no banco.
    """
    def db_type(self, connection):
        return "timestamp"


class TsRange(Func):
    

    function = "TSRANGE"
    output_field = DateTimeRangeField()
