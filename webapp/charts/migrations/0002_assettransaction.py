# Generated migration for asset_transactions table

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetTransaction',
            fields=[
                ('transaction_id', models.CharField(help_text='Unique transaction identifier (type:id)', max_length=100, primary_key=True, serialize=False)),
                ('transaction_type', models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('transfer', 'Transfer'), ('convert', 'Convert')], db_index=True, help_text='Type of transaction', max_length=10)),
                ('timestamp', models.BigIntegerField(db_index=True, help_text='Transaction timestamp (milliseconds since epoch)')),
                ('datetime', models.DateTimeField(db_index=True, help_text='Human-readable datetime')),
                ('status', models.CharField(choices=[('success', 'Success'), ('pending', 'Pending'), ('failed', 'Failed')], default='success', help_text='Transaction status', max_length=10)),
                ('currency', models.CharField(db_index=True, help_text='Asset symbol (BTC, EUR, BNB, etc.)', max_length=10)),
                ('amount', models.DecimalField(decimal_places=8, help_text='Transaction amount', max_digits=20)),
                ('from_currency', models.CharField(blank=True, help_text='Source currency for converts', max_length=10, null=True)),
                ('to_currency', models.CharField(blank=True, help_text='Target currency for converts', max_length=10, null=True)),
                ('from_amount', models.DecimalField(blank=True, decimal_places=8, help_text='Source amount for converts', max_digits=20, null=True)),
                ('fee', models.DecimalField(decimal_places=8, default=0, help_text='Transaction fee', max_digits=20)),
                ('fee_currency', models.CharField(blank=True, help_text='Fee currency', max_length=10, null=True)),
                ('network', models.CharField(blank=True, help_text='Network used (for deposits/withdrawals)', max_length=20, null=True)),
                ('address', models.CharField(blank=True, help_text='Deposit/withdrawal address', max_length=200, null=True)),
                ('tx_id', models.CharField(blank=True, help_text='Blockchain transaction ID', max_length=200, null=True)),
                ('synced_at', models.DateTimeField(auto_now_add=True, help_text='When this transaction was synced from Binance API')),
            ],
            options={
                'verbose_name': 'Asset Transaction',
                'verbose_name_plural': 'Asset Transactions',
                'db_table': 'asset_transactions',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='assettransaction',
            index=models.Index(fields=['-timestamp'], name='asset_trans_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransaction',
            index=models.Index(fields=['transaction_type', '-timestamp'], name='asset_trans_type_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransaction',
            index=models.Index(fields=['currency', '-timestamp'], name='asset_trans_currency_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='assettransaction',
            index=models.Index(fields=['status'], name='asset_trans_status_idx'),
        ),
    ]
