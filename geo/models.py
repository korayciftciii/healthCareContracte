from django.db import models


class Province(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, db_index=True)
    plate_code = models.CharField(
        max_length=2,
        unique=True,
        help_text="Plaka kodu, orn: '34'",
        blank=True,
        null=True,
    )
    # Zaman ve Durum Alanları
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'provinces'
        ordering = ['name']
        verbose_name = 'İl'
        verbose_name_plural = 'İller'
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]

    def __str__(self):
        return f"{self.plate_code} - {self.name}" if self.plate_code else self.name



class District(models.Model):
    id = models.BigAutoField(primary_key=True)
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name='districts',
        db_column='province_id',
    )
    name = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'districts'
        ordering = ['name']
        verbose_name = 'İlçe'
        verbose_name_plural = 'İlçeler'
        constraints = [
            models.UniqueConstraint(
                fields=['province', 'name'],
                name='unique_district_per_province',
            ),
        ]
        indexes = [
            models.Index(fields=['province', 'is_active']),
            models.Index(fields=['is_active', 'name']),
        ]

    def __str__(self):
        return f"{self.name} / {self.province.name}"