"""
Database models to create a structure for Handling CRUD.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from common.models import Timestampable
from common.managers import SoftDeletionManager, AllObjectsManager


class LawnEngine(Timestampable):
    """Lawn engine model"""
    lawn_id = models.IntegerField(default=0, db_index=True)
    start_date = models.DateTimeField(_('start date'),
                                      default=timezone.now,
                                      null=True,
                                      blank=True)
    subscription_year = models.IntegerField(default=2019)
    user_input = models.CharField(max_length=256,
                                  null=True,
                                  blank=True)
    stress_zone = models.CharField(max_length=256,
                                   null=True,
                                   blank=True)
    grass_type = models.CharField(max_length=256,
                                  null=True,
                                  blank=True)
    run_type = models.BooleanField(default=False)
    max_lawn_size = models.BooleanField(default=False)
    task_status = models.BooleanField(default=False)
    pouches_per_app = models.DecimalField(max_digits=4,
                                          decimal_places=1,
                                          null=True,
                                          default=0)


class GrassPotential(models.Model):
    """Grass potential model related to lawn engine model"""
    lawn_engine = models.ForeignKey(LawnEngine,
                                    related_name='grass_potential',
                                    on_delete=models.CASCADE, db_index=True)
    date = models.CharField(max_length=16,
                            null=True,
                            blank=True)
    value = models.CharField(max_length=64,
                             null=True,
                             blank=True)


class DateAndPouches(models.Model):
    """date and pouches model related to lawn engine model"""
    lawn_engine = models.ForeignKey(LawnEngine,
                                    related_name='date_and_pouches',
                                    on_delete=models.CASCADE, db_index=True)
    date = models.CharField(max_length=16,
                            null=True,
                            blank=True)
    pouches = models.CharField(max_length=64,
                               null=True,
                               blank=True)


class InternalParameters(Timestampable):
    parameter_name = models.CharField(max_length=512)
    production_value = models.CharField(max_length=512,
                                        null=True,
                                        blank=True)
    default_value = models.CharField(max_length=512,
                                     null=True,
                                     blank=True)
    is_delete = models.BooleanField(default=False)
    objects = SoftDeletionManager()
    all_objects = AllObjectsManager()

    def delete(self):
        """soft delete when call delete method in api"""
        self.is_delete = True
        self.save()
