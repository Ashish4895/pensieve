# Generated manually for Postgres + pgvector

from django.db import migrations
import pgvector.django.vector
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0002_documentchunk"),
    ]

    operations = [
        VectorExtension(),
        migrations.RemoveField(
            model_name="documentchunk",
            name="embedding_json",
        ),
        migrations.AddField(
            model_name="documentchunk",
            name="embedding",
            field=pgvector.django.vector.VectorField(dimensions=3072),
        ),
    ]
