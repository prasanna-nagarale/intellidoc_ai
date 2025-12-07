# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        if username is None:
            username = email.split("@")[0]
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    """Enhanced user model for IntelliDoc AI"""

    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Subscription & Usage
    plan = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("pro", "Pro"), ("enterprise", "Enterprise")],
        default="free",
    )
    documents_uploaded = models.IntegerField(default=0)
    queries_made = models.IntegerField(default=0)
    storage_used = models.BigIntegerField(default=0)  # in bytes

    # Timestamps
    last_active = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Preferences
    email_notifications = models.BooleanField(default=True)
    dark_mode = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # keep username but email is the unique identifier

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_plan_limits(self):
        """Get plan-specific limits"""
        limits = {
            "free": {"documents": 10, "storage": 100 * 1024 * 1024, "queries": 100},
            "pro": {"documents": 100, "storage": 1024 * 1024 * 1024, "queries": 1000},
            "enterprise": {"documents": -1, "storage": -1, "queries": -1},
        }
        return limits.get(self.plan, limits["free"])

    def can_upload_document(self, file_size):
        """Check if user can upload document"""
        limits = self.get_plan_limits()

        if limits["documents"] != -1 and self.documents_uploaded >= limits["documents"]:
            return False, "Document limit reached for your plan"

        if limits["storage"] != -1 and (self.storage_used + file_size) > limits["storage"]:
            return False, "Storage limit reached for your plan"

        return True, "OK"

    def update_usage(self, documents_delta=0, storage_delta=0, queries_delta=0):
        """Update user usage stats"""
        self.documents_uploaded += documents_delta
        self.storage_used += storage_delta
        self.queries_made += queries_delta
        self.last_active = timezone.now()
        self.save(update_fields=["documents_uploaded", "storage_used", "queries_made", "last_active"])
