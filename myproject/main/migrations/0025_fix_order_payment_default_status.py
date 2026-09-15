"""修正 Order.status 和 Payment.status 的 default 從 'paid' 改為 'pending'。

原先的 default='paid' 會導致從 Django Admin 手動建立的訂單直接被當作已付款，
被計入營收且學生能直接看課。正常流程走 place_order 會明確設 'pending' 所以
不受影響，但這個 default 值本身就是個隱患，應該在 model 層就堵住。

注意：這個 migration 只改 default（影響未來新建的資料），不會回溯修改
已存在的資料——既有的 paid 訂單都是走正常付款流程產生的，狀態是正確的。
"""

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
