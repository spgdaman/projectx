from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_add_alertlog_is_read'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_digest_opt_in',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_digest_frequency',
            field=models.CharField(
                choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
                default='daily',
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name='EmailConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('smtp_host', models.CharField(default='smtp.gmail.com', max_length=255)),
                ('smtp_port', models.IntegerField(default=587)),
                ('smtp_username', models.CharField(blank=True, max_length=255)),
                ('smtp_password', models.CharField(blank=True, max_length=255)),
                ('use_tls', models.BooleanField(default=True)),
                ('use_ssl', models.BooleanField(default=False)),
                ('from_email', models.EmailField(default='noreply@bargainhunters.co.ke')),
                ('from_name', models.CharField(default='Bargain Hunters', max_length=100)),
                ('is_active', models.BooleanField(
                    default=False,
                    help_text='When False, Django falls back to settings.py EMAIL_* env vars',
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Email configuration',
            },
        ),
    ]
