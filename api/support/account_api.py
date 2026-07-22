"""Customer-facing support ticket API (/account/support) — create/list/view
your own tickets and reply to them. Staff respond via Django's /admin/ for
now (see support/admin.py)."""
from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from support.models import SupportTicket, SupportTicketMessage


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicketMessage
        fields = ["id", "author_label", "is_staff_reply", "body", "created_at"]


class SupportTicketListSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = SupportTicket
        fields = ["id", "subject", "status", "message_count", "created_at", "updated_at"]


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    messages = SupportTicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = ["id", "subject", "status", "messages", "created_at", "updated_at"]


class SupportTicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return SupportTicketDetailSerializer if self.request.method == "POST" else SupportTicketListSerializer

    def create(self, request, *args, **kwargs):
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()
        if not subject:
            raise ValidationError({"subject": "Required."})
        if not body:
            raise ValidationError({"body": "Required."})

        with transaction.atomic():
            ticket = SupportTicket.objects.create(user=request.user, subject=subject[:200])
            SupportTicketMessage.objects.create(
                ticket=ticket, author=request.user, author_label=request.user.email,
                is_staff_reply=False, body=body,
            )
        return Response(SupportTicketDetailSerializer(ticket).data, status=201)


class SupportTicketDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketDetailSerializer

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)


class SupportTicketReplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk, user=request.user)
        body = (request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Required."})

        SupportTicketMessage.objects.create(
            ticket=ticket, author=request.user, author_label=request.user.email,
            is_staff_reply=False, body=body,
        )
        # A customer reply always means "this needs staff attention again" —
        # even if it had been marked resolved.
        ticket.status = SupportTicket.Status.OPEN
        ticket.save(update_fields=["status", "updated_at"])
        return Response(SupportTicketDetailSerializer(ticket).data)
