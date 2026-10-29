import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Bug Fix #2: Change SaleItem.product from CASCADE to SET_NULL so deleting a
    product no longer wipes out historical sale records.

    Also adds product_name as a snapshot field so invoices stay readable even
    after the product is deleted.
    """

    dependencies = [
        ('core', '0002_sale_staff'),
    ]

    operations = [
        # Step 1: Add the product_name snapshot column (blank allowed for existing rows)
        migrations.AddField(
            model_name='saleitem',
            name='product_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),

        # Step 2: Change the product FK from CASCADE → SET_NULL
        migrations.AlterField(
            model_name='saleitem',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.product',
            ),
        ),
    ]

