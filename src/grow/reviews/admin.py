from django.contrib import admin

from grow.reviews.models import HumanOverride, HumanReview

admin.site.register([HumanReview, HumanOverride])
