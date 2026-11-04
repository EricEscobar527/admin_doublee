from django.db import migrations, models


def backfill_plan(apps, schema_editor):
    """Llena plan base y oferta de las suscripciones ya guardadas, a partir de la respuesta de Google."""
    Subscription = apps.get_model("subscriptions", "Subscription")
    for sub in Subscription.objects.exclude(google_response={}):
        items = [i for i in sub.google_response.get("lineItems", []) if i.get("productId") == sub.product_id]
        if not items:
            continue
        offer = max(items, key=lambda i: i.get("expiryTime") or "").get("offerDetails") or {}
        sub.base_plan_id = offer.get("basePlanId", "")
        sub.offer_id = offer.get("offerId", "")
        sub.save(update_fields=["base_plan_id", "offer_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="base_plan_id",
            field=models.CharField(blank=True, max_length=100, verbose_name="plan base"),
        ),
        migrations.AddField(
            model_name="subscription",
            name="offer_id",
            field=models.CharField(blank=True, max_length=100, verbose_name="oferta"),
        ),
        migrations.RunPython(backfill_plan, migrations.RunPython.noop),
    ]
