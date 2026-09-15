
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_vmaccessrequest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '待付款'),
                    ('paid', '已付款'),
                    ('cancelled', '已取消'),
                    ('refunded', '已退款'),
                ],
                default='pending',
                max_length=20,
                verbose_name='訂單狀態',
            ),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '待付款'),
                    ('paid', '付款成功'),
                    ('failed', '付款失敗'),
                    ('refunded', '已退款'),
                ],
                default='pending',
                max_length=20,
                verbose_name='付款狀態',
            ),
        ),
    ]
