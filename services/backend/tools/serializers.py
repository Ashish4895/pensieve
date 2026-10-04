from rest_framework import serializers

from tools.crypto import encrypt_env
from tools.models import McpServer, ToolDefinition


class McpServerSerializer(serializers.ModelSerializer):
    env = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        write_only=True,
        required=False,
    )
    has_env = serializers.SerializerMethodField()

    class Meta:
        model = McpServer
        fields = (
            "id",
            "name",
            "transport",
            "command",
            "args",
            "env",
            "has_env",
            "enabled",
            "is_builtin",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_builtin", "created_at", "updated_at", "has_env")

    def get_has_env(self, obj):
        return bool(obj.env_ciphertext)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        return value

    def create(self, validated_data):
        env = validated_data.pop("env", None)
        request = self.context.get("request")
        server = McpServer(
            **validated_data,
            created_by=getattr(request, "user", None),
        )
        if env is not None:
            server.env_ciphertext = encrypt_env(env)
        server.save()
        return server

    def update(self, instance, validated_data):
        if instance.is_builtin:
            # Only enable/disable flags for builtin via this serializer path
            # when caller is super_admin (enforced in view).
            for field in ("command", "args", "name", "transport"):
                validated_data.pop(field, None)
        env = validated_data.pop("env", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if env is not None:
            instance.env_ciphertext = encrypt_env(env)
        instance.save()
        return instance


class ToolDefinitionSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source="mcp_server.name", read_only=True)
    preference_enabled = serializers.SerializerMethodField()

    class Meta:
        model = ToolDefinition
        fields = (
            "id",
            "name",
            "title",
            "description",
            "input_schema",
            "annotations",
            "enabled",
            "server_name",
            "mcp_server",
            "preference_enabled",
            "updated_at",
        )
        read_only_fields = fields

    def get_preference_enabled(self, obj):
        prefs = self.context.get("prefs") or {}
        return prefs.get(obj.id, True)


class ToolPreferenceSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()


class ToolCatalogFlagSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
