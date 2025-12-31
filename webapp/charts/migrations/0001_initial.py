# Generated migration for BTC/EUR trades table

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BTCEURTrade',
            fields=[
                ('trade_id', models.CharField(help_text='Binance trade ID (unique identifier)', max_length=50, primary_key=True, serialize=False)),
                ('order_id', models.CharField(db_index=True, help_text='Binance order ID that this trade belongs to', max_length=50)),
                ('symbol', models.CharField(default='BTC/EUR', help_text='Trading pair symbol', max_length=20)),
                ('timestamp', models.BigIntegerField(db_index=True, help_text='Trade execution timestamp (milliseconds since epoch)')),
                ('datetime', models.DateTimeField(db_index=True, help_text='Human-readable datetime of trade execution')),
                ('side', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], db_index=True, help_text='Trade side: buy or sell', max_length=4)),
                ('price', models.DecimalField(decimal_places=8, help_text='Execution price in EUR per BTC', max_digits=20)),
                ('amount', models.DecimalField(decimal_places=8, help_text='Amount of BTC traded', max_digits=20)),
                ('cost', models.DecimalField(decimal_places=8, help_text='Total cost in EUR (price * amount)', max_digits=20)),
                ('fee_cost', models.DecimalField(decimal_places=8, help_text='Fee amount paid', max_digits=20)),
                ('fee_currency', models.CharField(help_text='Currency in which fee was paid (usually BNB)', max_length=10)),
                ('is_maker', models.BooleanField(default=False, help_text='True if this was a maker order (provides liquidity)')),
                ('synced_at', models.DateTimeField(auto_now_add=True, help_text='When this trade was synced from Binance API')),
            ],
            options={
                'verbose_name': 'BTC/EUR Trade',
                'verbose_name_plural': 'BTC/EUR Trades',
                'db_table': 'btc_eur_trades',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='btceurtrade',
            index=models.Index(fields=['-timestamp'], name='btc_eur_tra_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='btceurtrade',
            index=models.Index(fields=['side', '-timestamp'], name='btc_eur_tra_side_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='btceurtrade',
            index=models.Index(fields=['datetime'], name='btc_eur_tra_datetim_idx'),
        ),
    ]
