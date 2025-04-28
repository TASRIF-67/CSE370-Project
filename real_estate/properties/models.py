from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('agent', 'Agent'),
        ('normal', 'Normal User'),
    )
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='normal')
    license_number = models.CharField(max_length=50, blank=True, null=True)
    experience_years = models.IntegerField(blank=True, null=True)
    total_listings = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0, null=True, blank=True)
    agent_application_status = models.CharField(
        max_length=20,
        choices=[('none', 'None'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='none'
    )
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username

class Property(models.Model):
    PROPERTY_TYPES = (
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('commercial', 'Commercial'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('sold', 'Sold'),
        ('under_review', 'Under Review'),
        ('rejected', 'Rejected'), #newly added
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    square_footage = models.PositiveIntegerField(default=100)
    year_built = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    seller = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='properties')
    assigned_agent = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_properties')
    commission_rate = models.FloatField(default=0.0)
    

    def __str__(self):
        return self.title

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')

    def __str__(self):
        return f"Image for {self.property.title}"

class AgentApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='agent_application')
    license_number = models.CharField(max_length=50)
    experience_years = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == 'approved':
            self.user.role = 'agent'
            self.user.license_number = self.license_number
            self.user.experience_years = self.experience_years
            self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.status}"

class Interest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigning', 'Assigning…'),
        ('assigned', 'Assigned'),
    )
    property = models.ForeignKey('Property', on_delete=models.CASCADE)
    interested_user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='interests')
    assigned_agent = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # New: Status field

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('property', 'interested_user')
class Transaction(models.Model):
    buyer = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='purchases')
    property = models.ForeignKey('Property', on_delete=models.CASCADE)
    agent = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, related_name='sales')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    invoice = models.FileField(upload_to='invoices/', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )

class Feedback(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('read', 'Read'),
    )
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    feedback_text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')

    def __str__(self):
        return f"Feedback from {self.user.username} on {self.date}"
    
class AgentRating(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='ratings_given')
    agent = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='ratings_received')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]  # Ensure rating is between 1 and 5
    )
    review = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE, related_name='ratings', null=True)  # Add this field to link ratings to transactions

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # SELECT * FROM properties_agentrating WHERE agent_id = <self.agent.id>;
        ratings = AgentRating.objects.filter(agent=self.agent)
        if ratings.exists():
            # UPDATE properties_customuser SET average_rating = <avg> WHERE id = <self.agent.id>;
            self.agent.average_rating = sum(r.rating for r in ratings) / ratings.count()
        else:
            self.agent.average_rating = 0.0
        self.agent.save()

    def __str__(self):
        return f"Rating {self.rating} for {self.agent.username} by {self.user.username}"

    class Meta:
        unique_together = ('transaction', 'user')  # Prevent multiple ratings per user per transaction