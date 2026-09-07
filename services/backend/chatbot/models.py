from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class Message(models.Model):
    session_id = models.CharField(max_length=100, default="default")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    role = models.CharField(max_length=20)  # "user" or "model"
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["session_id", "user"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:30]}..."


# gemini-embedding-2 default output size observed in this project
EMBEDDING_DIMENSIONS = 3072


class DocumentChunk(models.Model):
    source_name = models.CharField(max_length=255)
    content = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    def __str__(self):
        return f"{self.source_name} - Chunk {self.id}"
