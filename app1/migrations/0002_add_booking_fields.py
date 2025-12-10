from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='encounter',
            name='status',
            field=models.CharField(default='BOOKED', max_length=20),
        ),
        migrations.AddField(
            model_name='encounter',
            name='payment_status',
            field=models.CharField(default='PENDING', max_length=20),
        ),
        migrations.AddField(
            model_name='encounter',
            name='problem',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='Reminder',
            fields=[
                ('reminder_id', models.AutoField(primary_key=True, serialize=False)),
                ('remind_at', models.DateTimeField()),
                ('method', models.CharField(default='CALL', max_length=20)),
                ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to='app1.encounter')),
            ],
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('feedback_id', models.AutoField(primary_key=True, serialize=False)),
                ('rating', models.IntegerField(blank=True, null=True)),
                ('comments', models.TextField(blank=True, null=True)),
                ('follow_up_required', models.BooleanField(default=False)),
                ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='app1.encounter')),
            ],
        ),
    ]
