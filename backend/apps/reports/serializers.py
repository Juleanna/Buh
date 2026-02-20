from rest_framework import serializers

from .models import BackupRecord


class BackupRecordSerializer(serializers.ModelSerializer):
    file_size_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = BackupRecord
        fields = [
            'id', 'filename', 'file_size', 'file_size_display',
            'status', 'status_display', 'gdrive_file_id', 'gdrive_link',
            'error_message', 'is_auto', 'created_at',
        ]

    def get_file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        return f'{size / (1024 * 1024 * 1024):.2f} GB'
