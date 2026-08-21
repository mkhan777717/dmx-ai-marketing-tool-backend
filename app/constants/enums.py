from enum import Enum


class WorkspaceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"
    TRIAL = "TRIAL"


class MemberStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"


class InviteStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class NotificationType(str, Enum):
    SYSTEM = "SYSTEM"
    ALERT = "ALERT"
    MESSAGE = "MESSAGE"
    BILLING = "BILLING"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class AssetType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    AUDIO = "AUDIO"
    LOGO = "LOGO"
    ICON = "ICON"
    OTHER = "OTHER"


class AssetStatus(str, Enum):
    UPLOADING = "UPLOADING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ScheduleStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class ContentType(str, Enum):
    SOCIAL_POST = "SOCIAL_POST"
    EMAIL = "EMAIL"
    BLOG = "BLOG"
    ADVERTISEMENT = "ADVERTISEMENT"
    LANDING_PAGE = "LANDING_PAGE"
    SMS = "SMS"
    OTHER = "OTHER"


class ContentStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    READY = "READY"


class ApiProvider(str, Enum):
    OPENAI = "OPENAI"
    CLAUDE = "CLAUDE"
    GEMINI = "GEMINI"
    META = "META"
    LINKEDIN = "LINKEDIN"
    GOOGLE = "GOOGLE"
    STRIPE = "STRIPE"
    MOCK = "MOCK"
    INSTAGRAM = "INSTAGRAM"
    TWITTER = "TWITTER"


class RoleType(str, Enum):
    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"


class PermissionAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MANAGE = "MANAGE"
    PUBLISH = "PUBLISH"


class MembershipStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"


class UserRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class PublishStatus(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class SnapshotType(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobPriority(str, Enum):
    LOW = "LOW"
    DEFAULT = "DEFAULT"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
